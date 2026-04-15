from collections import OrderedDict


def assemble_resume(
    original_parsed: dict,
    modified_sections: dict[str, str],
    modified_experience_entries: dict[str, str] | None = None,
    section_order: list[str] | None = None,
    excluded_entries: set[str] | None = None,
) -> str:
    """Reconstruct full resume markdown from original + modifications.

    Args:
        original_parsed: Output of parse_resume()
        modified_sections: Dict of section_name -> new markdown content (only modified sections)
        modified_experience_entries: Dict of entry_key -> new markdown content (only modified entries)
        section_order: Optional ordered list of section names to reorder output

    Rules:
        1. Frontmatter: always from original, verbatim
        2. Sections in specified order (or original order if not given)
        3. Use modified version if present, else original verbatim
        4. Experience: per-entry replacement; unmodified entries preserved verbatim
        5. Separators restored between sections
    """
    parts = []

    if original_parsed["frontmatter"]:
        parts.append(original_parsed["frontmatter"])

    sections = original_parsed["sections"]
    original_keys = list(sections.keys())

    # Determine section order
    if section_order:
        # Match plan section names to actual keys (case-insensitive)
        ordered_keys = []
        remaining = list(original_keys)
        for planned in section_order:
            for key in remaining:
                if key.lower() == planned.lower():
                    ordered_keys.append(key)
                    remaining.remove(key)
                    break
        # Append any sections not mentioned in the plan
        ordered_keys.extend(remaining)
    else:
        ordered_keys = original_keys

    for i, key in enumerate(ordered_keys):
        parts.append(f"\n# {key}")
        original = sections[key]

        if key in modified_sections:
            parts.append(modified_sections[key])
        elif isinstance(original, dict) and "_entries" in original:
            entry_parts = []
            for entry in original["_entries"]:
                # Skip excluded entries
                if excluded_entries and _entry_matches_exclusion(entry["key"], excluded_entries):
                    continue
                if modified_experience_entries and entry["key"] in modified_experience_entries:
                    entry_parts.append(modified_experience_entries[entry["key"]])
                else:
                    entry_parts.append(entry["content"])
            if entry_parts:
                parts.append("\n\n".join(entry_parts))
        elif isinstance(original, dict) and "_full" in original:
            parts.append(original["_full"])
        else:
            parts.append(str(original))

        if i < len(ordered_keys) - 1:
            parts.append("\n---")

    return "\n".join(parts) + "\n"


def _entry_matches_exclusion(key: str, excluded: set[str]) -> bool:
    """Check if an entry key matches any exclusion (case-insensitive, substring)."""
    for ex in excluded:
        if ex.lower() in key.lower() or key.lower() in ex.lower():
            return True
    return False
