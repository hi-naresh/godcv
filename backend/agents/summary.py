from backend.services.gemini import GeminiClient


class SummaryAgent:
    def __init__(self, gemini: GeminiClient):
        self.gemini = gemini

    async def run(self, section_content: str, instructions: str,
                  job_description: str, extra: dict = None) -> str:
        candidate_facts = extra.get("candidate_facts", "") if extra else ""

        prompt = f"""You are a resume summary writer. Craft a compelling 2-3 sentence summary that positions this candidate as a strong fit for the target role.

CANDIDATE FACTS (trust these — do NOT re-interpret dates):
{candidate_facts}

YOUR GOAL: The summary is the first thing a recruiter reads. It should:
1. Lead with the candidate's strongest qualification that matches the JD
2. Mention 2-3 KEY skills/technologies from the JD that the candidate actually has
3. Include a concrete achievement or metric that demonstrates impact
4. Use the JD's own language — if they say "data engineering", say "data engineering" not "ETL development"

RULES:
- 2-3 sentences maximum
- Maintain truthfulness — only mention skills and experience the candidate actually has
- Use keywords from the JD naturally, not stuffed
- Keep a confident, professional tone
- Return ONLY the summary paragraph — no headers, no markdown formatting, no '# Summary'
- Do NOT add '---' separators

SPECIFIC INSTRUCTIONS: {instructions}

ORIGINAL SUMMARY:
{section_content}

FULL JOB DESCRIPTION:
{job_description}

Rewritten summary:"""
        return await self.gemini.generate(prompt)
