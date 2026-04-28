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
