"""Tests for the format validator / fixer service."""

from backend.services.formatter import validate_and_fix


class TestExperienceFormatting:
    def test_adds_newline_before_bold_title(self):
        broken = (
            "Some text**Senior Engineer — Acme Corp** *Jan 2023 – Present*\n"
            "- Built pipelines."
        )
        result = validate_and_fix("experience", broken)
        assert "\n\n**Senior Engineer" in result

    def test_ensures_bullets_on_own_lines(self):
        broken = (
            "**Role — Company** *Jan 2023 – Present*\n"
            "- First point. - Second point."
        )
        result = validate_and_fix("experience", broken)
        bullet_lines = [l for l in result.split("\n") if l.strip().startswith("- ")]
        assert len(bullet_lines) >= 2

    def test_preserves_correct_formatting(self):
        correct = (
            "**Senior Engineer — Acme Corp** *Jan 2023 – Present*\n"
            "- Built pipelines.\n"
            "- Designed systems."
        )
        result = validate_and_fix("experience", correct)
        assert result == correct

    def test_normalizes_multiple_blank_lines(self):
        content = "First block.\n\n\n\n\nSecond block."
        result = validate_and_fix("experience", content)
        assert "\n\n\n" not in result
        assert "First block.\n\nSecond block." == result

    def test_strips_trailing_whitespace(self):
        content = "- Built pipelines.   \n- Designed systems.  "
        result = validate_and_fix("experience", content)
        for line in result.split("\n"):
            assert line == line.rstrip(), f"Trailing whitespace found: {line!r}"


class TestSkillsFormatting:
    def test_adds_blank_line_between_categories(self):
        broken = "**Backend:** Python, FastAPI.\n**Cloud:** AWS, Docker."
        result = validate_and_fix("skills", broken)
        assert "FastAPI.\n\n**Cloud:**" in result

    def test_preserves_correct_skills_format(self):
        correct = "**Backend:** Python, FastAPI.\n\n**Cloud:** AWS, Docker."
        result = validate_and_fix("skills", correct)
        assert result == correct

    def test_fixes_missing_bold_colon_pattern(self):
        broken = "Backend: Python, FastAPI."
        result = validate_and_fix("skills", broken)
        assert result.startswith("**Backend:**")


class TestSummaryFormatting:
    def test_removes_accidental_headers(self):
        broken = "# Summary\nExperienced engineer with 5 years."
        result = validate_and_fix("summary", broken)
        assert result.startswith("Experienced")
        assert "#" not in result

    def test_preserves_plain_paragraph(self):
        correct = "Experienced engineer with 5 years of backend development."
        result = validate_and_fix("summary", correct)
        assert result == correct


class TestProjectsFormatting:
    def test_adds_newline_before_project_entry(self):
        broken = "Some text**[Project](https://url.com)**"
        result = validate_and_fix("projects", broken)
        assert "\n\n**[Project]" in result

    def test_preserves_correct_project_format(self):
        correct = (
            "**[DataFlow](https://github.com/test)** | Stack - Python\n"
            "- Built real-time pipeline."
        )
        result = validate_and_fix("projects", correct)
        assert result == correct


class TestGenericFormatting:
    def test_unknown_section_still_normalizes(self):
        content = "Some text.   \n\n\n\nMore text."
        result = validate_and_fix("volunteering", content)
        assert "\n\n\n" not in result
        for line in result.split("\n"):
            assert line == line.rstrip()
