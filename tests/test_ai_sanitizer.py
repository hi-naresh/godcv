"""Tests for the AI content sanitizer in formatter.py.

Ensures that AI meta-commentary, filler phrases, and other
AI-detectable artifacts are stripped from agent outputs.
"""

import pytest
from backend.services.formatter import strip_ai_artifacts, validate_and_fix


class TestStripAIMetaCommentary:
    """Test removal of full lines that are AI meta-commentary."""

    def test_removes_here_is_preamble(self):
        content = "Here is the rewritten entry:\n**Senior Engineer — Acme Corp** *Jan 2023 – Present*\n- Built data pipelines."
        result = strip_ai_artifacts(content)
        assert "Here is" not in result
        assert "**Senior Engineer — Acme Corp**" in result
        assert "- Built data pipelines." in result

    def test_removes_here_are_preamble(self):
        content = "Here are the projects aligned as per your description:\n**[DataFlow](https://github.com/test)**\n- Built pipeline."
        result = strip_ai_artifacts(content)
        assert "Here are" not in result
        assert "**[DataFlow]" in result

    def test_removes_ive_aligned_commentary(self):
        content = "**Role — Company** *Dates*\n- Built systems.\nI've aligned the bullets with the JD requirements."
        result = strip_ai_artifacts(content)
        assert "I've aligned" not in result
        assert "- Built systems." in result

    def test_removes_based_on_your_description(self):
        content = "Based on your description, here is the optimized section:\n**Backend:** Python, FastAPI."
        result = strip_ai_artifacts(content)
        assert "Based on your description" not in result
        assert "**Backend:** Python, FastAPI." in result

    def test_removes_note_lines(self):
        content = "**Backend:** Python, FastAPI.\nNote: I've reordered skills based on JD relevance."
        result = strip_ai_artifacts(content)
        assert "Note:" not in result
        assert "**Backend:** Python, FastAPI." in result

    def test_removes_note_that_lines(self):
        content = "- Built pipelines.\nNote that the stack has been reordered for relevance."
        result = strip_ai_artifacts(content)
        assert "Note that" not in result
        assert "- Built pipelines." in result

    def test_removes_as_requested_lines(self):
        content = "As requested, the summary now leads with data engineering.\nExperienced data engineer with 5 years..."
        result = strip_ai_artifacts(content)
        assert "As requested" not in result
        assert "Experienced data engineer" in result

    def test_removes_as_per_your_lines(self):
        content = "As per your instructions, I've restructured the experience.\n**Role — Company** *Dates*\n- Built systems."
        result = strip_ai_artifacts(content)
        assert "As per your" not in result

    def test_removes_key_changes_made(self):
        content = "**Role — Company** *Dates*\n- Built systems.\nKey changes made:\n1. Reordered bullets"
        result = strip_ai_artifacts(content)
        assert "Key changes made" not in result

    def test_removes_section_now_reflects(self):
        content = "The projects section now reflects the JD priorities.\n**[DataFlow](https://github.com/test)**\n- Built pipeline."
        result = strip_ai_artifacts(content)
        assert "section now reflects" not in result

    def test_removes_let_me_know(self):
        content = "- Built systems.\nLet me know if you'd like any changes."
        result = strip_ai_artifacts(content)
        assert "Let me know" not in result

    def test_removes_hope_this_helps(self):
        content = "- Built systems.\nHope this helps!"
        result = strip_ai_artifacts(content)
        assert "Hope this helps" not in result

    def test_removes_feel_free_to(self):
        content = "- Built systems.\nFeel free to adjust the wording."
        result = strip_ai_artifacts(content)
        assert "Feel free to" not in result

    def test_preserves_legitimate_content(self):
        content = (
            "**Senior Engineer — Acme Corp** *Jan 2023 – Present*\n"
            "**Stack Used:** Python, Kubernetes, PostgreSQL\n"
            "- Built scalable data pipelines processing 1M+ records daily.\n"
            "- Designed microservices architecture reducing latency by 30%."
        )
        result = strip_ai_artifacts(content)
        assert result.strip() == content.strip()

    def test_preserves_frontmatter_separators(self):
        """--- separators at the very start of content (frontmatter) should be preserved."""
        content = "---\nname: Test\n---\n# Summary\nExperienced engineer."
        result = strip_ai_artifacts(content)
        # The frontmatter separators at top (first 3 lines) should remain
        assert "name: Test" in result

    def test_removes_trailing_separator_not_frontmatter(self):
        content = "- Built pipelines.\n\n---\n"
        result = strip_ai_artifacts(content)
        assert "---" not in result

    def test_removes_this_entry_now(self):
        content = "**Role — Company** *Dates*\n- Built systems.\nThis entry now highlights the candidate's data engineering skills."
        result = strip_ai_artifacts(content)
        assert "This entry now" not in result


