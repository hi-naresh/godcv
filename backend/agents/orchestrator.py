from backend.services.gemini import GeminiClient


class OrchestratorAgent:
    def __init__(self, gemini: GeminiClient):
        self.gemini = gemini

    async def analyze(
        self,
        resume_markdown: str,
        job_description: str,
        role_insights: list[dict] | None = None,
        seniority_level: str | None = None,
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

        seniority_context = ""
        if seniority_level:
            seniority_guidance = {
                "graduate": "Target is a GRADUATE/ENTRY-LEVEL role. Emphasize coursework, projects, internships, and eagerness to learn. Tone down leadership language.",
                "junior": "Target is a JUNIOR role. Emphasize hands-on technical work, learning ability, and projects. Keep language confident but not senior.",
                "mid-level": "Target is a MID-LEVEL role. Balance technical depth with some ownership. Show progression and impact.",
                "senior": "Target is a SENIOR role. Emphasize leadership, architecture decisions, mentoring, and measurable business impact.",
                "lead": "Target is a LEAD/MANAGEMENT role. Emphasize team leadership, cross-functional work, technical strategy, and people management.",
                "principal": "Target is a PRINCIPAL/STAFF role. Emphasize org-wide impact, technical vision, and strategic thinking.",
            }
            seniority_context = f"\nSENIORITY CONTEXT:\n{seniority_guidance.get(seniority_level, '')}\n"

        prompt = f"""You are a resume tailoring orchestrator. Analyze the job description and the resume below.
Decide which resume sections need modification and which should stay unchanged.

For each section that needs changes, specify what agent should handle it and what instructions to give.

IMPORTANT RULES:
- Frontmatter (between --- markers at the top) is NEVER modified
- Education and Volunteering sections are almost always kept unchanged in CONTENT
- Only modify sections where the job description demands different emphasis
- For Experience, decide PER ENTRY whether to modify or keep
- Preserve the user's truthful experience -- only change wording and emphasis, never fabricate
- SECTION ORDER: Decide the best order for sections based on seniority and role type.
  For graduate/junior: Summary, Education, Skills, Experience, Projects, Volunteering
  For mid-level+: Summary, Experience, Skills, Education, Projects, Volunteering
  Adjust as appropriate for the specific role.

AVAILABLE AGENTS AND ACTIONS:
- agent: "summary", action: "rewrite" -- rewrite the summary to match job requirements
- agent: "skills", action: "reorder" -- reorder and emphasize relevant skills (with promote/demote lists)
- agent: "experience", entry: "<CompanyKey>", action: "rewrite"|"keep" -- per job entry
- agent: "projects", action: "reorder" -- reorder projects by relevance to job
{insights_context}{seniority_context}
RESUME:
{resume_markdown}

JOB DESCRIPTION:
{job_description}

CRITICAL: Keep your response CONCISE. Instructions must be 1-2 short sentences max. Key requirements and matched strengths should be short phrases, not full sentences. The entire JSON response MUST fit within 4000 tokens.

Respond with a JSON object with this exact structure:
{{
  "analysis": {{
    "role_type": "<category like ai_ml, backend, data_eng, frontend, devops, leadership>",
    "key_requirements": ["<short phrase>", "<short phrase>"],
    "matched_strengths": ["<short phrase>", "<short phrase>"]
  }},
  "tool_calls": [
    {{"agent": "<agent_name>", "action": "<rewrite|reorder|keep>", "entry": "<for experience only>", "instructions": "<1-2 sentences max>", "promote": ["<for reorder>"], "demote": ["<for reorder>"]}}
  ],
  "sections_unchanged": ["<section names to keep verbatim>"],
  "section_order": ["Summary", "Experience", "Skills", "Education", "Projects", "Volunteering and Interests"]
}}"""

        return await self.gemini.generate_json(prompt)
