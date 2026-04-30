import json
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from backend.db.models import TailorRequest, ExecuteRequest
from backend.services import profile as profile_service
from backend.services.parser import parse_resume
from backend.services.assembler import assemble_resume
from backend.services.gemini import GeminiClient
from backend.agents.orchestrator import OrchestratorAgent
from backend.agents.bus import AgentBus
from backend.agents.profile_learner import ProfileLearnerAgent
from backend.agents.ats_scorer import ATSScorerAgent
from backend.agents.resume_scorer import ResumeScorerAgent
from backend.config import GEMINI_API_KEY

logger = logging.getLogger("godcv.tailor")
router = APIRouter(prefix="/api/tailor", tags=["tailor"])


def _sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _resolve_tailoring_prefs(request, profile: dict | None) -> dict:
    """Resolve stealth_mode and tailoring style prefs: request override → profile → default."""
    def _get(field: str, default):
        req_val = getattr(request, field, None)
        if req_val is not None:
            return req_val
        if profile and profile.get(field) is not None:
            val = profile.get(field)
            return bool(val) if isinstance(default, bool) else val
        return default
    return {
        "stealth_mode": _get("stealth_mode", False),
        "max_projects": _get("max_projects", 4),
        "max_bullets_per_entry": _get("max_bullets_per_entry", 3),
        "require_quantified_bullets": _get("require_quantified_bullets", True),
    }


SECTION_ORDER_GRADUATE = [
    "Summary", "Education", "Skills", "Experience",
    "Projects", "Volunteering and Interests",
]
SECTION_ORDER_NON_GRADUATE = [
    "Summary", "Skills", "Experience", "Projects",
    "Education", "Volunteering and Interests",
]


def _section_order_for(role_level: str | None) -> list[str]:
    """Backend-deterministic section order. Defaults to non-graduate when
    role_level is unknown (safer for the 'ideal CV' framing)."""
    if role_level == "graduate":
        return SECTION_ORDER_GRADUATE
    return SECTION_ORDER_NON_GRADUATE


