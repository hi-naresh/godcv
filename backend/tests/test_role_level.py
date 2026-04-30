from backend.services.role_level import detect_role_level


class TestDetectRoleLevel:
    def test_graduate_keyword(self):
        assert detect_role_level("Graduate Data Engineer at Capgemini") == "graduate"

    def test_intern_keyword(self):
        assert detect_role_level("Software Engineering Intern, summer 2026") == "graduate"

    def test_junior_keyword_maps_to_graduate(self):
        assert detect_role_level("Junior Backend Developer") == "graduate"

    def test_senior_keyword(self):
        assert detect_role_level("Senior Software Engineer, 5+ years experience") == "non-graduate"

    def test_lead_keyword(self):
        assert detect_role_level("Tech Lead — Platform team") == "non-graduate"

    def test_principal_keyword(self):
        assert detect_role_level("Principal ML Engineer") == "non-graduate"

    def test_years_one(self):
        assert detect_role_level("looking for engineer with 1 year of experience") == "graduate"

    def test_years_two(self):
        assert detect_role_level("2 years of experience required") == "graduate"

    def test_years_three(self):
        assert detect_role_level("3+ years of experience in Python") == "non-graduate"

    def test_years_five(self):
        assert detect_role_level("5+ years experience required") == "non-graduate"

    def test_no_signal(self):
        assert detect_role_level("We're hiring great people who love product.") is None
