import json
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from backend.db.models import TailorRequest
from backend.services import profile as profile_service
from backend.services.parser import parse_resume
from backend.services.assembler import assemble_resume
from backend.services.gemini import GeminiClient
from backend.agents.orchestrator import OrchestratorAgent
from backend.agents.bus import AgentBus
from backend.agents.profile_learner import ProfileLearnerAgent
from backend.config import GEMINI_API_KEY

logger = logging.getLogger("godcv.tailor")
router = APIRouter(prefix="/api/tailor", tags=["tailor"])


def _sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


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

            plan = await orchestrator.analyze(resume_md, job_description, insights, request.seniority_level)
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
            })

            # Phase 2: Parse resume
            parsed = parse_resume(resume_md)

            # Phase 3: Dispatch agents
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
            section_order = plan.get("section_order")
            tailored_md = assemble_resume(parsed, modified_sections, modified_entries, section_order)

            sections_modified = list(modified_sections.keys()) + [f"experience:{k}" for k in modified_entries]
            logger.info("Tailoring complete — %d sections modified, %d kept",
                        len(sections_modified), len(sections_unchanged))

            yield _sse_event("complete", {
                "markdown": tailored_md,
                "sections_modified": len(sections_modified),
                "sections_kept": len(sections_unchanged),
            })

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