@router.post("")
async def tailor_resume(request: TailorRequest):
    # Resolve API key
    api_key = request.gemini_api_key or ""
    profile = await profile_service.get_profile()
    if not api_key and profile:
        api_key = profile.get("gemini_api_key", "")
    if not api_key:
        api_key = GEMINI_API_KEY
    if not api_key:
        raise HTTPException(status_code=400, detail="No Gemini API key configured.")

    # Resolve resume
    resume_md = request.resume_override
    if not resume_md and profile:
        resume_md = profile.get("master_resume", "")
    if not resume_md:
        raise HTTPException(status_code=400, detail="No resume available. Create a profile or provide resume_override.")

    job_description = request.job_description
    profile_id = profile["id"] if profile else None

    async def event_stream():
        try:
            gemini = GeminiClient(api_key)

            # Phase 1: Orchestrator
            logger.info("Tailoring started — analyzing job requirements")
            yield _sse_event("status", {"phase": "orchestrator", "message": "Analyzing job requirements..."})

            orchestrator = OrchestratorAgent(gemini)
            insights = []
            if profile_id:
                insights = await profile_service.get_role_insights(profile_id)

            # Pre-parse to extract entry keys for the orchestrator
            pre_parsed = parse_resume(resume_md)
            entry_keys = {}
            for sec_name, sec_val in pre_parsed["sections"].items():
                if isinstance(sec_val, dict) and "_entries" in sec_val:
                    entry_keys[sec_name] = [{"key": e["key"], "title": e["title"]} for e in sec_val["_entries"]]

            page_mode = request.page_mode or (profile.get("page_mode", "single") if profile else "single")
            prefs = _resolve_tailoring_prefs(request, profile)
            stealth_mode = prefs["stealth_mode"]

            # role_level: explicit request override → JD-detect fallback.
            # Used for both prompt context and the deterministic section_order.
            from backend.services.role_level import detect_role_level
            role_level = request.role_level or detect_role_level(job_description)

            # NOTE: agent-side kwarg `fabrication_mode=` and dispatch dict key
            # `call["fabrication_mode"]` are renamed in Task 9 alongside the
            # agents/fabrication.py → agents/stealth.py file rename.
            plan = await orchestrator.analyze(
                resume_md, job_description, insights,
                role_level=role_level,
                page_mode=page_mode,
                entry_keys=entry_keys,
                fabrication_mode=prefs["stealth_mode"],
                max_projects=prefs["max_projects"],
            )
            tool_calls = plan.get("tool_calls", [])
            sections_unchanged = plan.get("sections_unchanged", [])

            active = [c for c in tool_calls if c.get("action") != "keep"]
            logger.info("Orchestrator plan: %d agents to activate, %d sections unchanged",
                        len(active), len(sections_unchanged))
            for c in tool_calls:
                logger.debug("  tool_call: %s %s %s", c.get("agent"), c.get("action"), c.get("entry", ""))

            yield _sse_event("plan", {
                "analysis": plan.get("analysis", {}),
                "tool_calls": tool_calls,
                "sections_unchanged": sections_unchanged,
                "scoring": plan.get("scoring"),
            })

            # If analyze_only, stop here — user reviews before tailoring
            if request.analyze_only:
                yield _sse_event("analysis_complete", {"message": "Analysis complete. Review results before tailoring."})
                return

            # Phase 2: Parse resume
            parsed = parse_resume(resume_md)

            # Phase 3: Dispatch agents
            role_type = plan.get("analysis", {}).get("role_type", "")
            # Build candidate facts once, inject into every tool_call
            from backend.services.candidate_profile import build_candidate_profile
            candidate_facts = build_candidate_profile(resume_md)
            for call in tool_calls:
                call["role_type"] = role_type
                call["candidate_facts"] = candidate_facts
                call["fabrication_mode"] = prefs["stealth_mode"]
                call["max_bullets_per_entry"] = prefs["max_bullets_per_entry"]
                call["require_quantified_bullets"] = prefs["require_quantified_bullets"]

            active_calls = [c for c in tool_calls if c.get("action") != "keep"]
            for call in active_calls:
                agent_name = call["agent"]
                entry = call.get("entry", "")
                label = f"{agent_name}:{entry}" if entry else agent_name
                yield _sse_event("agent_start", {"agent": label})

            bus = AgentBus(gemini)
            result = await bus.dispatch(tool_calls, parsed["sections"], job_description)

            # Emit agent_done events
            if result:
                for key in result.get("modified_sections", {}):
                    preview = result["modified_sections"][key][:100]
                    yield _sse_event("agent_done", {"agent": key.lower(), "preview": preview})
                for key in result.get("modified_entries", {}):
                    preview = result["modified_entries"][key][:100]
                    yield _sse_event("agent_done", {"agent": f"experience:{key}", "preview": preview})

            # Phase 4: Assembly
            logger.info("All agents done — assembling final resume")
            yield _sse_event("assembly", {"message": "Assembling final resume..."})

            modified_sections = result["modified_sections"] if result else {}
            modified_entries = result["modified_entries"] if result else {}
            excluded_entries = result.get("excluded_entries", set()) if result else set()
            section_order = _section_order_for(role_level)
            tailored_md = assemble_resume(parsed, modified_sections, modified_entries, section_order, excluded_entries)

            sections_modified = list(modified_sections.keys()) + [f"experience:{k}" for k in modified_entries]
            logger.info("Tailoring complete — %d sections modified, %d kept",
                        len(sections_modified), len(sections_unchanged))

            yield _sse_event("complete", {
                "markdown": tailored_md,
                "sections_modified": len(sections_modified),
                "sections_kept": len(sections_unchanged),
            })

            # Phase 4.5: Score the tailored resume (real "after" scores)
            try:
                yield _sse_event("status", {"phase": "scoring_after", "message": "Scoring tailored resume..."})
                scorer = ResumeScorerAgent(gemini)
                after_scores = await scorer.score(tailored_md, job_description)
                yield _sse_event("scoring_after", after_scores)
            except Exception as e:
                logger.error("After-scoring failed: %s", e)

            # Phase 4.7: ATS Scoring
            try:
                yield _sse_event("status", {"phase": "ats_scoring", "message": "Running ATS analysis..."})
                ats_agent = ATSScorerAgent(gemini)
                ats_result = await ats_agent.score(tailored_md, job_description)
                yield _sse_event("ats_score", ats_result)
            except Exception as e:
                logger.error("ATS scoring failed: %s", e)
                yield _sse_event("ats_score", {"ats_score": 0, "breakdown": {}, "brutal_verdict": f"ATS scoring failed: {str(e)}"})

            # Phase 5: Learn (don't block response)
            if profile_id:
                try:
                    learner = ProfileLearnerAgent(gemini)
                    learning = await learner.learn(resume_md, tailored_md, job_description, plan)

                    await profile_service.upsert_role_insight(
                        profile_id=profile_id,
                        role_type=learning.get("role_type", "general"),
                        strongest_points=learning.get("strongest_points", []),
                        preferred_skill_order=learning.get("preferred_skill_order", []),
                        modified_sections=learning.get("sections_modified", []),
                    )

                    await profile_service.save_tailoring(
                        profile_id=profile_id,
                        job_title=learning.get("job_title"),
                        company=learning.get("company"),
                        job_description=job_description,
                        original_resume=resume_md,
                        tailored_resume=tailored_md,
                        orchestrator_plan=plan,
                        role_type=learning.get("role_type"),
                        sections_modified=sections_modified,
                    )
                except Exception as e:
                    yield _sse_event("error", {"message": f"Learning failed (resume still tailored): {str(e)}"})

        except Exception as e:
            yield _sse_event("error", {"message": str(e)})

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/execute")
async def execute_tailoring(request: ExecuteRequest):
    """Execute tailoring using an existing orchestrator plan (skips re-analysis)."""
    api_key = request.gemini_api_key or ""
    profile = await profile_service.get_profile()
    if not api_key and profile:
        api_key = profile.get("gemini_api_key", "")
    if not api_key:
        api_key = GEMINI_API_KEY
    if not api_key:
        raise HTTPException(status_code=400, detail="No Gemini API key configured.")

    resume_md = request.resume_override
    if not resume_md and profile:
        resume_md = profile.get("master_resume", "")
    if not resume_md:
        raise HTTPException(status_code=400, detail="No resume available.")

    job_description = request.job_description
    profile_id = profile["id"] if profile else None
    plan = request.plan

    async def event_stream():
        try:
            gemini = GeminiClient(api_key)
            tool_calls = plan.get("tool_calls", [])
            sections_unchanged = plan.get("sections_unchanged", [])
            prefs = _resolve_tailoring_prefs(request, profile)
            stealth_mode = prefs["stealth_mode"]
            role_level = request.role_level

            # Phase 1: Parse resume
            yield _sse_event("status", {"phase": "parsing", "message": "Parsing resume..."})
            parsed = parse_resume(resume_md)

            # Phase 2: Dispatch agents
            role_type = plan.get("analysis", {}).get("role_type", "")
            from backend.services.candidate_profile import build_candidate_profile
            candidate_facts = build_candidate_profile(resume_md)
            for call in tool_calls:
                call["role_type"] = role_type
                call["candidate_facts"] = candidate_facts
                call["fabrication_mode"] = prefs["stealth_mode"]
                call["max_bullets_per_entry"] = prefs["max_bullets_per_entry"]
                call["require_quantified_bullets"] = prefs["require_quantified_bullets"]

            active_calls = [c for c in tool_calls if c.get("action") != "keep"]
            for call in active_calls:
                agent_name = call["agent"]
                entry = call.get("entry", "")
                label = f"{agent_name}:{entry}" if entry else agent_name
                yield _sse_event("agent_start", {"agent": label})

            bus = AgentBus(gemini)
            result = await bus.dispatch(tool_calls, parsed["sections"], job_description)

            if result:
                for key in result.get("modified_sections", {}):
                    preview = result["modified_sections"][key][:100]
                    yield _sse_event("agent_done", {"agent": key.lower(), "preview": preview})
                for key in result.get("modified_entries", {}):
                    preview = result["modified_entries"][key][:100]
                    yield _sse_event("agent_done", {"agent": f"experience:{key}", "preview": preview})

            # Phase 3: Assembly
            yield _sse_event("status", {"phase": "assembly", "message": "Assembling final resume..."})
            modified_sections = result["modified_sections"] if result else {}
            modified_entries = result["modified_entries"] if result else {}
            excluded_entries = result.get("excluded_entries", set()) if result else set()
            section_order = _section_order_for(role_level)
            tailored_md = assemble_resume(parsed, modified_sections, modified_entries, section_order, excluded_entries)

            sections_modified = list(modified_sections.keys()) + [f"experience:{k}" for k in modified_entries]
            yield _sse_event("complete", {
                "markdown": tailored_md,
                "sections_modified": len(sections_modified),
                "sections_kept": len(sections_unchanged),
            })

            # Phase 4: Score the tailored resume
            try:
                yield _sse_event("status", {"phase": "scoring_after", "message": "Scoring tailored resume..."})
                scorer = ResumeScorerAgent(gemini)
                after_scores = await scorer.score(tailored_md, job_description)
                yield _sse_event("scoring_after", after_scores)
            except Exception as e:
                logger.error("After-scoring failed: %s", e)

            # Phase 6: ATS Scoring
            try:
                yield _sse_event("status", {"phase": "ats_scoring", "message": "Running ATS analysis..."})
                ats_agent = ATSScorerAgent(gemini)
                ats_result = await ats_agent.score(tailored_md, job_description)
                yield _sse_event("ats_score", ats_result)
            except Exception as e:
                logger.error("ATS scoring failed: %s", e)

            # Phase 7: Learn
            if profile_id:
                try:
                    learner = ProfileLearnerAgent(gemini)
                    learning = await learner.learn(resume_md, tailored_md, job_description, plan)
                    await profile_service.upsert_role_insight(
                        profile_id=profile_id,
                        role_type=learning.get("role_type", "general"),
                        strongest_points=learning.get("strongest_points", []),
                        preferred_skill_order=learning.get("preferred_skill_order", []),
                        modified_sections=learning.get("sections_modified", []),
                    )
                    await profile_service.save_tailoring(
                        profile_id=profile_id,
                        job_title=learning.get("job_title"),
                        company=learning.get("company"),
                        job_description=job_description,
                        original_resume=resume_md,
                        tailored_resume=tailored_md,
                        orchestrator_plan=plan,
                        role_type=learning.get("role_type"),
                        sections_modified=sections_modified,
                    )
                except Exception as e:
                    yield _sse_event("error", {"message": f"Learning failed (resume still tailored): {str(e)}"})

        except Exception as e:
            yield _sse_event("error", {"message": str(e)})

    return StreamingResponse(event_stream(), media_type="text/event-stream")
