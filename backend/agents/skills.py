from backend.services.gemini import GeminiClient


class SkillsAgent:
    def __init__(self, gemini: GeminiClient):
        self.gemini = gemini

    async def run(self, section_content: str, instructions: str,
                  job_description: str, extra: dict = None) -> str:
        promote = extra.get("promote", []) if extra else []
        demote = extra.get("demote", []) if extra else []

        prompt = f"""You are a resume skills section optimizer. Reorder and adjust this skills section to better match the job description.

RULES:
- Keep ALL existing skills -- do not remove any
- Reorder categories and skills within categories to put most relevant first
- You may add 1-2 skills from the JD if the candidate likely has them based on their experience
- Do NOT fabricate skills the candidate doesn't have
- Return ONLY the skills section content, no section header

FORMATTING:
- Each category MUST use bold header with colon: **Category Name:** skill1, skill2
- Each category MUST be separated by exactly ONE blank line

Example of correct format:
**Backend:** Python, FastAPI, Django.

**Cloud/Infra:** AWS, Docker, Kubernetes.

SKILLS TO PROMOTE (put first): {', '.join(promote) if promote else 'Use your judgment'}
SKILLS TO DEMOTE (put later): {', '.join(demote) if demote else 'None'}

ORIGINAL SKILLS:
{section_content}

JOB DESCRIPTION:
{job_description}

Reordered skills section:"""
        return await self.gemini.generate(prompt)
