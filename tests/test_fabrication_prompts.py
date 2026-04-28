import pytest
from backend.agents.orchestrator import OrchestratorAgent


class FakeGemini:
    def __init__(self, json_response=None):
        self.prompt = ""
        self.json_response = json_response or {"tool_calls": [], "analysis": {}, "scoring": {}}

    async def generate(self, prompt):
        self.prompt = prompt
        return "stub"

    async def generate_json(self, prompt):
        self.prompt = prompt
        return self.json_response


@pytest.mark.asyncio
async def test_orchestrator_truthful_by_default():
    fake = FakeGemini()
    agent = OrchestratorAgent(fake)
    await agent.analyze(resume_markdown="# Resume", job_description="JD")
    assert "DO NOT fabricate professional work experience" in fake.prompt
    assert "FABRICATION ALLOWED" not in fake.prompt


@pytest.mark.asyncio
async def test_orchestrator_fabrication_swaps_block():
    fake = FakeGemini()
    agent = OrchestratorAgent(fake)
    await agent.analyze(resume_markdown="# Resume", job_description="JD", fabrication_mode=True)
    assert "FABRICATION ALLOWED" in fake.prompt
    assert "DO NOT fabricate professional work experience" not in fake.prompt


from backend.agents.summary import SummaryAgent


@pytest.mark.asyncio
async def test_summary_truthful_by_default():
    fake = FakeGemini()
    agent = SummaryAgent(fake)
    await agent.run(section_content="orig", instructions="instr", job_description="jd", extra={})
    assert "only mention skills and experience the candidate actually has" in fake.prompt
    assert "FABRICATION ALLOWED" not in fake.prompt


@pytest.mark.asyncio
async def test_summary_fabrication_swaps_block():
    fake = FakeGemini()
    agent = SummaryAgent(fake)
    await agent.run(
        section_content="orig", instructions="instr", job_description="jd",
        extra={"fabrication_mode": True},
    )
    assert "FABRICATION ALLOWED" in fake.prompt
    assert "only mention skills and experience the candidate actually has" not in fake.prompt


from backend.agents.skills import SkillsAgent


@pytest.mark.asyncio
async def test_skills_truthful_by_default():
    fake = FakeGemini()
    agent = SkillsAgent(fake)
    await agent.run(section_content="orig", instructions="instr", job_description="jd", extra={})
    assert "Do NOT fabricate skills the candidate doesn't have" in fake.prompt
    assert "FABRICATION ALLOWED" not in fake.prompt


@pytest.mark.asyncio
async def test_skills_fabrication_swaps_block():
    fake = FakeGemini()
    agent = SkillsAgent(fake)
    await agent.run(
        section_content="orig", instructions="instr", job_description="jd",
        extra={"fabrication_mode": True},
    )
    assert "FABRICATION ALLOWED" in fake.prompt
    assert "Do NOT fabricate skills the candidate doesn't have" not in fake.prompt


from backend.agents.education import EducationAgent


@pytest.mark.asyncio
async def test_education_truthful_by_default():
    fake = FakeGemini()
    agent = EducationAgent(fake)
    await agent.run(section_content="orig", instructions="instr", job_description="jd", extra={})
    assert "Do NOT fabricate courses" in fake.prompt
    assert "FABRICATION ALLOWED" not in fake.prompt


@pytest.mark.asyncio
async def test_education_fabrication_swaps_block():
    fake = FakeGemini()
    agent = EducationAgent(fake)
    await agent.run(
        section_content="orig", instructions="instr", job_description="jd",
        extra={"fabrication_mode": True},
    )
    assert "FABRICATION ALLOWED" in fake.prompt
    assert "Do NOT fabricate courses" not in fake.prompt


from backend.agents.experience import ExperienceAgent


@pytest.mark.asyncio
async def test_experience_truthful_by_default():
    fake = FakeGemini()
    agent = ExperienceAgent(fake)
    await agent.run(
        section_content="orig", instructions="instr", job_description="jd",
        extra={"role_type": "backend"},
    )
    assert "Fabricate achievements, metrics, or technologies you didn't use" in fake.prompt
    assert "FABRICATION ALLOWED" not in fake.prompt


