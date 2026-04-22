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

OUTPUT HYGIENE — CRITICAL:
- Return ONLY the summary text. No notes, no commentary, no explanations, no preamble.
- NEVER write meta-text like "Here is the summary", "I've crafted...", "Based on your profile...", "Note:", "As requested..."
- NEVER use AI-detectable filler phrases: "spearheaded", "leveraged cutting-edge", "synergized", "passionate about", "driven by a desire to", "poised to", "adept at", "harnessing the power of", "in order to", "plays a pivotal role", "navigating the complexities", "aims to bridge the gap", "utilized state-of-the-art"
- Write like the candidate wrote it themselves — natural, direct, no corporate buzzword soup
- A recruiter should NOT be able to tell AI wrote this

SPECIFIC INSTRUCTIONS: {instructions}

ORIGINAL SUMMARY:
{section_content}

FULL JOB DESCRIPTION:
{job_description}

Rewritten summary:"""
        return await self.gemini.generate(prompt)
