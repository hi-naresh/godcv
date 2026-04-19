"""Tests for candidate profile fact extraction."""
from datetime import date
from unittest.mock import patch
from backend.services.candidate_profile import build_candidate_profile, _parse_education, _parse_date


SAMPLE_RESUME = """---
name: Test User
title: AI Engineer
---
# Education

**M.Sc. in Artificial Intelligence - Brunel University London, UK.** *Jan 2025 – Jan 2026*
***Coursework**:* Neural Networks; Deep Learning.

**B.Sc. in Computer Science - MIT** *Aug 2020 – Jun 2024*

---
# Skills

**Programming:** Python, TypeScript, Go.

**AI/ML:** PyTorch, LangChain, RAG Systems.

---
# Experience

**AI Engineer — NestDore (London startup)** *October 2025 – March 2026*
- Built AI matching engine.

**Software Engineer — Acme Corp** *Jan 2023 – Sep 2025*
- Built data pipelines.

---
# Projects

**[QEngine](https://github.com/test)** **| Stack -** Python, Q-learning
- Built backtester with genetic algorithms.
"""


@patch("backend.services.candidate_profile.date")
def test_completed_degree_detected(mock_date):
    """MSc ending Jan 2026 should be COMPLETED when today is April 2026."""
    mock_date.today.return_value = date(2026, 4, 19)
    mock_date.side_effect = lambda *a, **kw: date(*a, **kw)

    profile = build_candidate_profile(SAMPLE_RESUME)
    assert "COMPLETED" in profile
    assert "M.Sc." in profile
    assert "in progress" not in profile.lower() or "In progress" not in profile


@patch("backend.services.candidate_profile.date")
def test_in_progress_degree_detected(mock_date):
    """MSc ending Jan 2026 should be in progress when today is Dec 2025."""
    mock_date.today.return_value = date(2025, 12, 1)
    mock_date.side_effect = lambda *a, **kw: date(*a, **kw)

    profile = build_candidate_profile(SAMPLE_RESUME)
    assert "In progress" in profile


@patch("backend.services.candidate_profile.date")
def test_experience_duration(mock_date):
    mock_date.today.return_value = date(2026, 4, 19)
    mock_date.side_effect = lambda *a, **kw: date(*a, **kw)

    profile = build_candidate_profile(SAMPLE_RESUME)
    assert "EXPERIENCE:" in profile
    assert "roles" in profile


@patch("backend.services.candidate_profile.date")
def test_skills_extracted(mock_date):
    mock_date.today.return_value = date(2026, 4, 19)
    mock_date.side_effect = lambda *a, **kw: date(*a, **kw)

    profile = build_candidate_profile(SAMPLE_RESUME)
    assert "Python" in profile
    assert "PyTorch" in profile
    assert "LangChain" in profile


def test_parse_date():
    assert _parse_date("Jan 2026") == date(2026, 1, 1)
    assert _parse_date("June 2024") == date(2024, 6, 1)
    assert _parse_date("October 2025") == date(2025, 10, 1)
    assert _parse_date("invalid") is None


def test_empty_resume():
    profile = build_candidate_profile("")
    assert "TODAY'S DATE" in profile


FUTURE_RESUME = """---
name: Student
---
# Education

**Ph.D. in Machine Learning - Stanford** *Sep 2024 – Sep 2028*

**M.Sc. in AI - Oxford** *Sep 2022 – Sep 2024*
"""


@patch("backend.services.candidate_profile.date")
def test_mixed_completion_status(mock_date):
    """PhD in future should be in progress, MSc in past should be completed."""
    mock_date.today.return_value = date(2026, 4, 19)
    mock_date.side_effect = lambda *a, **kw: date(*a, **kw)

    profile = build_candidate_profile(FUTURE_RESUME)
    lines = profile.split("\n")
    phd_line = [l for l in lines if "Ph.D." in l][0]
    msc_line = [l for l in lines if "M.Sc." in l][0]

    assert "In progress" in phd_line
    assert "COMPLETED" in msc_line
