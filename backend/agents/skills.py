from backend.services.gemini import GeminiClient


class SkillsAgent:
    def __init__(self, gemini: GeminiClient):
        self.gemini = gemini

    async def run(self, section_content: str, instructions: str,
                  job_description: str, extra: dict = None) -> str:
        promote = extra.get("promote", []) if extra else []
        demote = extra.get("demote", []) if extra else []

        prompt = f"""You are a resume skills section optimizer. Reorder this skills section so the most JD-relevant skills jump out first.

YOUR GOAL: A recruiter scans the skills section in 3 seconds. Make sure they immediately see the skills they're looking for.
1. Put the CATEGORY that best matches the JD first (e.g., if JD is about data engineering, "Data Engineering:" goes first)
2. Within each category, put JD-mentioned skills FIRST
3. You may add 1-2 skills if the candidate clearly has them based on their experience (e.g., if they use LangChain, they know Python)
4. Do NOT remove any existing skills
5. Do NOT fabricate skills the candidate doesn't have

FORMATTING — follow this EXACTLY:
- Each category on its own line: **Category Name:** skill1, skill2, skill3.
- Bold markers around category name and colon: **Name:**
- End each category line with a period
- Separate categories with exactly ONE blank line
- Do NOT use bullet points, headers, sub-headers, or any other formatting
- Do NOT add section headers like "# Skills"

Example:
**Data Engineering:** ETL Pipelines, Apache Airflow, MongoDB, PostgreSQL, VectorDB.

**AI/ML:** LangChain, PyTorch, RAG Systems, Fine-tuning.

**Cloud/Infra:** AWS, Docker, Kubernetes, CI/CD.

OUTPUT HYGIENE — CRITICAL:
- Return ONLY the skills section content. No notes, no commentary, no explanations, no preamble.
- NEVER write meta-text like "Here are the reordered skills", "I've prioritized...", "Based on the JD...", "Note:", "As requested..."
- Output should be ONLY the category lines — nothing else

SKILLS TO PROMOTE (put first in their category): {', '.join(promote) if promote else 'JD-relevant skills'}
SKILLS TO DEMOTE (put later): {', '.join(demote) if demote else 'None'}

ORIGINAL SKILLS:
{section_content}

FULL JOB DESCRIPTION:
{job_description}

Reordered skills section:"""
        return await self.gemini.generate(prompt)
