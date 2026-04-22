"""Format validator and fixer for AI-generated resume section content.

Post-processes agent outputs to fix common formatting issues such as
collapsed newlines, merged bullet points, missing bold markers, and
excessive whitespace before the resume is assembled.
"""

import re


# Pattern for experience entry titles: **Role — Company** or **Role – Company** or **Role - Company**
# Must contain a dash variant (—, –, -) to distinguish from inline bold text
_EXP_TITLE_RE = re.compile(
    r'^\*\*.+?(?:—|–)\s*.+?\*\*',  # Only em-dash or en-dash (not plain hyphen which appears in inline text)
    re.MULTILINE,
)

# Lines that are pure AI meta-commentary (not resume content)
_AI_META_LINE_RE = re.compile(
    r'^\s*(?:'
    r'(?:Here\s+(?:is|are)\s+(?:the|your|my))|'
    r'(?:I\'ve\s+(?:aligned|rewritten|reordered|refined|updated|crafted|optimized|tailored|reorganized|restructured))|'
    r'(?:Based\s+on\s+(?:your|the)\s+(?:description|JD|job|profile|resume|requirements))|'
    r'(?:As\s+(?:requested|per\s+your|instructed))|'
    r'(?:Note(?:\s*:|\s+that))|'
    r'(?:The\s+(?:projects|experience|skills|summary|education|section)\s+(?:section\s+)?(?:has been|have been|is now|are now|now\s+reflect))|'
    r'(?:This\s+(?:entry|section|summary)\s+now)|'
    r'(?:Key\s+changes?\s*(?:made|:))|'
    r'(?:Changes?\s+made\s*:)|'
    r'(?:Let\s+me\s+know)|'
    r'(?:Hope\s+this\s+helps)|'
    r'(?:Feel\s+free\s+to)'
    r')',
    re.IGNORECASE,
)

# AI filler phrases that should be replaced with simpler alternatives within resume text
_AI_PHRASE_REPLACEMENTS = [
    (re.compile(r'\bspearheaded\b', re.IGNORECASE), 'led'),
    (re.compile(r'\bleveraged cutting-edge\b', re.IGNORECASE), 'used'),
    (re.compile(r'\bleveraged\b', re.IGNORECASE), 'used'),
    (re.compile(r'\butilized state-of-the-art\b', re.IGNORECASE), 'used'),
    (re.compile(r'\butilized\b', re.IGNORECASE), 'used'),
    (re.compile(r'\bsynergized\b', re.IGNORECASE), 'combined'),
    (re.compile(r'\bin order to\b', re.IGNORECASE), 'to'),
    (re.compile(r'\bharnessing the power of\b', re.IGNORECASE), 'using'),
    (re.compile(r'\bplays a pivotal role\b', re.IGNORECASE), 'is key'),
    (re.compile(r'\bplayed a pivotal role\b', re.IGNORECASE), 'was key'),
    (re.compile(r'\bpivotal role in\b', re.IGNORECASE), 'key role in'),
    (re.compile(r'\bnavigating the complexities of\b', re.IGNORECASE), 'handling'),
    (re.compile(r'\baims to bridge the gap\b', re.IGNORECASE), 'connects'),
    (re.compile(r'\bdriven by a desire to\b', re.IGNORECASE), 'motivated to'),
    (re.compile(r'\bpoised to\b', re.IGNORECASE), 'ready to'),
    (re.compile(r'\badept at\b', re.IGNORECASE), 'skilled in'),
    (re.compile(r'\bpassionate about\b', re.IGNORECASE), 'focused on'),
    (re.compile(r'\bseamlessly\b', re.IGNORECASE), ''),
    (re.compile(r'\bholistic\b', re.IGNORECASE), 'complete'),
    (re.compile(r'\brobust and scalable\b', re.IGNORECASE), 'scalable'),
    (re.compile(r'\bcutting-edge\b', re.IGNORECASE), 'modern'),
    (re.compile(r'\bstate-of-the-art\b', re.IGNORECASE), 'modern'),
    (re.compile(r'\bfostered\b', re.IGNORECASE), 'built'),
    (re.compile(r'\bfacilitated\b', re.IGNORECASE), 'led'),
    (re.compile(r'\borchestrated\b(?!\s+(?:container|deployment|service|workflow|pipeline))', re.IGNORECASE), 'coordinated'),
    (re.compile(r'\bpioneered\b', re.IGNORECASE), 'introduced'),
    (re.compile(r'\bchampioned\b', re.IGNORECASE), 'promoted'),
    (re.compile(r'\bempowered\b', re.IGNORECASE), 'enabled'),
]


