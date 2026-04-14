import json
import pytest
from backend.services.gemini import GeminiClient


@pytest.fixture
def client():
    return GeminiClient(api_key="dummy")


class TestRepairJson:
    def test_valid_json_passes_through(self, client):
        text = '{"key": "value", "list": [1, 2]}'
        assert json.loads(client._repair_json(text)) == {"key": "value", "list": [1, 2]}

    def test_trailing_comma_in_object(self, client):
        text = '{"a": 1, "b": 2,}'
        result = json.loads(client._repair_json(text))
        assert result == {"a": 1, "b": 2}

    def test_trailing_comma_in_array(self, client):
        text = '{"items": ["x", "y",]}'
        result = json.loads(client._repair_json(text))
        assert result == {"items": ["x", "y"]}

    def test_nested_trailing_commas(self, client):
        text = '{"a": {"b": 1,}, "c": [1, 2,],}'
        result = json.loads(client._repair_json(text))
        assert result == {"a": {"b": 1}, "c": [1, 2]}

    def test_markdown_fence_removal(self, client):
        text = '```json\n{"key": "value"}\n```'
        result = json.loads(client._repair_json(text))
        assert result == {"key": "value"}

    def test_garbage_after_json(self, client):
        text = '{"key": "value"}\nSome extra text here'
        result = json.loads(client._repair_json(text))
        assert result == {"key": "value"}

    def test_control_characters_removed(self, client):
        text = '{"key": "val\x00ue"}'
        result = json.loads(client._repair_json(text))
        assert result == {"key": "value"}

    def test_complex_orchestrator_like_response(self, client):
        text = """{
  "analysis": {
    "role_type": "backend",
    "key_requirements": ["Python", "Docker"],
    "matched_strengths": ["Strong Python"],
  },
  "tool_calls": [
    {"agent": "summary", "action": "rewrite", "instructions": "Focus on backend"},
  ],
  "sections_unchanged": ["Education"],
  "section_order": ["Summary", "Experience", "Skills"],
}"""
        result = json.loads(client._repair_json(text))
        assert result["analysis"]["role_type"] == "backend"
        assert len(result["tool_calls"]) == 1
        assert result["sections_unchanged"] == ["Education"]

    def test_truncated_json_gets_closed(self, client):
        """Simulates Gemini hitting MAX_TOKENS mid-output."""
        text = """{
  "analysis": {
    "role_type": "data_eng",
    "key_requirements": ["Python", "SQL"],
    "matched_strengths": ["Strong Python"]
  },
  "tool_calls": [
    {"agent": "summary", "action": "rewrite", "instructions": "Focus on data eng"}
  ],
  "sections_unchanged": ["Education"],
  "section_order": ["Summary", "Experience", "Skills", "Education"""
        # JSON is truncated mid-string — missing closing brackets/braces
        result = json.loads(client._repair_json(text))
        assert result["analysis"]["role_type"] == "data_eng"
        assert result["sections_unchanged"] == ["Education"]

    def test_truncated_mid_array(self, client):
        text = '{"items": ["a", "b", "c'
        result = json.loads(client._repair_json(text))
        assert "items" in result

    def test_truncated_mid_object_key(self, client):
        text = '{"analysis": {"role_type": "backend"}, "tool_calls": [{"agent": "summary"'
        result = json.loads(client._repair_json(text))
        assert result["analysis"]["role_type"] == "backend"
