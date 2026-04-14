from backend.services.gemini import GeminiClient


class ProfileLearnerAgent:
    def __init__(self, gemini: GeminiClient):
        self.gemini = gemini

    async def learn(
        self,
        original_resume: str,
        tailored_resume: str,
        job_description: str,
        orchestrator_plan: dict,
    ) -> dict:
        """Extract learning insights from a tailoring session."""
        role_type = orchestrator_plan.get("analysis", {}).get("role_type", "general")

        prompt = f"""Analyze this resume tailoring session and extract key insights.

ORCHESTRATOR PLAN:
Role type: {role_type}
Key requirements: {orchestrator_plan.get('analysis', {}).get('key_requirements', [])}

ORIGINAL RESUME (abbreviated):
{original_resume[:2000]}

TAILORED RESUME (abbreviated):
{tailored_resume[:2000]}

JOB DESCRIPTION (abbreviated):
{job_description[:1000]}

Return a JSON object:
{{
  "role_type": "{role_type}",
  "strongest_points": ["<top 5 talking points that were most effective for this role type>"],
  "preferred_skill_order": ["<top 10 skills in order of importance for this role type>"],
  "sections_modified": ["<list of section names that were modified>"],
  "job_title": "<extracted job title from JD or null>",
  "company": "<extracted company name from JD or null>"
}}"""

        return await self.gemini.generate_json(prompt)
