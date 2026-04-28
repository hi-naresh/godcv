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
