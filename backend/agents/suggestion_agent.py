from backend.services.gemini import GeminiClient


class SuggestionAgent:
    def __init__(self, gemini: GeminiClient):
        self.gemini = gemini

    async def generate(
        self,
        gap_suggestions: list[str],
        tailored_resume: str,
        job_description: str,
    ) -> list[dict]:
        """Generate concrete content suggestions from gap analysis."""
        if not gap_suggestions:
            return []

        gaps_text = "\n".join(f"- {g}" for g in gap_suggestions)

        prompt = f"""You are a resume content advisor. Given a tailored resume, a job description, and a list of profile gaps, generate CONCRETE content that could be added to the resume to address each gap.

RULES:
- Only generate suggestions for gaps that the candidate could PLAUSIBLY have (skill gaps they might know but didn't list, bullet rewording)
- Do NOT fabricate experience the candidate clearly doesn't have (e.g., don't add "5 years of Go" if resume shows no Go at all)
- Do NOT suggest content for experience-level gaps (e.g., "needs 5 more years") — these can't be fixed with text
- Each suggestion targets a specific existing section of the resume
- Skills: comma-separated items to append to the Skills section
- Bullets: a single bullet point for the most relevant experience or project entry

TAILORED RESUME:
{tailored_resume}

JOB DESCRIPTION:
{job_description}

GAPS TO ADDRESS:
{gaps_text}

Respond with a JSON array (may be empty if no actionable gaps):
[
  {{
    "id": "sug-1",
    "section": "<Skills|experience:CompanyKey|projects:ProjectKey>",
    "type": "<skill|bullet>",
    "content": "<the actual text to add>",
    "context": "<which gap this addresses, 1 short sentence>"
  }}
]"""

        result = await self.gemini.generate_json(prompt)
        if isinstance(result, list):
            return result
        return result.get("suggestions", [])
