import pytest
from backend.services.formatter import validate_and_fix


class TestExperienceAgentOutput:
    def test_well_formed_entry_passes(self):
        output = (
            "**Senior Engineer — Acme Corp** *Jan 2023 – Present*\n"
            "- Built scalable data pipelines processing 1M+ records daily.\n"
            "- Designed microservices architecture reducing latency by 30%."
        )
        result = validate_and_fix("experience", output)
        assert "**Senior Engineer — Acme Corp**" in result
        assert result.count("- ") == 2

    def test_collapsed_bullets_get_fixed(self):
        output = (
            "**Senior Engineer — Acme Corp** *Jan 2023 – Present*\n"
            "- Built scalable data pipelines processing 1M+ records daily. - Designed microservices."
        )
        result = validate_and_fix("experience", output)
        lines = [l for l in result.split("\n") if l.strip().startswith("- ")]
        assert len(lines) >= 2

    def test_missing_newline_before_title_fixed(self):
        output = "Some preamble text**Senior Engineer — Acme Corp** *Jan 2023 – Present*\n- Bullet."
        result = validate_and_fix("experience", output)
        assert "\n**Senior Engineer" in result


class TestSkillsAgentOutput:
    def test_well_formed_skills_pass(self):
        output = "**Backend:** Python, FastAPI, Django.\n\n**Cloud/Infra:** AWS, Docker, Kubernetes."
        result = validate_and_fix("skills", output)
        assert "**Backend:**" in result
        assert "**Cloud/Infra:**" in result

    def test_missing_blank_line_between_categories_fixed(self):
        output = "**Backend:** Python, FastAPI.\n**Cloud:** AWS, Docker."
        result = validate_and_fix("skills", output)
        assert "**Backend:** Python, FastAPI.\n\n**Cloud:**" in result


class TestSummaryAgentOutput:
    def test_clean_paragraph_passes(self):
        output = "Experienced engineer specializing in Python and cloud infrastructure."
        result = validate_and_fix("summary", output)
        assert result == output

    def test_accidental_header_removed(self):
        output = "# Summary\nExperienced engineer specializing in Python."
        result = validate_and_fix("summary", output)
        assert not result.startswith("#")
        assert "Experienced engineer" in result


class TestProjectsAgentOutput:
    def test_well_formed_project_passes(self):
        output = "**[DataFlow](https://github.com/test)** | Stack - Python, Kafka\n- Built real-time streaming pipeline."
        result = validate_and_fix("projects", output)
        assert "**[DataFlow]" in result
