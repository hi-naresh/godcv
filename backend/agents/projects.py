from backend.agents.stealth import STEALTH_ALLOWED_BLOCK, STRICT_BLOCK
from backend.services.gemini import GeminiClient


class ProjectsAgent:
    def __init__(self, gemini: GeminiClient):
        self.gemini = gemini

    async def run(self, section_content: str, instructions: str,
                  job_description: str, extra: dict = None) -> str:
        role_type = extra.get("role_type", "") if extra else ""
        candidate_facts = extra.get("candidate_facts", "") if extra else ""
        stealth_mode = extra.get("stealth_mode", False) if extra else False
        max_bullets = extra.get("max_bullets_per_entry", 3) if extra else 3
        require_quant = extra.get("require_quantified_bullets", True) if extra else True

        is_technical = role_type in ("ai_ml", "backend", "data_eng", "frontend", "devops", "fullstack", "")

        if is_technical:
            tech_stack_rule = (
                "- Every project MUST have a tech stack line immediately after the title: **| Stack -** Tech1, Tech2, ...\n"
                "- Reorder technologies to put JD-relevant ones first\n"
                "- Only list technologies ACTUALLY used in this project — do not add ones just because the JD mentions them"
            )
        else:
            tech_stack_rule = (
                "- This is NOT a technical/CS role — do NOT add '| Stack -' lines\n"
                "- Focus on methodologies, outcomes, and domain-relevant details"
            )

        if max_bullets <= 1:
            bullet_count_rule = "- Use exactly 1 bullet — make it the strongest JD-relevant achievement"
        elif max_bullets == 2:
            bullet_count_rule = "- Use 1-2 bullets"
        else:
            bullet_count_rule = (
                f"- Default to 2 bullets; use up to {max_bullets} ONLY if each additional bullet demonstrates a "
                f"clearly distinct JD-relevant skill or outcome"
            )

        if require_quant:
            quantified_rule = (
                "- Every bullet MUST include a quantified result (numbers, percentages, $ amounts, scale, throughput, "
                "or time saved). If the original has a number, keep it exactly — do NOT change metrics."
            )
        else:
            quantified_rule = "- Prefer quantified results where they exist in the original — do NOT invent numbers"

        if stealth_mode:
            fabrication_block = (
                STEALTH_ALLOWED_BLOCK +
                "- You may upgrade existing project metrics to plausible higher values\n"
                "- You may add capabilities plausibly adjacent to what the project actually did\n"
                "- Do NOT change project names or URLs — those remain real"
            )
        else:
            fabrication_block = (
                STRICT_BLOCK +
                "WHAT THIS MEANS FOR PROJECTS:\n"
                "- Reframing is fine: 'built data pipeline' → 'engineered ETL pipeline processing 500K records/day'\n"
                "- Invention is not: 'built web app' → 'conducted ML research' — this is a lie, do not do it\n"
                "- Do NOT add technologies to the Stack line that were not part of this project\n"
                "- Do NOT change any existing number, percentage, or metric — if original says 60%, keep 60%\n"
                "- Do NOT force JD buzzwords into bullets where they don't truthfully apply"
            )

        # Parse the relevance signal from orchestrator instructions
        expand_condense_guidance = ""
        instr_lower = instructions.lower()
        if "expand" in instr_lower:
            expand_condense_guidance = (
                "RELEVANCE: This project is DIRECTLY relevant to the JD. "
                f"Use up to {max_bullets} bullets — go into depth on the specific aspects called out in the instructions. "
                "Make the reader feel this project IS the kind of work the JD describes."
            )
        elif "condense" in instr_lower:
            expand_condense_guidance = (
                "RELEVANCE: This project is only TANGENTIALLY relevant. "
                "Use 1 bullet maximum — highlight only the transferable skill that matters for this JD. "
                "Don't pad with unrelated achievements."
            )
        else:
            expand_condense_guidance = (
                "RELEVANCE: Moderate — rewrite bullets to foreground JD-relevant aspects, but only where they truthfully apply."
            )

        prompt = f"""You are rewriting ONE project entry for a resume. Your job: present this project's REAL work in the language the hiring manager cares about.

{f"CANDIDATE FACTS:{chr(10)}{candidate_facts}{chr(10)}" if candidate_facts else ""}
{expand_condense_guidance}

{fabrication_block}

WHAT YOU SHOULD DO:
- Read the instructions carefully — they tell you EXACTLY which JD skill this project demonstrates and what to highlight
- Rewrite bullets to use JD terminology where it GENUINELY applies to what this project did
- Use strong action verbs that match the candidate's actual contribution (built, designed, trained, deployed, analyzed...)
- Make the most JD-relevant achievement the first bullet
{bullet_count_rule}
{quantified_rule}
{tech_stack_rule}

WHAT YOU MUST NOT DO:
- Do NOT write bullets that sound like a job listing — "This project enabled X to Y" is not how humans write resumes
- Do NOT use any of these AI-detectable phrases: "spearheaded", "leveraged cutting-edge", "synergized", "utilized state-of-the-art", "passionate about", "driven by", "poised to", "adept at", "harnessing the power of", "plays a pivotal role", "navigating the complexities", "aims to bridge the gap", "robust", "scalable solution", "end-to-end"
- Do NOT start every bullet with the same verb
- Do NOT invent capabilities, tools, or outcomes that aren't in the original
- Do NOT fabricate numbers if the original has none — use scale descriptors instead ("large dataset", "production system")

OUTPUT HYGIENE — CRITICAL:
- Return ONLY the rewritten project entry. No notes, no commentary, no preamble, no meta-text.
- NEVER write: "Here is the rewritten project", "I've aligned this with...", "Note:", "As requested...", "This project now reflects..."

FORMATTING:
- Project title line EXACTLY as original (preserve markdown links [Name](url) character-for-character)
- Tech stack line immediately after title (if applicable): **| Stack -** Tech1, Tech2
- Each bullet on its own line starting with '- '

SPECIFIC INSTRUCTIONS FROM ORCHESTRATOR:
{instructions}

ORIGINAL PROJECT ENTRY:
{section_content}

JOB DESCRIPTION:
{job_description}

Rewritten project entry:"""
        return await self.gemini.generate(prompt)