class TestStripAIFillerPhrases:
    """Test replacement of AI filler phrases with natural alternatives."""

    def test_replaces_spearheaded(self):
        content = "- Spearheaded the migration to cloud infrastructure."
        result = strip_ai_artifacts(content)
        assert "Spearheaded" not in result
        assert "led" in result

    def test_replaces_leveraged(self):
        content = "- Leveraged Kubernetes for container orchestration."
        result = strip_ai_artifacts(content)
        assert "Leveraged" not in result
        assert "used" in result.lower()

    def test_replaces_leveraged_cutting_edge(self):
        content = "- Leveraged cutting-edge ML techniques for classification."
        result = strip_ai_artifacts(content)
        assert "Leveraged cutting-edge" not in result
        assert "used" in result.lower()

    def test_replaces_utilized(self):
        content = "- Utilized Python and FastAPI to build REST APIs."
        result = strip_ai_artifacts(content)
        assert "Utilized" not in result
        assert "used" in result.lower()

    def test_replaces_utilized_state_of_the_art(self):
        content = "- Utilized state-of-the-art NLP models."
        result = strip_ai_artifacts(content)
        assert "Utilized state-of-the-art" not in result

    def test_replaces_in_order_to(self):
        content = "- Refactored the codebase in order to improve performance."
        result = strip_ai_artifacts(content)
        assert "in order to" not in result
        assert "to improve" in result

    def test_replaces_harnessing_the_power_of(self):
        content = "- Delivered insights by harnessing the power of machine learning."
        result = strip_ai_artifacts(content)
        assert "harnessing the power of" not in result
        assert "using" in result

    def test_replaces_pivotal_role(self):
        content = "- Played a pivotal role in system redesign."
        result = strip_ai_artifacts(content)
        assert "pivotal role" not in result
        assert "key" in result.lower()

    def test_replaces_navigating_complexities(self):
        content = "- Experienced in navigating the complexities of distributed systems."
        result = strip_ai_artifacts(content)
        assert "navigating the complexities of" not in result
        assert "handling" in result

    def test_replaces_passionate_about(self):
        content = "Passionate about building scalable systems."
        result = strip_ai_artifacts(content)
        assert "Passionate about" not in result
        assert "focused on" in result.lower()

    def test_replaces_poised_to(self):
        content = "Poised to deliver high-impact solutions."
        result = strip_ai_artifacts(content)
        assert "Poised to" not in result
        assert "ready to" in result.lower()

    def test_replaces_cutting_edge(self):
        content = "- Built cutting-edge data pipelines."
        result = strip_ai_artifacts(content)
        assert "cutting-edge" not in result
        assert "modern" in result

    def test_replaces_seamlessly(self):
        content = "- Seamlessly integrated third-party APIs."
        result = strip_ai_artifacts(content)
        assert "Seamlessly" not in result
        assert "integrated" in result.lower()

    def test_replaces_fostered(self):
        content = "- Fostered a culture of code review."
        result = strip_ai_artifacts(content)
        assert "Fostered" not in result
        assert "built" in result.lower()

    def test_replaces_pioneered(self):
        content = "- Pioneered the adoption of microservices."
        result = strip_ai_artifacts(content)
        assert "Pioneered" not in result
        assert "introduced" in result.lower()

    def test_replaces_empowered(self):
        content = "- Empowered the team to adopt CI/CD practices."
        result = strip_ai_artifacts(content)
        assert "Empowered" not in result
        assert "enabled" in result.lower()

    def test_preserves_orchestrated_in_technical_context(self):
        """'Orchestrated' followed by container/deployment/pipeline should stay."""
        content = "- Orchestrated container deployments via Kubernetes."
        result = strip_ai_artifacts(content)
        assert "Orchestrated container" in result

    def test_replaces_orchestrated_in_non_technical_context(self):
        content = "- Orchestrated a team of 10 engineers."
        result = strip_ai_artifacts(content)
        assert "Orchestrated" not in result
        assert "coordinated" in result.lower()

    def test_no_double_spaces_after_replacement(self):
        """Replacements with empty strings should not leave double spaces."""
        content = "- Seamlessly integrated APIs into the platform."
        result = strip_ai_artifacts(content)
        assert "  " not in result


