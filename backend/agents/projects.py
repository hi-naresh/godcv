from backend.services.gemini import GeminiClient


class ProjectsAgent:
    def __init__(self, gemini: GeminiClient):
        self.gemini = gemini

    async def run(self, section_content: str, instructions: str,
                  job_description: str, extra: dict = None) -> str:
        promote = extra.get("promote", []) if extra else []
        role_type = extra.get("role_type", "") if extra else ""
        is_technical = role_type in ("ai_ml", "backend", "data_eng", "frontend", "devops", "fullstack", "")

        tech_stack_rule = ""
        if is_technical:
            tech_stack_rule = """- IMPORTANT: Every project MUST have a "| Stack -" line listing key technologies
- If the original project has a stack line, preserve and update it (add JD-relevant tech if truthfully used)
- If a project is missing a stack line, add one based on the technologies mentioned in its bullets
- Reorder the tech list to put JD-relevant technologies first"""
        else:
            tech_stack_rule = """- This is NOT a technical/CS role — do NOT add "| Stack -" lines or technology lists
- Focus on methodologies, outcomes, and domain-relevant details instead"""

        prompt = f"""You are a resume projects section optimizer. Reorder and adjust this projects section to better match the job description.

RULES:
- Keep ALL existing projects
- Reorder to put most relevant projects first
- You may slightly adjust bullet point wording to emphasize relevant aspects
- Keep project names and links accurate
- Return ONLY the projects content, no section header
{tech_stack_rule}

FORMATTING:
- Each project MUST start on its own line with bold title
- Each bullet MUST start on its own new line with '- '
- Separate projects with exactly ONE blank line

Example of correct format (technical role):
**[DataFlow](https://github.com/test)** | Stack - Python, Kafka, Docker
- Built real-time streaming pipeline processing 500K events per second.

**[WebApp](https://github.com/test2)** | Stack - React, Node.js, PostgreSQL
- Designed responsive dashboard interface with real-time data visualization.

PROJECTS TO PROMOTE (put first): {', '.join(promote) if promote else 'Use your judgment based on JD'}

ORIGINAL PROJECTS:
{section_content}

JOB DESCRIPTION:
{job_description}

Reordered projects section:"""
        return await self.gemini.generate(prompt)
