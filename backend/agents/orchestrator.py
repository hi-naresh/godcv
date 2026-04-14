from backend.services.gemini import GeminiClient


class OrchestratorAgent:
    def __init__(self, gemini: GeminiClient):
        self.gemini = gemini

    async def analyze(
        self,
        resume_markdown: str,
        job_description: str,
        role_insights: list[dict] | None = None,
    ) -> dict:
        """Analyze job description against resume and produce a tool_calls plan."""
        insights_context = ""
        if role_insights:
            insights_context = "\nPROFILE INSIGHTS FROM PAST TAILORINGS:\n"
            for insight in role_insights:
                insights_context += (
                    f"- Role type '{insight['role_type']}' (tailored {insight['tailoring_count']}x): "
                    f"strongest points: {', '.join(insight.get('strongest_points', [])[:5])}\n"
                )

        prompt = f"""You are a resume tailoring orchestrator. Analyze the job description and the resume below.
Decide which resume sections need modification and which should stay unchanged.

For each section that needs changes, specify what agent should handle it and what instructions to give.

IMPORTANT RULES:
- Frontmatter (between --- markers at the top) is NEVER modified
- Education and Volunteering sections are almost always kept unchanged
- Only modify sections where the job description demands different emphasis
- For Experience, decide PER ENTRY whether to modify or keep
- Preserve the user's truthful experience -- only change wording and emphasis, never fabricate

AVAILABLE AGENTS AND ACTIONS:
- agent: "summary", action: "rewrite" -- rewrite the summary to match job requirements
- agent: "skills", action: "reorder" -- reorder and emphasize relevant skills (with promote/demote lists)
- agent: "experience", entry: "<CompanyKey>", action: "rewrite"|"keep" -- per job entry
- agent: "projects", action: "reorder" -- reorder projects by relevance to job
{insights_context}
RESUME:
{resume_markdown}

JOB DESCRIPTION:
{job_description}

Respond with a JSON object with this exact structure:
{{
  "analysis": {{
    "role_type": "<category like ai_ml, backend, data_eng, frontend, devops, leadership>",
    "key_requirements": ["<top 5-8 requirements from JD>"],
    "matched_strengths": ["<user's existing strengths that match>"]
  }},
  "tool_calls": [
    {{"agent": "<agent_name>", "action": "<rewrite|reorder|keep>", "entry": "<for experience only>", "instructions": "<specific instructions>", "promote": ["<for reorder>"], "demote": ["<for reorder>"]}}
  ],
  "sections_unchanged": ["<section names to keep verbatim>"]
}}"""

        return await self.gemini.generate_json(prompt)
