"""Server-side project count cap (_enforce_max_projects).

These tests are pure logic — no LLM calls, no DB. They verify that the
guardrail converts excess project rewrite/include actions to exclude,
regardless of what the orchestrator LLM decided to output.
"""

import pytest
from backend.routers.tailor import _enforce_max_projects


class TestEnforceMaxProjects:
    def _proj(self, name, action="rewrite"):
        return {"agent": "projects", "entry": name, "action": action}

    def _summary(self):
        return {"agent": "summary", "action": "rewrite"}

    def test_under_limit_untouched(self):
        calls = [self._proj("A"), self._proj("B")]
        out = _enforce_max_projects(calls, max_projects=3)
        assert [c["action"] for c in out] == ["rewrite", "rewrite"]

    def test_exactly_at_limit_untouched(self):
        calls = [self._proj("A"), self._proj("B"), self._proj("C")]
        out = _enforce_max_projects(calls, max_projects=3)
        assert all(c["action"] == "rewrite" for c in out)

    def test_excess_converted_to_exclude(self):
        calls = [self._proj("A"), self._proj("B"), self._proj("C"),
                 self._proj("D"), self._proj("E")]
        out = _enforce_max_projects(calls, max_projects=3)
        actions = [c["action"] for c in out if c.get("agent") == "projects"]
        assert actions == ["rewrite", "rewrite", "rewrite", "exclude", "exclude"]

    def test_non_project_calls_pass_through(self):
        calls = [self._summary(), self._proj("A"), self._proj("B"),
                 self._proj("C"), self._proj("D")]
        out = _enforce_max_projects(calls, max_projects=2)
        assert out[0]["agent"] == "summary"
        assert out[0]["action"] == "rewrite"
        proj_actions = [c["action"] for c in out if c.get("agent") == "projects"]
        assert proj_actions == ["rewrite", "rewrite", "exclude", "exclude"]

    def test_already_excluded_dont_count(self):
        """Pre-excluded entries (orchestrator already said exclude) don't consume slots."""
        calls = [self._proj("A", "exclude"), self._proj("B"), self._proj("C"), self._proj("D")]
        out = _enforce_max_projects(calls, max_projects=2)
        proj_out = [c for c in out if c.get("agent") == "projects"]
        assert proj_out[0]["action"] == "exclude"   # original exclude preserved
        assert proj_out[1]["action"] == "rewrite"   # slot 1
        assert proj_out[2]["action"] == "rewrite"   # slot 2
        assert proj_out[3]["action"] == "exclude"   # excess

    def test_include_counts_toward_limit(self):
        """'include' and 'rewrite' both count — include just means no LLM rewrite."""
        calls = [self._proj("A", "include"), self._proj("B", "include"),
                 self._proj("C", "rewrite"), self._proj("D", "rewrite")]
        out = _enforce_max_projects(calls, max_projects=3)
        proj_out = [c for c in out if c.get("agent") == "projects"]
        assert proj_out[0]["action"] == "include"
        assert proj_out[1]["action"] == "include"
        assert proj_out[2]["action"] == "rewrite"
        assert proj_out[3]["action"] == "exclude"

    def test_entry_less_project_calls_ignored(self):
        """generate_projects tool_calls have no 'entry' — they're whole-section calls and exempt."""
        calls = [
            {"agent": "projects", "action": "rewrite", "generate_projects": True},  # no entry
            self._proj("A"), self._proj("B"), self._proj("C"), self._proj("D"),
        ]
        out = _enforce_max_projects(calls, max_projects=2)
        no_entry = [c for c in out if c.get("agent") == "projects" and not c.get("entry")]
        assert len(no_entry) == 1
        assert no_entry[0]["action"] == "rewrite"  # untouched
        with_entry = [c for c in out if c.get("agent") == "projects" and c.get("entry")]
        assert [c["action"] for c in with_entry] == ["rewrite", "rewrite", "exclude", "exclude"]

    def test_max_projects_zero_excludes_all(self):
        calls = [self._proj("A"), self._proj("B")]
        out = _enforce_max_projects(calls, max_projects=0)
        assert all(c["action"] == "exclude" for c in out)

    def test_max_projects_one(self):
        calls = [self._proj("A"), self._proj("B"), self._proj("C")]
        out = _enforce_max_projects(calls, max_projects=1)
        proj = [c for c in out if c.get("agent") == "projects"]
        assert proj[0]["action"] == "rewrite"
        assert proj[1]["action"] == "exclude"
        assert proj[2]["action"] == "exclude"

    def test_real_world_seven_to_three(self):
        """Regression: the exact scenario from bug2 — 7 projects, limit 3."""
        names = ["Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta", "Eta"]
        calls = [self._proj(n) for n in names]
        out = _enforce_max_projects(calls, max_projects=3)
        kept = [c for c in out if c["action"] == "rewrite"]
        excluded = [c for c in out if c["action"] == "exclude"]
        assert len(kept) == 3
        assert len(excluded) == 4
        assert kept[0]["entry"] == "Alpha"   # relevance order preserved
        assert excluded[0]["entry"] == "Delta"
