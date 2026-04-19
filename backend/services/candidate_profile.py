"""Build a structured candidate profile from resume markdown.

Pre-computes facts that agents need so they don't have to infer from raw text.
This prevents hallucinations like "MSc in progress" when it's already completed.
"""

import re
from datetime import date, datetime


def build_candidate_profile(resume_md: str) -> str:
    """Extract key facts from the resume and return a structured context block."""
    today = date.today()
    today_str = today.strftime("%B %Y")

    facts = []
    facts.append(f"TODAY'S DATE: {today_str}")

    # Extract education with completion status
    edu_entries = _parse_education(resume_md, today)
    if edu_entries:
        facts.append("\nEDUCATION STATUS:")
        for e in edu_entries:
            facts.append(f"  - {e['degree']} — {e['status']}")

    # Extract total experience duration
    exp_entries = _parse_experience_dates(resume_md, today)
    if exp_entries:
        total_months = sum(e["months"] for e in exp_entries)
        years = total_months // 12
        months = total_months % 12
        current_roles = [e for e in exp_entries if e["current"]]
        facts.append(f"\nEXPERIENCE: ~{years} years {months} months total, {len(exp_entries)} roles")
        if current_roles:
            facts.append(f"  Currently at: {', '.join(e['company'] for e in current_roles)}")
        else:
            last = exp_entries[0] if exp_entries else None
            if last:
                facts.append(f"  Most recent: {last['company']} (ended {last['end_str']})")

    # Extract all technologies mentioned
    skills = _extract_skills(resume_md)
    if skills:
        facts.append(f"\nALL KNOWN TECHNOLOGIES: {', '.join(skills[:30])}")

    return "\n".join(facts)


def _parse_education(md: str, today: date) -> list[dict]:
    entries = []
    # Match: **Degree - University** *Start – End*
    pattern = re.compile(
        r'\*\*(.+?)\*\*\s*\*(.+?)\s*[–—-]\s*(.+?)\*',
        re.MULTILINE,
    )
    for m in pattern.finditer(md):
        title = m.group(1).strip()
        end_str = m.group(3).strip()

        # Only process education-like entries (degree keywords)
        if not any(k in title.lower() for k in ['m.sc', 'b.sc', 'b.tech', 'msc', 'bsc', 'ph.d', 'phd', 'bachelor', 'master', 'diploma', 'b.a', 'm.a', 'b.eng', 'm.eng']):
            continue

        end_date = _parse_date(end_str)
        if end_date:
            if end_date <= today:
                status = f"COMPLETED ({end_str})"
            else:
                status = f"In progress (expected {end_str})"
        elif 'present' in end_str.lower():
            status = "In progress (currently enrolled)"
        else:
            status = f"Unknown ({end_str})"

        entries.append({"degree": title, "status": status, "end_str": end_str})

    return entries


def _parse_experience_dates(md: str, today: date) -> list[dict]:
    entries = []
    # Match experience headers: **Role — Company** *Start – End*
    pattern = re.compile(
        r'\*\*(.+?[—–-]\s*.+?)\*\*\s*\*(.+?)\s*[–—-]\s*(.+?)\*',
        re.MULTILINE,
    )
    for m in pattern.finditer(md):
        title = m.group(1).strip()
        start_str = m.group(2).strip()
        end_str = m.group(3).strip()

        # Skip education entries
        if any(k in title.lower() for k in ['m.sc', 'b.sc', 'b.tech', 'bachelor', 'master']):
            continue

        company = title.split('—')[-1].split('–')[-1].split('-')[-1].strip()
        company = re.split(r'[\s(]', company)[0]

        is_current = 'present' in end_str.lower()
        start_date = _parse_date(start_str)
        end_date = today if is_current else _parse_date(end_str)

        months = 0
        if start_date and end_date:
            months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
            months = max(1, months)

        entries.append({
            "company": company,
            "months": months,
            "current": is_current,
            "end_str": end_str,
        })

    return entries


def _extract_skills(md: str) -> list[str]:
    """Extract all skills from **Category:** skill1, skill2 lines."""
    skills = []
    for m in re.finditer(r'\*\*[^*]+:\*\*\s*(.+)', md):
        line = m.group(1).strip().rstrip('.')
        for s in line.split(','):
            s = s.strip()
            if s and len(s) < 60:
                skills.append(s)
    return skills


def _parse_date(s: str) -> date | None:
    """Parse a date string like 'Jan 2026', 'January 2026', 'Jun 2024'."""
    s = s.strip()
    for fmt in ('%B %Y', '%b %Y', '%m/%Y'):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None
