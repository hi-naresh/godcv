"""Prompt-shape tests for ProjectsAgent.

These tests verify the right rules are injected into the prompt based on
the extra config. They use a fake Gemini client so no real API calls are made.
They do NOT test whether the LLM follows the instructions — that's a quality
evaluation concern. They test that we are ASKING the right things.
"""

import pytest
from backend.agents.projects import ProjectsAgent


class FakeGemini:
    def __init__(self):
        self.last_prompt = ""

    async def generate(self, prompt, json_mode=False):
        self.last_prompt = prompt
        return "stub output"


def _run(extra=None, instructions=""):
    import asyncio
    gemini = FakeGemini()
    agent = ProjectsAgent(gemini)
    asyncio.get_event_loop().run_until_complete(
        agent.run(
            section_content="**TestProject** | Stack - Python\n- Did some work.",
            instructions=instructions,
            job_description="We need a data engineer with Python and Spark.",
            extra=extra or {},
        )
    )
    return gemini.last_prompt


class TestStrictVsStealthBlock:
    def test_strict_mode_uses_strict_block(self):
        p = _run({"stealth_mode": False})
        assert "STRICT MODE" in p
        assert "STEALTH MODE" not in p

    def test_stealth_mode_uses_stealth_block(self):
        p = _run({"stealth_mode": True})
        assert "STEALTH MODE" in p
        assert "STRICT MODE" not in p

    def test_strict_forbids_metric_changes(self):
        p = _run({"stealth_mode": False})
        assert "Do NOT change any existing number, percentage, or metric" in p

    def test_strict_forbids_adding_tech_to_stack(self):
        p = _run({"stealth_mode": False})
        assert "do not add ones just because the JD mentions them" in p

    def test_strict_forbids_forcing_jd_buzzwords(self):
        p = _run({"stealth_mode": False})
        assert "Do NOT force JD buzzwords" in p


class TestExpandCondenseSignal:
    def test_expand_signal_in_instructions(self):
        p = _run(instructions="EXPAND: this demonstrates Python pipelines. Highlight throughput.")
        assert "DIRECTLY relevant" in p
        assert "go into depth" in p

    def test_condense_signal_in_instructions(self):
        p = _run(instructions="CONDENSE: 1 bullet only. Highlight transferable skill: testing.")
        assert "TANGENTIALLY relevant" in p
        assert "1 bullet maximum" in p

    def test_no_signal_defaults_to_moderate(self):
        p = _run(instructions="Rewrite to align with the JD requirements.")
        assert "Moderate" in p

    def test_expand_case_insensitive(self):
        p = _run(instructions="expand: highlight ML pipeline aspects")
        assert "DIRECTLY relevant" in p


class TestBulletCountRule:
    def test_single_bullet_cap(self):
        p = _run({"max_bullets_per_entry": 1})
        assert "exactly 1 bullet" in p

    def test_two_bullet_cap(self):
        p = _run({"max_bullets_per_entry": 2})
        assert "1-2 bullets" in p

    def test_three_plus_bullets(self):
        p = _run({"max_bullets_per_entry": 4})
        assert "up to 4 ONLY" in p

    def test_default_is_three(self):
        p = _run()
        assert "up to 3 ONLY" in p


class TestQuantifiedRule:
    def test_require_quantified_on(self):
        p = _run({"require_quantified_bullets": True})
        assert "MUST include a quantified result" in p

    def test_require_quantified_off(self):
        p = _run({"require_quantified_bullets": False})
        assert "do NOT invent numbers" in p
        assert "MUST include" not in p


class TestTechStackRule:
    def test_technical_role_gets_stack_line(self):
        for rt in ("ai_ml", "backend", "data_eng", "frontend", "devops", "fullstack"):
            p = _run({"role_type": rt})
            assert "| Stack -" in p

    def test_non_technical_role_no_stack_line(self):
        p = _run({"role_type": "leadership"})
        assert "NOT a technical/CS role" in p
        assert "do NOT add '| Stack -' lines" in p

    def test_empty_role_type_treated_as_technical(self):
        p = _run({"role_type": ""})
        assert "| Stack -" in p


class TestAntiAIPhraseList:
    def test_common_ai_phrases_listed_in_prompt(self):
        p = _run()
        for phrase in ("spearheaded", "leveraged cutting-edge", "synergized",
                       "utilized state-of-the-art", "passionate about",
                       "harnessing the power of", "plays a pivotal role",
                       "navigating the complexities", "robust", "end-to-end"):
            assert phrase in p, f"Expected '{phrase}' to be forbidden in prompt"

    def test_no_job_listing_style_bullets_rule(self):
        p = _run()
        assert "sound like a job listing" in p


class TestOutputHygiene:
    def test_no_meta_text_rule_present(self):
        p = _run()
        assert "No notes, no commentary, no preamble, no meta-text" in p
        assert "NEVER write:" in p

    def test_preserve_markdown_links(self):
        p = _run()
        assert "PRESERVE ALL markdown links" in p or "preserve markdown links" in p.lower()

    def test_original_content_injected(self):
        p = _run()
        assert "TestProject" in p
        assert "Did some work." in p

    def test_jd_injected(self):
        p = _run()
        assert "data engineer" in p


class TestOrchestratorProjectCountRule:
    """Verify the orchestrator prompt contains the hard project count instruction."""

    def test_orchestrator_includes_hard_count_rule(self):
        import asyncio
        from backend.agents.orchestrator import OrchestratorAgent

        class FakeOrchGemini:
            def __init__(self):
                self.last_prompt = ""
            async def generate_json(self, prompt):
                self.last_prompt = prompt
                return {"tool_calls": [], "analysis": {}, "scoring": {}}

        gemini = FakeOrchGemini()
        agent = OrchestratorAgent(gemini)
        asyncio.get_event_loop().run_until_complete(
            agent.analyze(resume_markdown="# Resume", job_description="JD", max_projects=3)
        )
        p = gemini.last_prompt
        assert "EXACTLY 3 projects" in p
        assert "hard limit" in p.lower()

    def test_orchestrator_expand_condense_instruction_present(self):
        import asyncio
        from backend.agents.orchestrator import OrchestratorAgent

        class FakeOrchGemini:
            def __init__(self):
                self.last_prompt = ""
            async def generate_json(self, prompt):
                self.last_prompt = prompt
                return {"tool_calls": [], "analysis": {}, "scoring": {}}

        gemini = FakeOrchGemini()
        agent = OrchestratorAgent(gemini)
        asyncio.get_event_loop().run_until_complete(
            agent.analyze(resume_markdown="# Resume", job_description="JD")
        )
        p = gemini.last_prompt
        assert "EXPAND:" in p
        assert "CONDENSE:" in p
