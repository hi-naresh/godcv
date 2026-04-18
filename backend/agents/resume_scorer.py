from backend.services.gemini import GeminiClient


class ResumeScorerAgent:
    def __init__(self, gemini: GeminiClient):
        self.gemini = gemini

    async def score(self, resume_markdown: str, job_description: str) -> dict:
        """Score a resume against a job description for keyword match, skills coverage, experience fit."""
        prompt = f"""You are a resume scoring evaluator. Score this resume against the job description honestly.

Evaluate:
- keyword_match: percentage of important JD keywords/phrases found in the resume (0-100)
- skills_coverage: percentage of JD required skills present in the Skills section (0-100)
- experience_fit: one sentence describing how experience level matches (years, seniority, domain)
- overall_fit: aggregated score considering all factors (0-100)

RESUME:
{resume_markdown}

JOB DESCRIPTION:
{job_description}

Respond with JSON:
{{
  "keyword_match": "<0-100>",
  "skills_coverage": "<0-100>",
  "experience_fit": "<one sentence>",
  "overall_fit": "<0-100>"
}}"""

        return await self.gemini.generate_json(prompt)
