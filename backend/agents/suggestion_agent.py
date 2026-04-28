from backend.services.gemini import GeminiClient
from backend.agents.fabrication import FABRICATION_ALLOWED_BLOCK


class SuggestionAgent:
    def __init__(self, gemini: GeminiClient):
        self.gemini = gemini

    async def generate(
        self,
        gap_suggestions: list[str],
        tailored_resume: str,
        job_description: str,
        original_resume: str = "",
        fabrication_mode: bool = False,
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

        if fabrication_mode:
            strict_rules = (
                FABRICATION_ALLOWED_BLOCK +
                "Per-suggestion rules:\n"
                "- Coursework projects may use adjacent technologies the candidate could plausibly learn\n"
                "- Skills may include plausible JD-relevant additions consistent with the candidate's stack\n"
                "- For REMOVE: only flag content that actively hurts the application\n"
                "- For REPLACE: the replacement may strengthen existing claims (within plausibility)\n"
                "- Do NOT suggest content for unfixable gaps (e.g., \"needs 5 more years of experience\")\n"
                "- Keep suggestions concise — each bullet should be 1-2 lines max\n"
                "- Suggest at most 7 items total, prioritise highest-impact changes"
            )
        else:
            strict_rules = (
                "STRICT RULES:\n"
                "- NEVER fabricate professional experience, job roles, or company names\n"
                "- NEVER claim skills the candidate has zero evidence of knowing\n"
                "- Coursework projects MUST be derivable from listed coursework topics\n"
                "- Skills MUST be inferable from their education, projects, or tech stack\n"
                "- Do NOT suggest content for unfixable gaps (e.g., \"needs 5 more years of experience\")\n"
                "- For REMOVE: only flag content that actively hurts the application (not just neutral content)\n"
                "- For REPLACE: the replacement must be truthful — only reword, don't fabricate new claims\n"
                "- Keep suggestions concise — each bullet should be 1-2 lines max\n"
                "- Suggest at most 7 items total, prioritise highest-impact changes"
            )

        prompt = f"""You are a resume content advisor. Given a tailored resume, a job description, the candidate's full original resume, and a list of profile gaps, generate CONCRETE content to make the CV more competitive for this role.

WHAT YOU CAN SUGGEST:

ADD content:

1. **Skills** (type: "skill") — Skills the candidate clearly knows from their coursework, tech stack, or projects but didn't explicitly list.
   - section: "Skills"
   - content: comma-separated skill names
   - skill_category: the EXACT name of the existing skill category these skills belong to (e.g., "Backend", "Cloud/Infra", "AI/ML"). Match the category name exactly as it appears in the resume. If no category fits, use the most relevant existing one.

2. **Bullet points** (type: "bullet") — New bullet points for existing experience/project entries that highlight relevant work.
   - section: "experience:CompanyKey" or "projects:ProjectKey"
   - content: a single bullet starting with "- "

3. **Coursework/personal projects** (type: "project") — Suggest realistic project entries the candidate could build or has built based on their skills and coursework. These fill JD gaps that existing projects don't cover.
   - section: "Projects"
   - content: full project entry in markdown format:
     **Project Name** at University **| Stack -** Tech1, Tech2
     - One compelling bullet describing the project and its outcome/impact
   - These must use ONLY technologies the candidate already knows
   - Must be realistic — something they would actually build given their background

REMOVE or REPLACE content:

4. **Remove** (type: "remove") — Flag content that HURTS this application: irrelevant bullets, off-topic skills, or entries that waste space for this specific role.
   - section: "experience:CompanyKey" or "projects:ProjectKey" or "Skills"
   - content: the EXACT text to remove (copy it verbatim from the resume)
   - context: why removing this helps

5. **Replace** (type: "replace") — Flag a bullet or skill that should be reworded to better match the JD.
   - section: "experience:CompanyKey" or "projects:ProjectKey" or "Skills"
   - content: the replacement text
   - old_content: the EXACT original text being replaced (copy verbatim from the resume)
   - context: why this rewording is better

{strict_rules}
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
    "type": "<skill|bullet|project|remove|replace>",
    "content": "<text to add, or exact text to remove, or replacement text>",
    "old_content": "<ONLY for type=replace: the exact original text being replaced>",
    "skill_category": "<ONLY for type=skill: exact category name from resume, e.g. Backend, Cloud/Infra>",
    "context": "<what this addresses, 1 short sentence>"
  }}
]"""

        result = await self.gemini.generate_json(prompt)
        if isinstance(result, list):
            return result
        return result.get("suggestions", [])
