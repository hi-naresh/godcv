from backend.services.gemini import GeminiClient
from backend.agents.stealth import STEALTH_ALLOWED_BLOCK, STRICT_BLOCK


class EducationAgent:
    def __init__(self, gemini: GeminiClient):
        self.gemini = gemini

    async def run(self, section_content: str, instructions: str,
                  job_description: str, extra: dict = None) -> str:
        stealth_mode = extra.get("stealth_mode", False) if extra else False
        if stealth_mode:
            coursework_rules = (
                STEALTH_ALLOWED_BLOCK +
                "- You may add up to 5 plausible JD-relevant coursework items consistent with the degree program\n"
                "- Degree names, university names, and dates remain UNCHANGED"
            )
        else:
            coursework_rules = (
                STRICT_BLOCK +
                "- Do NOT remove any courses — only reorder and optionally rephrase\n"
                "- Degree names, university names, and dates remain UNCHANGED"
            )
        prompt = f"""You are a resume education section optimizer. Reorder the coursework in this education section to match the job description.

RULES:
- Keep ALL degree names, university names, and dates EXACTLY as they are — character for character
- ONLY reorder the coursework list — put the most JD-relevant courses first
- Do NOT rephrase, rename, or reword any course names — copy them exactly
- Do NOT add, remove, or merge courses
{coursework_rules}
- Return the COMPLETE education section content, no section header

FORMATTING:
- Each degree MUST be on its own line with bold formatting
- Coursework line MUST follow immediately after the degree line
- Preserve the exact formatting pattern of the original

OUTPUT HYGIENE — CRITICAL:
- Return ONLY the education section content. No notes, no commentary, no explanations, no preamble.
- NEVER write meta-text like "Here is the refined education", "I've reordered...", "Note:", "As requested..."

SPECIFIC INSTRUCTIONS: {instructions}

ORIGINAL EDUCATION:
{section_content}

JOB DESCRIPTION:
{job_description}

Refined education section:"""
        return await self.gemini.generate(prompt)
