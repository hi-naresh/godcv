import pytest
from backend.services.parser import (
    parse_frontmatter,
    parse_experience_entries,
    parse_sections,
    parse_resume,
    _extract_company_key,
)


class TestParseFrontmatter:
    def test_extracts_frontmatter_and_body(self, sample_resume):
        fm, body = parse_frontmatter(sample_resume)
        assert "name: Test User" in fm
        assert fm.startswith("---")
        assert fm.strip().endswith("---")
        assert "# Summary" in body

    def test_no_frontmatter_returns_full_body(self):
        md = "# Summary\nHello world"
        fm, body = parse_frontmatter(md)
        assert fm == ""
        assert body == md

    def test_malformed_frontmatter_returns_full_body(self):
        # Missing closing --- marker
        md = "---\nname: Test User\n# Summary\nHello world"
        fm, body = parse_frontmatter(md)
        assert fm == ""
        assert body == md


class TestParseExperienceEntries:
    EXPERIENCE_TWO = (
        "**Senior Engineer — Acme Corp (London)** *Jan 2023 – Present*\n"
        "- Built scalable pipelines.\n"
        "- Designed microservices.\n\n"
        "**Junior Developer — StartupXYZ (Remote)** *Jun 2021 – Dec 2022*\n"
        "- Developed REST APIs.\n"
        "- Implemented CI/CD.\n"
    )

    EXPERIENCE_ONE = (
        "**Solo Dev — OnlyCo** *Jan 2020 – Dec 2020*\n"
        "- Did everything.\n"
    )

    def test_splits_two_entries(self):
        entries = parse_experience_entries(self.EXPERIENCE_TWO)
        assert len(entries) == 2
        keys = {e["key"] for e in entries}
        assert "Acme" in keys
        assert "StartupXYZ" in keys

    def test_single_entry(self):
        entries = parse_experience_entries(self.EXPERIENCE_ONE)
        assert len(entries) == 1

    def test_entry_has_content(self):
        entries = parse_experience_entries(self.EXPERIENCE_TWO)
        acme = next(e for e in entries if e["key"] == "Acme")
        assert "Built scalable pipelines" in acme["content"]


class TestExtractCompanyKey:
    def test_em_dash_separator(self):
        assert _extract_company_key("AI Engineer — BotWot iCX") == "BotWot"

    def test_en_dash_separator(self):
        assert _extract_company_key("Engineer – Google LLC") == "Google"

    def test_hyphen_separator(self):
        # With plain-hyphen split the parser takes parts[-1] then splits on whitespace,
        # so "Intern - SAILC AURO" → last segment "SAILC AURO" → first word "SAILC".
        assert _extract_company_key("Intern - SAILC AURO") == "SAILC"

    def test_parenthetical_stripped(self):
        assert _extract_company_key("Engineer — NestDore (London)") == "NestDore"


class TestParseSections:
    def test_all_sections_found(self, sample_resume):
        _, body = parse_frontmatter(sample_resume)
        sections, _ = parse_sections(body)
        for name in ("Summary", "Education", "Skills", "Experience", "Projects"):
            assert name in sections

    def test_experience_has_entries(self, sample_resume):
        _, body = parse_frontmatter(sample_resume)
        sections, _ = parse_sections(body)
        exp = sections["Experience"]
        assert isinstance(exp, dict)
        assert "_entries" in exp
        assert len(exp["_entries"]) == 2

    def test_separators_tracked(self):
        # Separators are recorded when the entire content between two headings is "---".
        # Build a minimal body that triggers this.
        body = "# Summary\n---\n# Skills\nPython"
        _, separators = parse_sections(body)
        assert "Summary" in separators


class TestParseResume:
    def test_full_parse(self, sample_resume):
        result = parse_resume(sample_resume)
        assert "frontmatter" in result
        assert "sections" in result
        assert "separators" in result
