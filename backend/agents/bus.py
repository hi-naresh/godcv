import asyncio
import logging
import re
from backend.agents.summary import SummaryAgent
from backend.agents.skills import SkillsAgent
from backend.agents.experience import ExperienceAgent
from backend.agents.projects import ProjectsAgent
from backend.services.gemini import GeminiClient
from backend.services.formatter import validate_and_fix


class AgentBus:
    """Event-driven agent dispatcher. Executes only the agents specified in the orchestrator's tool_calls."""

    def __init__(self, gemini: GeminiClient):
        self.log = logging.getLogger("godcv.bus")
        self.gemini = gemini
        self.agents = {
            "summary": SummaryAgent(gemini),
            "skills": SkillsAgent(gemini),
            "experience": ExperienceAgent(gemini),
            "projects": ProjectsAgent(gemini),
        }

    async def dispatch(
        self, tool_calls: list[dict], sections: dict, job_description: str
    ) -> dict:
        """Dispatch tool_calls to agents. Returns dict with modified_sections and modified_entries."""

        modified_sections: dict[str, str] = {}
        modified_entries: dict[str, str] = {}

        parallel_calls = []
        experience_calls = []

        for call in tool_calls:
            if call.get("action") == "keep":
                continue
            if call["agent"] == "experience":
                experience_calls.append(call)
            else:
                parallel_calls.append(call)

        # Run non-experience agents in parallel
        if parallel_calls:
            tasks = []
            for call in parallel_calls:
                agent_name = call["agent"]
                agent = self.agents.get(agent_name)
                if not agent:
                    continue

                section_key = _find_section_key(sections, agent_name)
                section_content = sections.get(section_key, "")
                if isinstance(section_content, dict):
                    section_content = section_content.get("_full", "")

                tasks.append(
                    _run_single_agent(agent, agent_name, str(section_content), call, job_description)
                )

            results = await asyncio.gather(*tasks, return_exceptions=True)
            for r in results:
                if isinstance(r, Exception):
                    continue
                agent_name, content = r
                section_key = _find_section_key(sections, agent_name)
                modified_sections[section_key] = content

        # Run experience entries in parallel
        if experience_calls:
            exp_section = sections.get("Experience", {})
            entries = exp_section.get("_entries", []) if isinstance(exp_section, dict) else []
            entry_map = {e["key"]: e for e in entries}

            exp_tasks = []
            exp_agent = self.agents["experience"]
            for call in experience_calls:
                entry_key = call.get("entry", "")
                entry = entry_map.get(entry_key)
                if not entry:
                    # Try fuzzy match
                    for k, v in entry_map.items():
                        if entry_key.lower() in k.lower() or k.lower() in entry_key.lower():
                            entry = v
                            entry_key = k
                            break
                if not entry:
                    continue

                exp_tasks.append(
                    _run_single_agent(
                        exp_agent,
                        f"experience:{entry_key}",
                        entry["content"],
                        call,
                        job_description,
                    )
                )

            results = await asyncio.gather(*exp_tasks, return_exceptions=True)
            for r in results:
                if isinstance(r, Exception):
                    continue
                name, content = r
                entry_key = name.split(":", 1)[1] if ":" in name else name
                modified_entries[entry_key] = content

        return {
            "modified_sections": modified_sections,
            "modified_entries": modified_entries,
        }


def _find_section_key(sections: dict, agent_name: str) -> str:
    """Find the actual section key matching an agent name (case-insensitive)."""
    for key in sections:
        if key.lower() == agent_name.lower():
            return key
    return agent_name.capitalize()


async def _run_single_agent(agent, name: str, content: str, call: dict, jd: str) -> tuple[str, str]:
    result = await agent.run(
        section_content=content,
        instructions=call.get("instructions", ""),
        job_description=jd,
        extra=call,
    )
    section_type = name.split(":")[0] if ":" in name else name
    result = validate_and_fix(section_type, result)
    return name, result
