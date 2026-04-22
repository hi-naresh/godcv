from backend.services.gemini import GeminiClient


class EducationAgent:
    def __init__(self, gemini: GeminiClient):
        self.gemini = gemini

    async def run(self, section_content: str, instructions: str,
                  job_description: str, extra: dict = None) -> str:
        prompt = f"""You are a resume education section optimizer. Refine the coursework and emphasis in this education section to better match the job description.

RULES:
- Keep ALL degree names, university names, and dates EXACTLY as they are
- ONLY modify the coursework lists — reorder to put most relevant courses first
- You may rephrase course names slightly to better align with JD terminology (e.g., "Neural Networks" → "Deep Learning & Neural Networks") but keep them truthful
- You may add 1-2 relevant coursework items if they are clearly implied by the degree (e.g., an MSc in AI clearly includes "Machine Learning")
- Do NOT fabricate courses that wouldn't exist in the program
- Do NOT remove any courses — only reorder and optionally rephrase
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
