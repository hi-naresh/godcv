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

    def test_blank_line_between_entries(self):
        """Two experience entries with only single newline between them should get a blank line."""
        broken = (
            "**AI Engineer — BotWot** *Jan 2025 – Oct 2025*\n"
            "- Built multi-agent CRM automation.\n"
            "**LLM Engineer — InsurStaq** *March 2024 – Nov 2024*\n"
            "- Built data pipelines."
        )
        result = validate_and_fix("experience", broken)
        assert "\n\n**LLM Engineer — InsurStaq**" in result

    def test_broken_bold_across_lines(self):
        """Bold text split across lines should be rejoined."""
        broken = (
            "**AI Engineer — BotWot** *Jan 2025 – Oct 2025*\n"
            "- Developed **multi-agent CRM\n"
            "** automation using LangChain."
        )
        result = validate_and_fix("experience", broken)
        assert "**multi-agent CRM**" in result
        assert "\n**" not in result or "\n**AI Engineer" in result  # Only title should start with **

    def test_broken_bold_with_blank_lines(self):
        """Bold text with blank lines inside should be fixed."""
        broken = (
            "**Role — Company** *Dates*\n"
            "- Defining **validation strategies\n"
            "\n"
            "** for agent behavior."
        )
        result = validate_and_fix("experience", broken)
        assert "**validation strategies**" in result

    def test_inline_bold_not_treated_as_title(self):
        """Inline bold text inside bullets should NOT be treated as a new experience entry."""
        content = (
            "**AI Engineer — BotWot** *Jan 2025 – Oct 2025*\n"
            "- Built **multi-agent CRM automation** targeting 35% uplift.\n"
            "- Designed **data pipelines** for customer workflows."
        )
        result = validate_and_fix("experience", content)
        # Should NOT insert blank lines before inline bold
        assert "\n\n- Designed" not in result
        assert "- Built **multi-agent CRM automation**" in result

    def test_newline_before_lowercase_bold(self):
        """Newline followed by **lowercase text should be joined to previous line."""
        broken = (
            "**Role — Company** *Dates*\n"
            "- deliver\n"
            "**high-quality data** for workflows."
        )
        result = validate_and_fix("experience", broken)
        assert "deliver **high-quality data**" in result


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
        # Formatter normalizes "| Stack -" to bold "**| Stack -**"
        assert "**| Stack -**" in result
        assert "**[DataFlow](https://github.com/test)**" in result
        assert "- Built real-time pipeline." in result


class TestEducationFormatting:
    def test_coursework_on_own_line(self):
        """Coursework merged onto degree line should be split."""
        broken = (
            "**M.Sc. in Computer Science - University of London** *Jan 2023 – Jan 2024*"
            "***Coursework**:* Distributed Systems; Machine Learning."
        )
        result = validate_and_fix("education", broken)
        assert "\n***Coursework" in result or "\nCoursework" in result

    def test_preserves_correct_education_format(self):
        correct = (
            "**M.Sc. in Computer Science - University of London** *Jan 2023 – Jan 2024*\n"
            "***Coursework**:* Distributed Systems; Machine Learning."
        )
        result = validate_and_fix("education", correct)
        assert "***Coursework**:*" in result

    def test_blank_line_between_degrees(self):
        broken = (
            "**M.Sc. in CS - University A** *2023 – 2024*\n"
            "***Coursework**:* ML; AI.\n"
            "**B.Sc. in CS - University B** *2019 – 2023*\n"
            "***Coursework**:* Data Structures; Algorithms."
        )
        result = validate_and_fix("education", broken)
        assert "\n\n**B.Sc." in result


class TestExperienceStackUsed:
    def test_stack_used_on_own_line(self):
        """Stack Used merged onto title line should be split."""
        broken = (
            "**Senior Engineer — Acme Corp** *Jan 2023 – Present*"
            "**Stack Used:** Python, FastAPI\n"
            "- Built pipelines."
        )
        result = validate_and_fix("experience", broken)
        assert "\n**Stack Used:**" in result

    def test_unbolded_stack_used_on_own_line(self):
        broken = (
            "**Senior Engineer — Acme Corp** *Jan 2023 – Present*"
            "Stack Used: Python, FastAPI\n"
            "- Built pipelines."
        )
        result = validate_and_fix("experience", broken)
        assert "\n**Stack Used:**" in result

    def test_preserves_correct_stack_format(self):
        correct = (
            "**Senior Engineer — Acme Corp** *Jan 2023 – Present*\n"
            "**Stack Used:** Python, FastAPI\n"
            "- Built pipelines."
        )
        result = validate_and_fix("experience", correct)
        assert "**Stack Used:** Python, FastAPI" in result
        # Should still be on its own line
        lines = result.split("\n")
        stack_line = [l for l in lines if "Stack Used" in l]
        assert len(stack_line) == 1


class TestGenericFormatting:
    def test_unknown_section_still_normalizes(self):
        content = "Some text.   \n\n\n\nMore text."
        result = validate_and_fix("volunteering", content)
        assert "\n\n\n" not in result
        for line in result.split("\n"):
            assert line == line.rstrip()
