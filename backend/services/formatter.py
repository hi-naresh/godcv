"""Format validator and fixer for AI-generated resume section content.

Post-processes agent outputs to fix common formatting issues such as
collapsed newlines, merged bullet points, missing bold markers, and
excessive whitespace before the resume is assembled.
"""

import re


# Pattern for experience entry titles: **Role — Company** or **Role – Company** or **Role - Company**
# Must contain a dash variant (—, –, -) to distinguish from inline bold text
_EXP_TITLE_RE = re.compile(
    r'^\*\*[^*]+(?:—|–)\s*[^*]+\*\*',  # Only em-dash or en-dash (not plain hyphen which appears in inline text)
    re.MULTILINE,
)


def validate_and_fix(section_name: str, content: str) -> str:
    """Validate and fix markdown formatting for a given section type."""
    # First: fix broken bold markers (bold text split across lines)
    content = _fix_broken_bold(content)
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


def _fix_broken_bold(content: str) -> str:
    """Rejoin bold markers that are split across lines.

    Fixes cases like:
        **multi-agent CRM\n** → **multi-agent CRM**
        **reliable RAG workflows\n** → **reliable RAG workflows**
        **validation strategies\n\n** for → **validation strategies** for

    Must NOT touch:
        - Lines starting with **Title — Company** (experience entries)
        - Lines starting with **Category:** (skills categories)
    """
    # Fix: bold text where closing ** is on the next line(s)
    # e.g., "**multi-agent CRM\n**" or "**strategies\n\n**"
    # Only match when the closing ** is followed by a space/word (not a title pattern)
    content = re.sub(
        r'\*\*([^*\n]+)\s*\n+\*\*(?=\s+[a-z]|[.,;)\s])',
        r'**\1**',
        content,
    )
    # Also catch: closing ** at start of line with nothing after, or followed by period
    content = re.sub(
        r'\*\*([^*\n]+)\s*\n+\*\*(?=\.|\s*$)',
        r'**\1**',
        content,
    )
    # Fix: newline between text and **lowercase-word (inline bold pushed to next line)
    # "deliver\n**high-quality" → "deliver **high-quality"
    # Only when lowercase follows (not uppercase which could be a title/category)
    content = re.sub(
        r'(\S)\s*\n+(\*\*[a-z])',
        r'\1 \2',
        content,
    )
    return content


def _normalize_whitespace(content: str) -> str:
    """Strip trailing whitespace per line and collapse excess blank lines."""
    lines = [line.rstrip() for line in content.split("\n")]
    result = "\n".join(lines)
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result.strip()


def _is_experience_title(line: str) -> bool:
    """Check if a line is an experience entry title (not just inline bold text).

    Must match pattern: **Role — Company** or **Role – Company**
    with em-dash or en-dash (not plain hyphen which appears in many inline contexts).
    """
    stripped = line.strip()
    return bool(re.match(r'^\*\*[^*]+(?:—|–)[^*]+\*\*', stripped))


def _fix_experience(content: str) -> str:
    """Fix experience section formatting issues."""
    # Fix text running directly into a title on the same line (no newline at all)
    # e.g., "Some text**Senior Engineer — Acme Corp**" → "Some text\n\n**Senior..."
    content = re.sub(
        r'([^\n\*])(\*\*[^*]+(?:—|–)[^*]+\*\*)',
        r'\1\n\n\2',
        content,
    )
    # Ensure blank line before experience entry titles (not inline bold)
    lines = content.split('\n')
    result_lines = []
    for i, line in enumerate(lines):
        if _is_experience_title(line) and i > 0:
            # Check if previous non-empty line exists and isn't already a blank line
            prev = result_lines[-1] if result_lines else ''
            if prev.strip():  # Previous line has content → insert blank line
                result_lines.append('')
        result_lines.append(line)
    content = '\n'.join(result_lines)

    # Split bullets joined on same line: "- text. - text" → separate lines
    content = re.sub(r'(\.\s*)- ', r'.\n- ', content)
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
