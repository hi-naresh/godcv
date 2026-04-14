"""Format validator and fixer for AI-generated resume section content.

Post-processes agent outputs to fix common formatting issues such as
collapsed newlines, merged bullet points, missing bold markers, and
excessive whitespace before the resume is assembled.
"""

import re


def validate_and_fix(section_name: str, content: str) -> str:
    """Validate and fix markdown formatting for a given section type."""
    content = _normalize_whitespace(content)

    section_lower = section_name.lower()
    if section_lower == "experience" or section_lower.startswith("experience:"):
        content = _fix_experience(content)
    elif section_lower == "skills":
        content = _fix_skills(content)
    elif section_lower == "summary":
        content = _fix_summary(content)
    elif section_lower == "projects":
        content = _fix_projects(content)

    content = _normalize_whitespace(content)
    return content


def _normalize_whitespace(content: str) -> str:
    """Strip trailing whitespace per line and collapse excess blank lines."""
    lines = [line.rstrip() for line in content.split("\n")]
    result = "\n".join(lines)
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result.strip()


def _fix_experience(content: str) -> str:
    """Fix experience section formatting issues."""
    # Ensure bold title lines are on their own line (text immediately before **)
    content = re.sub(
        r"([^\n])(\*\*[^*]+(?:—|–|-)[^*]+\*\*)", r"\1\n\n\2", content
    )
    # Split bullets joined on same line: "- text. - text" → separate lines
    content = re.sub(r"(\.\s*)- ", r".\n- ", content)
    return content


def _fix_skills(content: str) -> str:
    """Fix skills section formatting issues."""
    # Add blank line between category entries
    content = re.sub(
        r"(\.\s*)\n(\*\*[A-Za-z/]+:?\*\*)", r"\1\n\n\2", content
    )
    # Fix unbolded category headers: "Backend: ..." → "**Backend:** ..."
    content = re.sub(
        r"^([A-Z][A-Za-z /]+):\s", r"**\1:** ", content, flags=re.MULTILINE
    )
    return content


def _fix_summary(content: str) -> str:
    """Fix summary section formatting issues."""
    content = re.sub(r"^#+\s*.*\n?", "", content, flags=re.MULTILINE)
    return content.strip()


def _fix_projects(content: str) -> str:
    """Fix projects section formatting issues."""
    # Ensure project title lines (with links) are on their own line
    content = re.sub(r"([^\n])(\*\*\[[^\]]+\])", r"\1\n\n\2", content)
    # Ensure project title lines (with pipe) are on their own line
    content = re.sub(
        r"([^\n])(\*\*[A-Z][^*]*\*\*\s*\|)", r"\1\n\n\2", content
    )
    return content