@pytest.mark.asyncio
async def test_experience_fabrication_swaps_block():
    fake = FakeGemini()
    agent = ExperienceAgent(fake)
    await agent.run(
        section_content="orig", instructions="instr", job_description="jd",
        extra={"role_type": "backend", "fabrication_mode": True},
    )
    assert "FABRICATION ALLOWED" in fake.prompt
    assert "Fabricate achievements, metrics, or technologies you didn't use" not in fake.prompt


from backend.agents.projects import ProjectsAgent


@pytest.mark.asyncio
async def test_projects_truthful_by_default():
    fake = FakeGemini()
    agent = ProjectsAgent(fake)
    await agent.run(
        section_content="orig", instructions="instr", job_description="jd",
        extra={"role_type": "backend"},
    )
    assert "DON'T FABRICATE" in fake.prompt
    assert "FABRICATION ALLOWED" not in fake.prompt


@pytest.mark.asyncio
async def test_projects_fabrication_swaps_block():
    fake = FakeGemini()
    agent = ProjectsAgent(fake)
    await agent.run(
        section_content="orig", instructions="instr", job_description="jd",
        extra={"role_type": "backend", "fabrication_mode": True},
    )
    assert "FABRICATION ALLOWED" in fake.prompt
    assert "DON'T FABRICATE" not in fake.prompt


@pytest.mark.asyncio
async def test_projects_generate_block_softens_when_fabrication_on():
    fake = FakeGemini()
    agent = ProjectsAgent(fake)
    await agent.run(
        section_content="orig", instructions="instr", job_description="jd",
        extra={"role_type": "backend", "fabrication_mode": True, "generate_projects": True, "candidate_skills": "Python"},
    )
    # Strict generation rule should be removed when fabrication_mode is on
    assert "Must use ONLY technologies the candidate already knows" not in fake.prompt


from backend.agents.suggestion_agent import SuggestionAgent


@pytest.mark.asyncio
async def test_suggestions_truthful_by_default():
    fake = FakeGemini(json_response=[])
    agent = SuggestionAgent(fake)
    await agent.generate(gap_suggestions=["g"], tailored_resume="r", job_description="j")
    assert "NEVER fabricate professional experience" in fake.prompt
    assert "FABRICATION ALLOWED" not in fake.prompt


@pytest.mark.asyncio
async def test_suggestions_fabrication_swaps_block():
    fake = FakeGemini(json_response=[])
    agent = SuggestionAgent(fake)
    await agent.generate(gap_suggestions=["g"], tailored_resume="r", job_description="j", fabrication_mode=True)
    assert "FABRICATION ALLOWED" in fake.prompt
    assert "NEVER fabricate professional experience" not in fake.prompt


@pytest.mark.asyncio
async def test_orchestrator_uses_custom_max_projects():
    fake = FakeGemini()
    agent = OrchestratorAgent(fake)
    await agent.analyze(resume_markdown="r", job_description="j", max_projects=6)
    assert "Always select up to 6 projects total" in fake.prompt


@pytest.mark.asyncio
async def test_experience_uses_custom_bullet_cap():
    fake = FakeGemini()
    agent = ExperienceAgent(fake)
    await agent.run(
        section_content="o", instructions="i", job_description="j",
        extra={"role_type": "backend", "max_bullets_per_entry": 2},
    )
    assert "Use 1-2 bullets per entry" in fake.prompt
    assert "use up to" not in fake.prompt  # no "up to N" wording when capped at 2


@pytest.mark.asyncio
async def test_experience_drops_quantified_requirement_when_disabled():
    fake = FakeGemini()
    agent = ExperienceAgent(fake)
    await agent.run(
        section_content="o", instructions="i", job_description="j",
        extra={"role_type": "backend", "require_quantified_bullets": False},
    )
    assert "EVERY bullet MUST include a quantified result" not in fake.prompt
    assert "Prefer quantified results when available" in fake.prompt


@pytest.mark.asyncio
async def test_projects_uses_custom_bullet_cap_with_ceiling():
    fake = FakeGemini()
    agent = ProjectsAgent(fake)
    await agent.run(
        section_content="o", instructions="i", job_description="j",
        extra={"role_type": "backend", "max_bullets_per_entry": 5},
    )
    assert "use up to 5 bullets" in fake.prompt
