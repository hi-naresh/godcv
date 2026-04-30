from backend.routers.tailor import _strip_generate_projects_when_strict


class TestStripGenerateProjectsWhenStrict:
    def test_strict_strips_flag(self):
        tool_calls = [
            {"agent": "projects", "action": "rewrite", "generate_projects": True},
            {"agent": "summary", "action": "rewrite"},
        ]
        out = _strip_generate_projects_when_strict(tool_calls, stealth_mode=False)
        assert "generate_projects" not in out[0]
        assert out[1] == {"agent": "summary", "action": "rewrite"}

    def test_stealth_keeps_flag(self):
        tool_calls = [
            {"agent": "projects", "action": "rewrite", "generate_projects": True},
        ]
        out = _strip_generate_projects_when_strict(tool_calls, stealth_mode=True)
        assert out[0]["generate_projects"] is True

    def test_no_flag_strict_passthrough(self):
        tool_calls = [{"agent": "summary", "action": "rewrite"}]
        out = _strip_generate_projects_when_strict(tool_calls, stealth_mode=False)
        assert out == tool_calls
