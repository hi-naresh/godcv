from backend.agents.fabrication import FABRICATION_ALLOWED_BLOCK
from backend.services.gemini import GeminiClient


class ProjectsAgent:
    def __init__(self, gemini: GeminiClient):
        self.gemini = gemini

    async def run(self, section_content: str, instructions: str,
                  job_description: str, extra: dict = None) -> str:
        promote = extra.get("promote", []) if extra else []
        role_type = extra.get("role_type", "") if extra else ""
        candidate_facts = extra.get("candidate_facts", "") if extra else ""
        generate_new = extra.get("generate_projects", False) if extra else False
        candidate_skills = extra.get("candidate_skills", "") if extra else ""
        fabrication_mode = extra.get("fabrication_mode", False) if extra else False
        is_technical = role_type in ("ai_ml", "backend", "data_eng", "frontend", "devops", "fullstack", "")

        if is_technical:
            tech_stack_rule = """- Every project MUST have a tech stack line: **| Stack -** Tech1, Tech2
- Reorder technologies to put JD-relevant ones first
- Only list technologies ACTUALLY used in the project"""
        else:
            tech_stack_rule = """- This is NOT a technical/CS role — do NOT add "| Stack -" lines
- Focus on methodologies, outcomes, and domain-relevant details"""

        if fabrication_mode:
            dont_fabricate_block = (
                FABRICATION_ALLOWED_BLOCK +
                "Per-project rules:\n"
                "- You may upgrade existing project metrics to plausible higher values\n"
                "- You may add capabilities that are plausibly adjacent to what the project actually did\n"
                "- Do NOT change project NAMES or URLs — those remain real"
            )
        else:
            dont_fabricate_block = (
                "4. DON'T FABRICATE: Never add capabilities, metrics, or technologies that weren't part of the project.\n"
                "   Reframing is fine (\"built data pipeline\" → \"engineered scalable research pipeline processing X records\").\n"
                "   Inventing is not (\"built chatbot\" → \"conducted cutting-edge ML research\" — this is a lie)."
            )

        generation_rule = ""
        if generate_new:
            if fabrication_mode:
                generation_rule = f"""
GENERATE NEW PROJECTS:
Generate 1-2 NEW project entries demonstrating JD requirements existing projects don't cover.
Rules:
- Adjacent technologies the candidate hasn't directly used but could plausibly learn are acceptable
- Must be realistic — something they would actually build
- No fake URLs — use "at University" or "Personal" after the name
- Place after real projects

CANDIDATE'S KNOWN SKILLS:
{candidate_skills}
"""
            else:
                generation_rule = f"""
GENERATE NEW PROJECTS:
Generate 1-2 NEW project entries based on the candidate's real skills and coursework that fill JD gaps.
Rules:
- Must use ONLY technologies the candidate already knows
- Must be realistic — something they would actually build
- Must directly demonstrate a JD requirement existing projects don't cover
- No fake URLs — use "at University" or "Personal" after the name
- Place after real projects

CANDIDATE'S KNOWN SKILLS:
{candidate_skills}
"""

        prompt = f"""You are a resume projects strategist. Your job is to make the projects section tell a CONVINCING and TRUTHFUL story of the candidate's fit for this specific role.

{f"CANDIDATE FACTS:{chr(10)}{candidate_facts}{chr(10)}" if candidate_facts else ""}
STRATEGY — Think like the hiring manager reading these projects:

1. RELEVANCE FIRST: Rank projects by how directly they demonstrate JD requirements.
   A project that IS the kind of work the JD describes should come first with expanded detail.
   A project that's tangentially related gets condensed to 1-2 bullets.

2. BE HONEST ABOUT FIT: If a project doesn't demonstrate JD-relevant skills, do NOT force JD buzzwords into it.
   A chatbot project is NOT "ML research" — don't call it that.
   A web app is NOT "quantitative analysis" — don't pretend it is.
   Instead: either condense it (1 bullet showing transferable skills like "deployment", "system design")
   or let the orchestrator exclude it.

3. EXPAND WHAT MATTERS: For the most relevant projects, add detail that maps to specific JD requirements:
   - If JD wants "model validation" and the project has backtesting → expand that aspect
   - If JD wants "scalable pipelines" and the project has data processing → highlight scale/throughput
   - Use the JD's exact terminology where it truthfully applies

{dont_fabricate_block}

WHAT YOU MUST DO:
- Reorder projects: most JD-relevant first
- Expand relevant projects (3-5 bullets for top projects)
- Condense less relevant projects (1-2 bullets)
- Use JD terminology ONLY where it truthfully applies
{tech_stack_rule}
{generation_rule}
OUTPUT HYGIENE — CRITICAL:
- Return ONLY the projects section content. No notes, no commentary, no explanations, no preamble.
- NEVER write meta-text like "Here are the projects aligned as per...", "I've reordered...", "Based on your description...", "Note:", "As requested...", "The projects now reflect..."
- NEVER use AI-detectable filler phrases: "spearheaded", "leveraged cutting-edge", "synergized", "utilized state-of-the-art", "passionate about", "driven by a desire to", "poised to", "adept at", "harnessing the power of", "in order to", "plays a pivotal role", "navigating the complexities", "aims to bridge the gap"
- Write like a real human wrote their own resume — direct, specific, no buzzword stuffing
- Every bullet must sound like something the candidate would actually say about their work

CRITICAL FORMATTING:
- Each project: **[Name](url)** or **Name** on its own line
- PRESERVE ALL markdown links [Name](url) EXACTLY — never remove URLs
- Tech stack: **| Stack -** Tech1, Tech2
- Each bullet on its own line with '- '
- ONE blank line between projects

PROJECTS TO PROMOTE: {', '.join(promote) if promote else 'Most JD-relevant first'}

ORIGINAL PROJECTS:
{section_content}

FULL JOB DESCRIPTION:
{job_description}

SPECIFIC INSTRUCTIONS: {instructions}

Optimized projects section:"""
        return await self.gemini.generate(prompt)