def validate_and_fix(section_name: str, content: str) -> str:
    """Validate and fix markdown formatting for a given section type."""
    # First: strip AI meta-commentary and filler phrases
    content = strip_ai_artifacts(content)
    # Fix broken bold markers (bold text split across lines)
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
    elif section_lower == "education":
        content = _fix_education(content)

    content = _normalize_whitespace(content)
    return content


def strip_ai_artifacts(content: str) -> str:
    """Remove AI meta-commentary lines and replace AI filler phrases.

    Strips lines that are pure AI commentary (e.g., "Here is the rewritten entry...")
    and replaces overused AI phrases with natural alternatives.
    """
    # Remove full lines that are AI meta-commentary
    lines = content.split("\n")
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()
        # Skip empty lines (preserve them) or lines that are resume content
        if not stripped:
            cleaned_lines.append(line)
            continue
        # Skip lines that are AI meta-commentary
        if _AI_META_LINE_RE.match(stripped):
            continue
        # Skip lines that are just trailing AI notes (often after a blank line at end)
        if stripped.startswith("---") and not any(
            l.strip().startswith("---") for l in cleaned_lines[:3]
        ):
            # Only skip separators that aren't frontmatter
            continue
        cleaned_lines.append(line)

    content = "\n".join(cleaned_lines)

    # Replace AI filler phrases with natural alternatives
    for pattern, replacement in _AI_PHRASE_REPLACEMENTS:
        content = pattern.sub(replacement, content)

    # Clean up double spaces left by empty replacements
    content = re.sub(r'  +', ' ', content)

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
    return bool(re.match(r'^\*\*.+?(?:—|–).+?\*\*', stripped))


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

    # Ensure "Stack Used:" (bold or not) is on its own line after the title line
    # Fix: title line merged with Stack Used on same line
    content = re.sub(
        r'(\*[^\n]+)\s*\n?(\*?\*?Stack Used:)',
        r'\1\n\2',
        content,
    )
    # Normalize "Stack Used:" to bold format: "Stack Used:" → "**Stack Used:**"
    content = re.sub(
        r'^Stack Used:\s*', '**Stack Used:** ', content, flags=re.MULTILINE
    )
    # Also catch "**Stack Used:**" that got merged onto previous line without newline
    content = re.sub(
        r'([^\n])(\*\*Stack Used:\*\*)',
        r'\1\n\2',
        content,
    )
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


def _fix_education(content: str) -> str:
    """Fix education section formatting issues."""
    # Ensure Coursework line is on its own line after the degree line
    # Handles all variants: ***Coursework**, **Coursework:, plain Coursework:
    # The pattern matches any non-newline char before Coursework-related markers
    content = re.sub(
        r'([^\n])\s*(\*{0,3}Coursework)',
        lambda m: m.group(1) + '\n' + m.group(2) if m.group(1) != '\n' else m.group(0),
        content,
    )
    # Ensure blank line between degree entries
    # A degree entry starts with **Degree — University** or **Degree - University**
    content = re.sub(
        r'(\.\s*)\n(\*\*[A-Z])',
        r'\1\n\n\2',
        content,
    )
    return content


def _fix_projects(content: str) -> str:
    """Fix projects section formatting issues."""
    # Ensure project title lines (with links) are on their own line
    content = re.sub(r"([^\n])(\*\*\[[^\]]+\])", r"\1\n\n\2", content)
    # Ensure project title lines (with pipe) are on their own line
    content = re.sub(
        r"([^\n])(\*\*[A-Z][^*]*\*\*\s*\|)", r"\1\n\n\2", content
    )
    # Normalize "| Stack -" to bold format: "| Stack -" → "**| Stack -**"
    content = re.sub(
        r'(?<!\*)\| Stack -(?!\*)', '**| Stack -**', content
    )
    return content
