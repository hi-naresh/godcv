from backend.services.gemini import GeminiClient


class SummaryAgent:
    def __init__(self, gemini: GeminiClient):
        self.gemini = gemini

    async def run(self, section_content: str, instructions: str,
                  job_description: str, extra: dict = None) -> str:
        prompt = f"""You are a resume summary writer. Rewrite ONLY this summary section to better match the job description.

RULES:
- Keep it to 2-3 sentences maximum
- Maintain truthfulness -- only emphasize existing skills/experience
- Use keywords from the job description naturally
- Keep the same professional tone
- Return ONLY the rewritten summary text, no headers, no extra text

SPECIFIC INSTRUCTIONS: {instructions}

ORIGINAL SUMMARY:
{section_content}

JOB DESCRIPTION:
{job_description}

Rewritten summary:"""
        return await self.gemini.generate(prompt)
