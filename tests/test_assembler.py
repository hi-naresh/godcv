import pytest
from backend.services.parser import parse_resume
from backend.services.assembler import assemble_resume


class TestAssembleUnmodified:
    def test_roundtrip_preserves_content(self, sample_resume):
        parsed = parse_resume(sample_resume)
        output = assemble_resume(parsed, {})
        for header in ("# Summary", "# Education", "# Skills", "# Experience", "# Projects"):
            assert header in output
        assert "name: Test User" in output

    def test_roundtrip_preserves_experience_entries(self, sample_resume):
        parsed = parse_resume(sample_resume)
        output = assemble_resume(parsed, {})
        assert "Senior Engineer — Acme Corp" in output
        assert "Junior Developer — StartupXYZ" in output


class TestAssembleWithModifications:
    def test_replace_single_section(self, sample_resume):
        parsed = parse_resume(sample_resume)
        new_summary = "Experienced backend engineer focused on distributed systems."
        output = assemble_resume(parsed, {"Summary": new_summary})
        assert new_summary in output
        # Other sections should still be present
        assert "# Education" in output
        assert "# Skills" in output

    def test_replace_experience_entry(self, sample_resume):
        parsed = parse_resume(sample_resume)
        new_bullet = "- Led migration of legacy monolith to microservices."
        output = assemble_resume(parsed, {}, modified_experience_entries={"Acme": new_bullet})
        assert new_bullet in output
        # Other experience entry unchanged
        assert "Developed REST APIs" in output

    def test_frontmatter_always_preserved(self, sample_resume):
        parsed = parse_resume(sample_resume)
        output = assemble_resume(
            parsed,
            {"Summary": "New summary text.", "Skills": "**Python**, **Go**."},
        )
        assert "name: Test User" in output
        assert "email: test@example.com" in output

    def test_separators_between_sections(self, sample_resume):
        parsed = parse_resume(sample_resume)
        output = assemble_resume(parsed, {})
        assert "---" in output
