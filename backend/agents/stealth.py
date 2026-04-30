"""Shared prompt blocks for stealth mode (the rebrand of fabrication mode).

When stealth_mode is False (default), agents use STRICT_BLOCK — rewrite-only.
When True, agents use STEALTH_ALLOWED_BLOCK — match-first → reshape → invent
for gaps with believability guardrails.
"""

STRICT_BLOCK = """STRICT MODE:
Use ONLY content present in the master CV. You may reorder, rephrase,
promote, demote, and tighten language. You may NOT invent bullets,
metrics, projects, skills, or any content not derivable from the
master CV.
"""


STEALTH_ALLOWED_BLOCK = """STEALTH MODE — IDEAL CV CONSTRUCTION:
Your job is to produce the strongest possible CV for this JD.

Hierarchy (in order):
1. MATCH-FIRST. Scan the master CV for content that already maps to JD
   requirements. Use those bullets, projects, and skills verbatim (or
   lightly reshape) — they are the strongest evidence.
2. RESHAPE. For partial matches, rephrase emphasis and terminology to
   mirror the JD's language without changing facts.
3. INVENT ONLY FOR GAPS. Where a JD requirement has no coverage in the
   master CV, you may add believable, candidate-consistent content to
   fill it.

Each invented item must be:
- Plausible for this candidate's seniority, role, company, and degree
- Consistent with their actual stack (no technologies they have zero
  exposure to)
- Bounded — minor upgrades, not bold claims
- Within believable metric ranges for the role

Never invent: employers, job titles, degrees, leadership-scale claims
for graduate-level roles.
"""
