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
        page_mode: str = "single",
        entry_keys: dict | None = None,
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

        # Determine section order example based on seniority
        # Note: Publications is optional — only include in section_order if you're creating one
        if seniority_level in ("graduate", "junior"):
            order_example = '["Summary", "Education", "Skills", "Experience", "Projects", "Publications (optional)", "Volunteering and Interests"]'
            order_rule = "For graduate/junior roles: Education MUST come BEFORE Experience and Skills."
        else:
            order_example = '["Summary", "Experience", "Skills", "Education", "Projects", "Publications (optional)", "Volunteering and Interests"]'
            order_rule = "For mid-level+ roles: Experience comes first, then Skills, then Education."

        prompt = f"""You are a resume tailoring orchestrator. Analyze the job description and the resume below.

STEP 1: Extract the job title, company name, and position level from the JD.
STEP 2: Decide which resume sections need modification and which should stay unchanged.
STEP 3: For each section that needs changes, specify what agent should handle it and what instructions to give.

IMPORTANT RULES:
- Frontmatter (between --- markers at the top) is NEVER modified
- Volunteering section is almost always kept unchanged
- Only modify sections where the job description demands different emphasis
- For Experience, decide PER ENTRY whether to modify or keep
- Preserve the user's truthful experience -- only change wording and emphasis, never fabricate
- SECTION ORDER: {order_rule}

AVAILABLE AGENTS AND ACTIONS:
- agent: "summary", action: "rewrite" -- rewrite the summary to match job requirements
- agent: "skills", action: "reorder" -- reorder and emphasize relevant skills (with promote/demote lists)
- agent: "experience", entry: "<CompanyKey>", action: "rewrite"|"include"|"exclude" -- per job entry
  - "include": keep this entry as-is (relevant, no changes needed)
  - "exclude": drop this entry entirely (not relevant for this role)
  - "rewrite": include but rewrite bullets to better match the JD
- agent: "projects", entry: "<ProjectKey>", action: "rewrite"|"include"|"exclude" -- per project entry
  - Same include/exclude/rewrite logic as experience
  - Prioritize projects whose tech stack matches the JD
- agent: "education", action: "rewrite" -- refine coursework emphasis (reorder courses, align terminology with JD)
  - Use when the JD has specific technical requirements that match coursework topics
  - The agent will NOT change degrees/universities/dates — only coursework lists
- agent: "publications", action: "create" -- generate a Publications section
  - ONLY use when the JD explicitly values research, publications, or academic output
  - OR when adding publications would give a meaningful edge (research roles, PhD-level positions, academic jobs)
  - The agent creates entries from the candidate's coursework projects and thesis work
  - Do NOT use for standard industry roles that don't value publications

ENTRY SELECTION RULES:
- You MUST provide an action for EVERY experience and project entry (include, exclude, or rewrite)
- You MUST use the EXACT entry keys provided in the ENTRY KEYS section below (if provided)
- Prefer entries most relevant to the job description
- When excluding, drop the least relevant entries first
{insights_context}{seniority_context}
PAGE MODE: {"MULTI-PAGE — Include ALL entries. No need to exclude entries for space. Agents can add richer content." if page_mode == "multi" else "SINGLE-PAGE — Select entries to fit one page. Typically 2-3 experience entries and 2-3 projects."}
{self._entry_keys_context(entry_keys)}
RESUME:
{resume_markdown}

JOB DESCRIPTION:
{job_description}

SCORING: You MUST also evaluate the ORIGINAL resume as-is against the JD and provide "before" scores:
- keyword_match: percentage of important JD keywords/phrases found in the resume (0-100)
- skills_coverage: percentage of JD required skills present in the Skills section (0-100)
- experience_fit: one sentence describing how experience level matches (years, seniority, domain)
- overall_fit: aggregated score considering all factors (0-100)

For "gap_suggestions" — list specific weaknesses the candidate has for THIS job:
- Missing skills the JD requires but resume doesn't have at all
- Experience gaps (years, seniority level, domain mismatch)
- Missing project types or technologies
- Soft skill gaps (leadership, mentoring, etc.)
- Be brutally honest — these help the user understand what tailoring alone cannot fix

CRITICAL: Keep your response CONCISE. Instructions must be 1-2 short sentences max. Key requirements and matched strengths should be short phrases, not full sentences.

Respond with a JSON object:
{{
  "analysis": {{
    "job_title": "<exact role title from JD, e.g. Graduate Data Engineer>",
    "company": "<company name from JD, e.g. Capgemini>",
    "position_level": "<graduate|junior|mid-level|senior|lead|principal>",
    "role_type": "<ai_ml|backend|data_eng|frontend|devops|leadership|fullstack>",
    "key_requirements": ["<short phrase>"],
    "matched_strengths": ["<short phrase>"]
  }},
  "tool_calls": [
    {{"agent": "<name>", "action": "<rewrite|reorder|include|exclude|keep>", "entry": "<for experience/projects>", "instructions": "<1-2 sentences>", "promote": ["<items>"], "demote": ["<items>"]}}
  ],
  "sections_unchanged": ["<section names>"],
  "section_order": {order_example},
  "scoring": {{
    "before": {{
      "keyword_match": "<0-100>",
      "skills_coverage": "<0-100>",
      "experience_fit": "<one sentence>",
      "overall_fit": "<0-100>"
    }},
    "gap_suggestions": ["<specific weakness 1>", "<specific weakness 2>"]
  }}
}}"""

        return await self.gemini.generate_json(prompt)

    @staticmethod
    def _entry_keys_context(entry_keys: dict | None) -> str:
        if not entry_keys:
            return ""
        lines = ["ENTRY KEYS (use these EXACT keys in tool_calls):"]
        for section, keys in entry_keys.items():
            for k in keys:
                lines.append(f'  - agent: "{section.lower()}", entry: "{k["key"]}" (= {k["title"][:60]})')
        return "\n".join(lines) + "\n"
