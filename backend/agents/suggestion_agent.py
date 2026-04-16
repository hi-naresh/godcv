from backend.services.gemini import GeminiClient


class SuggestionAgent:
    def __init__(self, gemini: GeminiClient):
        self.gemini = gemini

    async def generate(
        self,
        gap_suggestions: list[str],
        tailored_resume: str,
        job_description: str,
        original_resume: str = "",
    ) -> list[dict]:
        """Generate concrete content suggestions from gap analysis."""
        if not gap_suggestions:
            return []

        gaps_text = "\n".join(f"- {g}" for g in gap_suggestions)

        original_context = ""
        if original_resume and original_resume != tailored_resume:
            original_context = f"""
ORIGINAL FULL RESUME (may contain entries excluded from tailored version):
{original_resume}
"""

        prompt = f"""You are a resume content advisor. Given a tailored resume, a job description, the candidate's full original resume, and a list of profile gaps, generate CONCRETE content to make the CV more competitive for this role.

WHAT YOU CAN SUGGEST:

1. **Skills** (type: "skill") — Skills the candidate clearly knows from their coursework, tech stack, or projects but didn't explicitly list. Only suggest skills genuinely derivable from their background.
   - section: "Skills"
   - content: comma-separated skill names

2. **Bullet points** (type: "bullet") — New or improved bullet points for existing experience/project entries that better highlight relevant work.
   - section: "experience:CompanyKey" or "projects:ProjectKey"
   - content: a single bullet starting with "- "

3. **Coursework projects** (type: "project") — If the candidate has relevant coursework (check Education section) that matches a JD requirement, suggest a concise project entry based on what they would have built during that coursework. This is NOT fabrication — coursework projects are real academic work.
   - section: "Projects"
   - content: full project entry in markdown format:
     **ProjectName** at University | Stack - Tech1, Tech2
     - One bullet describing the project outcome

STRICT RULES:
- NEVER fabricate professional experience, job roles, or company names
- NEVER claim skills the candidate has zero evidence of knowing
- Coursework projects MUST be derivable from listed coursework topics (e.g., "Predictive Analytics" coursework → a predictive model project is valid)
- Skills MUST be inferable from their education, projects, or tech stack (e.g., candidate uses PyTorch + does ML coursework → "CNNs" is valid to suggest)
- Do NOT suggest content for unfixable gaps (e.g., "needs 5 more years of experience")
- Keep suggestions concise — each bullet should be 1-2 lines max
- Suggest at most 5 items total, prioritise highest-impact gaps
{original_context}
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
    "section": "<Skills|experience:CompanyKey|projects:ProjectKey|Projects>",
    "type": "<skill|bullet|project>",
    "content": "<the actual text to add>",
    "context": "<which gap this addresses, 1 short sentence>"
  }}
]"""

        result = await self.gemini.generate_json(prompt)
        if isinstance(result, list):
            return result
        return result.get("suggestions", [])
