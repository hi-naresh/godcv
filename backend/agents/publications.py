from backend.services.gemini import GeminiClient


class PublicationsAgent:
    def __init__(self, gemini: GeminiClient):
        self.gemini = gemini

    async def run(self, section_content: str, instructions: str,
                  job_description: str, extra: dict = None) -> str:
        """Generate a Publications section based on the candidate's coursework and projects.

        Only called when the JD values research/publications and the candidate
        has academic work that could be framed as publications or research output.
        """
        prompt = f"""You are a resume publications section writer. Based on the candidate's academic background and projects, create a concise Publications section.

RULES:
- Only include items that are PLAUSIBLE given the candidate's coursework and projects
- Frame academic coursework projects, thesis work, or research-adjacent projects as publications/research
- Use proper academic citation-like format
- Do NOT fabricate published papers — frame them as "Working Paper", "Thesis", "Technical Report", or "Conference Poster" as appropriate
- Keep it to 2-3 entries maximum
- Each entry should be relevant to the job description
- Return ONLY the section content, no "# Publications" header

FORMATTING:
- Each publication on its own line, bold title
- Format: **Title** — Venue/Type, Year
  - One-line description of contribution

CANDIDATE CONTEXT (from resume):
{section_content}

SPECIFIC INSTRUCTIONS: {instructions}

JOB DESCRIPTION:
{job_description}

Publications section content:"""
        return await self.gemini.generate(prompt)
