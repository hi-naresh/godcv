from backend.services.gemini import GeminiClient


class ExperienceAgent:
    def __init__(self, gemini: GeminiClient):
        self.gemini = gemini

    async def run(self, section_content: str, instructions: str,
                  job_description: str, extra: dict = None) -> str:
        role_type = extra.get("role_type", "") if extra else ""
        is_technical = role_type in ("ai_ml", "backend", "data_eng", "frontend", "devops", "fullstack", "")

        if is_technical:
            stack_rule = """- IMMEDIATELY after the title line, add a "Stack Used:" line listing key technologies from this role
- Extract technologies from the original bullets or infer from context
- Reorder the stack to put JD-relevant technologies first
- Bullet points should then focus on IMPACT and RESULTS — not repeat the technologies
- Bullets should highlight quantitative results (numbers, %, time saved) and qualitative takeaways"""
            example = """**Senior Engineer — Acme Corp** *Jan 2023 – Present*
Stack Used: Python, Airflow, Kubernetes, PostgreSQL, gRPC
- Built scalable data pipelines processing 1M+ records daily, reducing processing time by 60%.
- Designed microservices architecture that cut API latency by 30%, improving user retention.
- Led migration from monolith to event-driven system, enabling 3x throughput at peak load."""
        else:
            stack_rule = """- This is NOT a technical/CS role — do NOT add a "Stack Used:" line
- Bullets should focus on impact, outcomes, methodologies, and domain-relevant results"""
            example = """**Senior Analyst — Acme Corp** *Jan 2023 – Present*
- Led cross-functional initiative reducing customer churn by 15% through data-driven retention strategies.
- Designed operational workflow that cut processing time by 40%, saving $200K annually."""

        prompt = f"""You are a resume experience bullet point writer. Rewrite ONLY this single job entry to better match the job description.

RULES:
- Keep the exact same job title, company name, and dates line (first bold line) UNCHANGED
{stack_rule}
- Maintain truthfulness — reword to emphasize relevant aspects, don't fabricate
- Use action verbs and keywords from the job description
- Keep quantified achievements (numbers, percentages) — they are real
- Return the COMPLETE entry (title line + stack + bullets), no section header
- Keep 2-4 bullet points per entry

FORMATTING:
- The title line MUST be on its own line
- Stack Used line (if applicable) on the very next line after title
- Each bullet MUST start on its own new line with '- '
- Do NOT merge bullets onto the same line

Example of correct format:
{example}

SPECIFIC INSTRUCTIONS: {instructions}

ORIGINAL ENTRY:
{section_content}

JOB DESCRIPTION:
{job_description}

Rewritten entry:"""
        return await self.gemini.generate(prompt)
