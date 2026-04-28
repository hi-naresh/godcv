import json
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from backend.services.gemini import GeminiClient, _parse_retry_delay


def make_response(status_code: int, body: dict | None = None, text: str = ""):
    """Build a mock httpx.Response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.headers = {}
    resp.json = MagicMock(return_value=body or {})
    resp.text = text
    return resp


def make_success_response(text: str = "ok"):
    return make_response(200, {
        "candidates": [{"content": {"parts": [{"text": text}]}, "finishReason": "STOP"}],
        "usageMetadata": {"promptTokenCount": 1, "candidatesTokenCount": 1},
    })


def make_429_response(retry_seconds: float = 1.0):
    return make_response(429, {
        "error": {
            "code": 429,
            "message": f"Quota exceeded. Please retry in {retry_seconds}s.",
            "status": "RESOURCE_EXHAUSTED",
            "details": [
                {"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": f"{retry_seconds}s"}
            ],
        }
    })


def make_503_response():
    return make_response(503, {"error": {"message": "This model is currently experiencing high demand."}})


def patch_post_sequence(responses):
    """Patch httpx.AsyncClient.post to return responses in order."""
    iterator = iter(responses)

    async def fake_post(*args, **kwargs):
        return next(iterator)

    return patch("backend.services.gemini.httpx.AsyncClient.post", new=fake_post)


# --- _parse_retry_delay unit tests ---

@pytest.mark.asyncio
async def test_parse_retry_delay_from_structured_details():
    err = {"error": {"details": [{"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "13.5s"}]}}
    assert _parse_retry_delay(err, "") == 13.5


@pytest.mark.asyncio
async def test_parse_retry_delay_from_message_fallback():
    assert _parse_retry_delay({}, "Please retry in 7.2s") == 7.2


@pytest.mark.asyncio
async def test_parse_retry_delay_default():
    assert _parse_retry_delay({}, "no info here") == 30.0


# --- generate() integration tests ---

@pytest.mark.asyncio
async def test_generate_succeeds_first_try():
    with patch_post_sequence([make_success_response("hello")]):
        client = GeminiClient(api_key="k")
        result = await client.generate("p")
        assert result == "hello"


@pytest.mark.asyncio
async def test_generate_retries_429_then_succeeds(monkeypatch):
    monkeypatch.setattr("backend.services.gemini.asyncio.sleep", AsyncMock())
    with patch_post_sequence([make_429_response(0.1), make_success_response("hello")]):
        client = GeminiClient(api_key="k")
        result = await client.generate("p")
        assert result == "hello"


@pytest.mark.asyncio
async def test_generate_retries_503_with_backoff_then_succeeds(monkeypatch):
    monkeypatch.setattr("backend.services.gemini.asyncio.sleep", AsyncMock())
    with patch_post_sequence([make_503_response(), make_success_response("ok")]):
        client = GeminiClient(api_key="k")
        result = await client.generate("p")
        assert result == "ok"


@pytest.mark.asyncio
async def test_generate_gives_up_after_max_attempts(monkeypatch):
    monkeypatch.setattr("backend.services.gemini.asyncio.sleep", AsyncMock())
    with patch_post_sequence([make_429_response(0.1), make_429_response(0.1), make_429_response(0.1)]):
        client = GeminiClient(api_key="k")
        with pytest.raises(RuntimeError, match="Gemini API error"):
            await client.generate("p")


@pytest.mark.asyncio
async def test_generate_does_not_retry_400():
    bad = make_response(400, {"error": {"message": "Invalid argument"}})
    with patch_post_sequence([bad]):
        client = GeminiClient(api_key="k")
        with pytest.raises(RuntimeError, match="Invalid argument"):
            await client.generate("p")


@pytest.mark.asyncio
async def test_generate_increments_usage_per_attempt(monkeypatch):
    """Each retry attempt should increment total_requests."""
    monkeypatch.setattr("backend.services.gemini.asyncio.sleep", AsyncMock())
    from backend.services import gemini as gemini_module
    gemini_module.reset_usage()

    with patch_post_sequence([make_429_response(0.1), make_429_response(0.1), make_success_response("hi")]):
        client = GeminiClient(api_key="k")
        result = await client.generate("p")
        assert result == "hi"
        assert gemini_module._usage["total_requests"] == 3


@pytest.mark.asyncio
async def test_generate_total_wait_cap_gives_up(monkeypatch):
    """Total accumulated wait cap (90s) prevents unlimited retrying.

    Scenario: each 429 carries a 60s capped delay.
    - Attempt 0: delay=60s, total_waited=0 → 0+60=60 ≤ 90 → sleep, retry
    - Attempt 1: delay=60s, total_waited=60 → 60+60=120 > 90 → give up (no sleep)
    So sleep is called exactly once and we ultimately raise.
    """
    sleep_mock = AsyncMock()
    monkeypatch.setattr("backend.services.gemini.asyncio.sleep", sleep_mock)

    # retryDelay=91s is capped to MAX_SLEEP_PER_ATTEMPT=60s
    big_delay_resp = make_response(429, {
        "error": {
            "code": 429,
            "message": "retry in 91s",
            "status": "RESOURCE_EXHAUSTED",
            "details": [
                {"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "91s"}
            ],
        }
    })
    with patch_post_sequence([big_delay_resp, big_delay_resp, big_delay_resp]):
        client = GeminiClient(api_key="k")
        with pytest.raises(RuntimeError, match="Gemini API error"):
            await client.generate("p")
    # First retry sleeps 60s (total=60 ≤ 90); second retry would push total to 120 > 90 → no more sleeps
    assert sleep_mock.call_count == 1
