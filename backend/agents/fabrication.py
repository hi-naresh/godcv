"""Shared prompt blocks for fabrication mode.

When fabrication_mode is False (default), agents use their existing strict
"no fabrication" wording. When True, that wording is replaced with the
FABRICATION_ALLOWED_BLOCK below — subtle plausibility-bounded invention.
"""

FABRICATION_ALLOWED_BLOCK = """FABRICATION ALLOWED — PLAUSIBILITY GUARDRAILS:
You may invent metrics, bullets, projects, coursework, or skills to strengthen JD fit.
Constraints:
- Must be PLAUSIBLE for this candidate's seniority, role, company, and degree
- Must be MINOR additions — small upgrades that show potential to excel, not bold claims
- Must be CONSISTENT with the candidate's actual tech stack and background
- No leadership-scale claims for graduate/junior candidates
- No metrics outside believable ranges for the role/seniority
- No technologies the candidate has zero exposure to
- No employers, degrees, or job titles invented from scratch
"""
