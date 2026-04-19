from backend.services.gemini import GeminiClient


class ExperienceAgent:
    def __init__(self, gemini: GeminiClient):
        self.gemini = gemini

    async def run(self, section_content: str, instructions: str,
                  job_description: str, extra: dict = None) -> str:
        role_type = extra.get("role_type", "") if extra else ""
        candidate_facts = extra.get("candidate_facts", "") if extra else ""
        is_technical = role_type in ("ai_ml", "backend", "data_eng", "frontend", "devops", "fullstack", "")

        if is_technical:
            stack_rule = """- IMMEDIATELY after the title line, add a "**Stack Used:**" line (bold) listing technologies ACTUALLY used in this role
- Reorder the stack to put JD-relevant technologies first
- Only include technologies that are truthful to the role — do NOT add technologies just because the JD mentions them
- Bullet points should focus on IMPACT and RESULTS, not repeat technologies from the stack line"""
            example = """**Senior Engineer — Acme Corp** *Jan 2023 – Present*
**Stack Used:** Python, Airflow, Kubernetes, PostgreSQL, gRPC
- Built scalable data pipelines processing 1M+ records daily, reducing processing time by 60%.
- Designed microservices architecture that cut API latency by 30%, improving user retention."""
        else:
            stack_rule = """- This is NOT a technical/CS role — do NOT add a "Stack Used:" line
- Bullets should focus on impact, outcomes, methodologies, and domain-relevant results"""
            example = """**Senior Analyst — Acme Corp** *Jan 2023 – Present*
- Led cross-functional initiative reducing customer churn by 15% through data-driven retention strategies.
- Designed operational workflow that cut processing time by 40%, saving $200K annually."""

        prompt = f"""You are a resume experience bullet point writer. Rewrite this single job entry to be more compelling for the target role.

CANDIDATE FACTS:
{candidate_facts}

YOUR GOAL: Make this experience entry resonate with the JD by:
1. Using KEYWORDS and TERMINOLOGY from the JD naturally in the bullets
2. Emphasizing aspects of the work that OVERLAP with JD requirements
3. Framing achievements in terms the hiring manager cares about
4. Keeping the core truth — you worked at this company doing this work — but presenting it through the lens of what the JD values

WHAT YOU CANNOT DO:
- Change the job title, company name, or dates (first bold line stays UNCHANGED)
- Fabricate achievements, metrics, or technologies you didn't use
- Add technologies to Stack Used that weren't part of this specific role
- Remove quantified achievements (numbers, percentages) — they are real

WHAT YOU SHOULD DO:
- Reword bullets to weave in JD keywords where they genuinely apply
- Reorder bullets so the most JD-relevant achievement comes first
- If a bullet describes work that maps to a JD requirement, make that connection explicit
- Use strong action verbs that match the JD's language (e.g., if JD says "orchestrate", use "orchestrated")
{stack_rule}
- Keep 2-4 bullet points per entry

FORMATTING:
- Title line on its own line (UNCHANGED from original)
- Stack Used line (if applicable) on the very next line after title
- Each bullet on its own new line starting with '- '

Example:
{example}

SPECIFIC INSTRUCTIONS FROM ORCHESTRATOR: {instructions}

ORIGINAL ENTRY:
{section_content}

FULL JOB DESCRIPTION:
{job_description}

Rewritten entry:"""
        return await self.gemini.generate(prompt)
