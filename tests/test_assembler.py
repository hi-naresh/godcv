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


class TestAssembleWithSectionOrder:
    def test_reorders_sections(self, sample_resume):
        parsed = parse_resume(sample_resume)
        order = ["Summary", "Experience", "Skills", "Education", "Projects", "Volunteering and Interests"]
        output = assemble_resume(parsed, {}, section_order=order)
        # Experience should come before Skills and Education
        exp_pos = output.index("# Experience")
        skills_pos = output.index("# Skills")
        edu_pos = output.index("# Education")
        assert exp_pos < skills_pos
        assert exp_pos < edu_pos

    def test_original_order_without_section_order(self, sample_resume):
        parsed = parse_resume(sample_resume)
        output = assemble_resume(parsed, {})
        # Original order: Summary, Education, Skills, Experience
        summary_pos = output.index("# Summary")
        edu_pos = output.index("# Education")
        skills_pos = output.index("# Skills")
        exp_pos = output.index("# Experience")
        assert summary_pos < edu_pos < skills_pos < exp_pos

    def test_missing_sections_in_order_appended(self, sample_resume):
        parsed = parse_resume(sample_resume)
        # Only mention a few sections — rest should still appear
        order = ["Experience", "Summary"]
        output = assemble_resume(parsed, {}, section_order=order)
        assert "# Experience" in output
        assert "# Summary" in output
        assert "# Skills" in output
        assert "# Education" in output
        # Experience and Summary should come first
        exp_pos = output.index("# Experience")
        summary_pos = output.index("# Summary")
        skills_pos = output.index("# Skills")
        assert exp_pos < summary_pos < skills_pos