class TestSanitizerIntegration:
    """Test that sanitizer works within validate_and_fix."""

    def test_experience_with_ai_preamble(self):
        content = (
            "Here is the rewritten experience entry:\n"
            "**Senior Engineer — Acme Corp** *Jan 2023 – Present*\n"
            "- Spearheaded the migration to Kubernetes.\n"
            "- Leveraged FastAPI for microservices."
        )
        result = validate_and_fix("experience", content)
        assert "Here is" not in result
        assert "Spearheaded" not in result
        assert "Leveraged" not in result
        assert "led" in result
        assert "used" in result.lower()
        assert "**Senior Engineer — Acme Corp**" in result

    def test_projects_with_ai_note(self):
        content = (
            "**[DataFlow](https://github.com/test)** **| Stack -** Python, Kafka\n"
            "- Built real-time streaming pipeline.\n\n"
            "Note: Projects have been reordered by JD relevance."
        )
        result = validate_and_fix("projects", content)
        assert "Note:" not in result
        assert "**[DataFlow]" in result

    def test_skills_with_ai_commentary(self):
        content = (
            "I've reordered the skills to match the JD:\n"
            "**Backend:** Python, FastAPI, Django.\n\n"
            "**Cloud/Infra:** AWS, Docker, Kubernetes."
        )
        result = validate_and_fix("skills", content)
        assert "I've reordered" not in result
        assert "**Backend:**" in result

    def test_summary_with_ai_preamble(self):
        content = (
            "Here is the rewritten summary:\n"
            "Experienced engineer with 5 years of Python development."
        )
        result = validate_and_fix("summary", content)
        assert "Here is" not in result
        assert "Experienced engineer" in result

    def test_clean_content_passes_through(self):
        """Content without AI artifacts should pass through unchanged (modulo formatting fixes)."""
        content = (
            "**Senior Engineer — Acme Corp** *Jan 2023 – Present*\n"
            "**Stack Used:** Python, Kubernetes, PostgreSQL\n"
            "- Built scalable data pipelines processing 1M+ records daily.\n"
            "- Designed microservices architecture reducing latency by 30%."
        )
        result = validate_and_fix("experience", content)
        assert "- Built scalable data pipelines" in result
        assert "- Designed microservices architecture" in result

    def test_multiple_ai_artifacts_in_one_output(self):
        """Agent output with both preamble and AI phrases gets fully cleaned."""
        content = (
            "Here is your optimized experience entry:\n"
            "**Senior Engineer — Acme Corp** *Jan 2023 – Present*\n"
            "- Spearheaded the development of cutting-edge data pipelines.\n"
            "- Leveraged state-of-the-art ML models in order to improve accuracy.\n"
            "Let me know if you'd like any changes."
        )
        result = validate_and_fix("experience", content)
        assert "Here is" not in result
        assert "Spearheaded" not in result
        assert "cutting-edge" not in result
        assert "Leveraged" not in result
        assert "state-of-the-art" not in result
        assert "in order to" not in result
        assert "Let me know" not in result
        assert "led" in result
        assert "modern" in result
