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
- Maintain the exact markdown formatting (bold category headers, comma-separated skills)
- Return ONLY the skills section content, no section header

SKILLS TO PROMOTE (put first): {', '.join(promote) if promote else 'Use your judgment'}
SKILLS TO DEMOTE (put later): {', '.join(demote) if demote else 'None'}

ORIGINAL SKILLS:
{section_content}

JOB DESCRIPTION:
{job_description}

Reordered skills section:"""
        return await self.gemini.generate(prompt)
