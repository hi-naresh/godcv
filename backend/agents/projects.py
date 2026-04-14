from backend.services.gemini import GeminiClient


class ProjectsAgent:
    def __init__(self, gemini: GeminiClient):
        self.gemini = gemini

    async def run(self, section_content: str, instructions: str,
                  job_description: str, extra: dict = None) -> str:
        promote = extra.get("promote", []) if extra else []

        prompt = f"""You are a resume projects section optimizer. Reorder and adjust this projects section to better match the job description.

RULES:
- Keep ALL existing projects
- Reorder to put most relevant projects first
- You may slightly adjust bullet point wording to emphasize relevant aspects
- Keep project names, links, and tech stacks accurate
- Maintain the exact markdown formatting
- Return ONLY the projects content, no section header

PROJECTS TO PROMOTE (put first): {', '.join(promote) if promote else 'Use your judgment based on JD'}

ORIGINAL PROJECTS:
{section_content}

JOB DESCRIPTION:
{job_description}

Reordered projects section:"""
        return await self.gemini.generate(prompt)
