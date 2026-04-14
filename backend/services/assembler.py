from collections import OrderedDict


def assemble_resume(
    original_parsed: dict,
    modified_sections: dict[str, str],
    modified_experience_entries: dict[str, str] | None = None,
) -> str:
    """Reconstruct full resume markdown from original + modifications.

    Args:
        original_parsed: Output of parse_resume()
        modified_sections: Dict of section_name -> new markdown content (only modified sections)
        modified_experience_entries: Dict of entry_key -> new markdown content (only modified entries)

    Rules:
        1. Frontmatter: always from original, verbatim
        2. Sections in original order; use modified version if present, else original verbatim
        3. Experience: per-entry replacement; unmodified entries preserved verbatim
        4. Separators restored between sections
    """
    parts = []

    if original_parsed["frontmatter"]:
        parts.append(original_parsed["frontmatter"])

    sections = original_parsed["sections"]
    section_keys = list(sections.keys())

    for i, key in enumerate(section_keys):
        parts.append(f"\n# {key}")
        original = sections[key]

        if key in modified_sections:
            parts.append(modified_sections[key])
        elif isinstance(original, dict) and "_entries" in original and modified_experience_entries:
            entry_parts = []
            for entry in original["_entries"]:
                if entry["key"] in modified_experience_entries:
                    entry_parts.append(modified_experience_entries[entry["key"]])
                else:
                    entry_parts.append(entry["content"])
            parts.append("\n".join(entry_parts))
        elif isinstance(original, dict) and "_full" in original:
            parts.append(original["_full"])
        else:
            parts.append(str(original))

        if i < len(section_keys) - 1:
            parts.append("\n---")

    return "\n".join(parts) + "\n"
