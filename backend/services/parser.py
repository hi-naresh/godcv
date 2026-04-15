import re
from collections import OrderedDict


def parse_frontmatter(markdown: str) -> tuple[str, str]:
    """Extract frontmatter and body from markdown.
    Returns (frontmatter_block, body) where frontmatter_block includes --- markers."""
    match = re.match(r'^(---\s*\n[\s\S]*?\n---)\s*\n?([\s\S]*)', markdown)
    if not match:
        return "", markdown
    return match.group(1), match.group(2)


def parse_experience_entries(section_content: str) -> list[dict]:
    """Split experience section into individual job entries.
    Each entry starts with a bold line containing a job title pattern like:
    **Role — Company** *dates*
    """
    entries = []
    parts = re.split(r'(?=^\*\*[^*]+(?:—|–|-)[^*]+\*\*)', section_content, flags=re.MULTILINE)
    for part in parts:
        part = part.strip()
        if not part:
            continue
        title_match = re.match(r'^\*\*([^*]+)\*\*', part)
        title = title_match.group(1).strip() if title_match else "Unknown"
        key = _extract_company_key(title)
        entries.append({"key": key, "title": title, "content": part})
    return entries


def _extract_company_key(title: str) -> str:
    """Extract a short company key from a title like 'AI Data Engineer — BotWot iCX ...'"""
    # First try to split on em-dash or en-dash only (not plain hyphen)
    parts = re.split(r'\s*(?:—|–)\s*', title)
    if len(parts) >= 2:
        company = parts[1].strip()
        return re.split(r'[\s(,]', company)[0]
    # Fall back to plain hyphen split, but take last segment as company
    parts = re.split(r'\s*-\s*', title)
    if len(parts) >= 2:
        company = parts[-1].strip()
        return re.split(r'[\s(,]', company)[0]
    return title[:20]


def parse_project_entries(section_content: str) -> list[dict]:
    """Split projects section into individual project entries.
    Each entry starts with a bold title line like:
    **[ProjectName](url)** | Stack - Tech1, Tech2
    or **ProjectName** | Stack - Tech1, Tech2
    """
    entries = []
    parts = re.split(r'(?=^\*\*[\[{]?.+?\*\*)', section_content, flags=re.MULTILINE)
    for part in parts:
        part = part.strip()
        if not part:
            continue
        title_match = re.match(r'^\*\*\[?([^\]*]+)', part)
        title = title_match.group(1).strip() if title_match else "Unknown"
        key = re.split(r'[\s(\]|]', title)[0]
        entries.append({"key": key, "title": title, "content": part})
    return entries


def parse_sections(body: str) -> tuple[OrderedDict, list[str]]:
    """Parse markdown body into ordered sections.
    Returns (sections_dict, separators_list)."""
    sections = OrderedDict()
    separators = []

    parts = re.split(r'^(# .+)$', body, flags=re.MULTILINE)

    current_key = None
    for part in parts:
        stripped = part.strip()
        if not stripped:
            continue

        if stripped.startswith('# '):
            current_key = stripped[2:].strip()
            sections[current_key] = ""
        elif current_key is not None:
            content = part
            if content.strip() == '---':
                separators.append(current_key)
                continue
            content = re.sub(r'^\s*---\s*$', '', content, flags=re.MULTILINE).strip()
            if content:
                sections[current_key] = content
                if current_key.lower() == "experience":
                    entries = parse_experience_entries(content)
                    if entries:
                        sections[current_key] = {
                            "_full": content,
                            "_entries": entries,
                        }
                if current_key.lower() == "projects":
                    entries = parse_project_entries(content)
                    if entries:
                        sections[current_key] = {
                            "_full": content,
                            "_entries": entries,
                        }
        else:
            if stripped == '---':
                separators.append("_pre")

    return sections, separators


def parse_resume(markdown: str) -> dict:
    """Full resume parser. Returns structured dict with frontmatter, sections, separators."""
    frontmatter, body = parse_frontmatter(markdown)
    sections, separators = parse_sections(body)
    return {
        "frontmatter": frontmatter,
        "sections": sections,
        "separators": separators,
    }
