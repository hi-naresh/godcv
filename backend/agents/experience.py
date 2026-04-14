from backend.services.gemini import GeminiClient


class ExperienceAgent:
    def __init__(self, gemini: GeminiClient):
        self.gemini = gemini

    async def run(self, section_content: str, instructions: str,
                  job_description: str, extra: dict = None) -> str:
        prompt = f"""You are a resume experience bullet point writer. Rewrite ONLY this single job entry to better match the job description.

RULES:
- Keep the exact same job title, company name, and dates line (first bold line) UNCHANGED
- Only modify the bullet points below the title line
- Maintain truthfulness -- reword to emphasize relevant aspects, don't fabricate
- Use action verbs and keywords from the job description
- Keep quantified achievements (numbers, percentages) -- they are real
- Return the COMPLETE entry (title line + bullets), no section header
- Keep 2-4 bullet points per entry

SPECIFIC INSTRUCTIONS: {instructions}

ORIGINAL ENTRY:
{section_content}

JOB DESCRIPTION:
{job_description}

Rewritten entry:"""
        return await self.gemini.generate(prompt)
