from backend.services.gemini import GeminiClient


class ExperienceAgent:
    def __init__(self, gemini: GeminiClient):
        self.gemini = gemini

    async def run(self, section_content: str, instructions: str,
                  job_description: str, extra: dict = None) -> str:
        role_type = extra.get("role_type", "") if extra else ""
        is_technical = role_type in ("ai_ml", "backend", "data_eng", "frontend", "devops", "fullstack", "")

        tech_stack_rule = ""
        if is_technical:
            tech_stack_rule = """- IMPORTANT: Each bullet MUST mention specific technologies/tools used (e.g., Python, Kubernetes, FastAPI)
- If the original entry mentions technologies, preserve them. If not, infer from context.
- Technologies should be naturally woven into the bullet, not listed separately
  Good: "Built end-to-end data pipelines using **Python, Airflow, and Kubernetes**, reducing triage time by 40%."
  Bad: "Built data pipelines reducing triage time by 40%." (missing tech stack)"""
        else:
            tech_stack_rule = """- This is NOT a technical/CS role — do NOT add programming languages or technology stacks
- Focus on domain-relevant skills, methodologies, and outcomes instead"""

        prompt = f"""You are a resume experience bullet point writer. Rewrite ONLY this single job entry to better match the job description.

RULES:
- Keep the exact same job title, company name, and dates line (first bold line) UNCHANGED
- Only modify the bullet points below the title line
- Maintain truthfulness -- reword to emphasize relevant aspects, don't fabricate
- Use action verbs and keywords from the job description
- Keep quantified achievements (numbers, percentages) -- they are real
- Return the COMPLETE entry (title line + bullets), no section header
- Keep 2-4 bullet points per entry
{tech_stack_rule}

FORMATTING:
- The title line MUST be on its own line
- Each bullet MUST start on its own new line with '- '
- Do NOT merge bullets onto the same line

Example of correct format:
**Senior Engineer — Acme Corp** *Jan 2023 – Present*
- Built scalable data pipelines using **Python, Airflow, and Kubernetes**, processing 1M+ records daily.
- Designed microservices architecture with **Go and gRPC**, reducing latency by 30%.

SPECIFIC INSTRUCTIONS: {instructions}

ORIGINAL ENTRY:
{section_content}

JOB DESCRIPTION:
{job_description}

Rewritten entry:"""
        return await self.gemini.generate(prompt)
