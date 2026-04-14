import pytest
from backend.services.seniority import detect_seniority

class TestSeniorityDetection:
    def test_graduate_keywords(self):
        assert detect_seniority("Looking for a graduate software engineer.") == "graduate"

    def test_entry_level(self):
        assert detect_seniority("Entry level position for a data analyst. 0-1 years experience.") == "graduate"

    def test_junior(self):
        assert detect_seniority("Junior developer with 1-2 years of experience in Python.") == "junior"

    def test_mid_level_years(self):
        assert detect_seniority("We need someone with 3-5 years of experience building distributed systems.") == "mid-level"

    def test_senior_explicit(self):
        assert detect_seniority("Senior Backend Engineer with 5+ years experience leading projects.") == "senior"

    def test_senior_years(self):
        assert detect_seniority("Requires 7 years of experience in software development.") == "senior"

    def test_lead(self):
        assert detect_seniority("Lead Engineer to manage a team of 8 developers.") == "lead"

    def test_principal(self):
        assert detect_seniority("Principal Engineer to drive technical strategy.") == "principal"

    def test_no_signals_returns_none(self):
        assert detect_seniority("Software engineer to work on our platform. Python and AWS required.") is None

    def test_case_insensitive(self):
        assert detect_seniority("SENIOR SOFTWARE ENGINEER needed for our team.") == "senior"
