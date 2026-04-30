from backend.services.gemini import GeminiClient
from backend.agents.stealth import STEALTH_ALLOWED_BLOCK, STRICT_BLOCK


class OrchestratorAgent:
    def __init__(self, gemini: GeminiClient):
        self.gemini = gemini

    async def analyze(
        self,
        resume_markdown: str,
        job_description: str,
        role_insights: list[dict] | None = None,
        role_level: str | None = None,
        page_mode: str = "single",
        entry_keys: dict | None = None,
        stealth_mode: bool = False,
        max_projects: int = 4,
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

        role_level_context = ""
        if role_level:
            role_level_guidance = {
                "graduate": (
                    "Target is a GRADUATE-level role. Lead with education, coursework, "
                    "internships, and projects. Tone: capable and eager. Avoid leadership "
                    "or architectural claims."
                ),
                "non-graduate": (
                    "Target is a non-graduate professional role. Lead with experience and "
                    "impact. Show ownership, scale, and measurable outcomes appropriate to "
                    "the seniority signaled in the JD (mid-level vs senior vs lead vs principal)."
                ),
            }
            role_level_context = f"\nROLE LEVEL CONTEXT:\n{role_level_guidance.get(role_level, '')}\n"

        from backend.services.candidate_profile import build_candidate_profile
        candidate_facts = build_candidate_profile(resume_markdown)

        stealth_notice = STEALTH_ALLOWED_BLOCK if stealth_mode else STRICT_BLOCK

        projects_count_rule = (
            f"PROJECTS COUNT: Always select up to {max_projects} projects total — rank by JD relevance, "
            f"\"exclude\" the rest. Aim for {max_projects} unless fewer projects strongly demonstrate fit. "
            f"If generate_projects is set on a tool_call, those generated entries count toward this {max_projects} total "
            f"(so existing projects must be reduced accordingly)."
        )

        if stealth_mode:
            generate_projects_rule = (
                "    1-2 new project entries demonstrating JD-relevant skills. "
                "Adjacent technologies the candidate hasn't directly used but could plausibly learn are acceptable.\n"
            )
        else:
            generate_projects_rule = (
                "    NEVER set generate_projects in strict mode — fabricated projects are forbidden.\n"
            )

        prompt = f"""You are a resume tailoring orchestrator. Analyze the job description and the resume below.

CANDIDATE FACTS (pre-computed — trust these, do NOT re-interpret dates yourself):
{candidate_facts}

Use the CANDIDATE FACTS above as ground truth. If it says a degree is COMPLETED, it IS completed — do not contradict this anywhere in your response (analysis, scoring, or gap_suggestions).

STEP 1: Extract the job title, company name, and role level from the JD.
STEP 2: Decide which resume sections need modification and which should stay unchanged.
STEP 3: For each section that needs changes, specify what agent should handle it and what instructions to give.

IMPORTANT RULES:
- Frontmatter (between --- markers at the top) is NEVER modified
- Volunteering section is almost always kept unchanged
- The candidate's REAL work and achievements must be preserved — you refine how they're PRESENTED, not what they did
- For Experience: the company, role, and core work are FIXED truths. What changes is EMPHASIS, KEYWORDS, and FRAMING
- For Projects: these demonstrate capability. Rewrite bullets to highlight JD-relevant skills demonstrated

STRATEGY — Think like a recruiter reading this resume for the JD:
1. What keywords/skills does the JD REQUIRE? Map each to the resume
2. Which experience entries demonstrate those skills? Those get "rewrite" to emphasize the overlap
3. Which projects prove the candidate can do what the JD asks? Promote and rewrite those
4. Skills section should lead with what the JD values most

AVAILABLE AGENTS AND ACTIONS:
- agent: "summary", action: "rewrite" — rewrite to lead with the candidate's strongest JD-match
- agent: "skills", action: "reorder" — reorder categories and skills within them; promote JD-relevant, demote others
- agent: "experience", entry: "<CompanyKey>", action: "rewrite"|"include"|"exclude"
  - "rewrite": reframe bullets using JD keywords and terminology (most entries should be rewritten)
  - "include": keep as-is only if already well-aligned with JD
  - "exclude": drop only if completely irrelevant AND space is needed
  - INSTRUCTIONS must say WHICH JD requirements this entry should emphasize
- agent: "projects", entry: "<ProjectKey>", action: "rewrite"|"include"|"exclude"
  - "rewrite": INSTRUCTIONS must be SPECIFIC about this project's relevance:
    - Is this project DIRECTLY relevant? → "EXPAND: this demonstrates [JD skill X, Y]. Highlight [specific aspect]."
    - Is it tangentially relevant? → "CONDENSE to 1-2 bullets. Only highlight [transferable skill]."
    - Is it irrelevant? → use "exclude" instead
  - Do NOT tell the agent to force JD buzzwords into irrelevant projects — that's dishonest
  - You may set "generate_projects": true on ONE projects tool_call (without entry) to generate
{generate_projects_rule}
- agent: "education", action: "rewrite" — reorder coursework to lead with JD-relevant topics
  - Only changes coursework lists, NOT degrees/universities/dates

DO NOT use agent: "publications" — it is not available.
{stealth_notice}

ENTRY SELECTION RULES:
- You MUST provide an action for EVERY experience and project entry
- You MUST use the EXACT entry keys provided in the ENTRY KEYS section below (if provided)
- DEFAULT to "rewrite" — only use "include" if the entry is already perfectly aligned
- Prefer entries most relevant to the job description
- When excluding, drop the least relevant entries first
{insights_context}{role_level_context}
PAGE MODE: {"MULTI-PAGE — Include ALL experience entries. No exclusions for space. Agents can add richer content." if page_mode == "multi" else "SINGLE-PAGE — Select experience entries to fit one page (typically 2-3)."}
{projects_count_rule}
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
- Do NOT contradict CANDIDATE FACTS above. If it says a degree is COMPLETED, do not list it as a gap.

CRITICAL: Keep your response CONCISE. Instructions must be 1-2 short sentences max. Key requirements and matched strengths should be short phrases, not full sentences.

Respond with a JSON object:
{{
  "analysis": {{
    "job_title": "<exact role title from JD, e.g. Graduate Data Engineer>",
    "company": "<company name from JD, e.g. Capgemini>",
    "role_level": "<graduate|non-graduate>",
    "role_type": "<ai_ml|backend|data_eng|frontend|devops|leadership|fullstack>",
    "key_requirements": ["<short phrase>"],
    "matched_strengths": ["<short phrase>"]
  }},
  "tool_calls": [
    {{"agent": "<name>", "action": "<rewrite|reorder|include|exclude|keep>", "entry": "<for experience/projects>", "instructions": "<1-2 sentences>", "promote": ["<items>"], "demote": ["<items>"]}}
  ],
  "sections_unchanged": ["<section names>"],
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
