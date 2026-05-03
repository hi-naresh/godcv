import asyncio
import httpx
import json
import random
import re
import logging
from backend.config import (
    GEMINI_BASE_URL,
    GEMINI_DEFAULT_MODEL,
    GEMINI_MODEL_CHAIN,
    GEMINI_GENERATION_CONFIG,
    GEMINI_SAFETY_SETTINGS,
)

logger = logging.getLogger("godcv.gemini")

# Global usage tracker (per-process, resets on restart)
_usage = {
    "total_requests": 0,
    "total_prompt_tokens": 0,
    "total_completion_tokens": 0,
    "total_tokens": 0,
    "errors": 0,
    "model": GEMINI_DEFAULT_MODEL,
}

# Rate limit info from last response headers
_rate_limits: dict = {}

# Per-minute sliding window tracking
import time
_minute_log: list[dict] = []  # [{ts, prompt, completion}]
_day_log: list[float] = []    # [timestamp]


RETRYABLE_STATUSES = {429, 500, 502, 503, 504}
MAX_ATTEMPTS = 3
MAX_SLEEP_PER_ATTEMPT = 60.0
MAX_TOTAL_WAIT = 90.0

# ── Concurrency limiter ────────────────────────────────────────────────────────
MAX_CONCURRENT_CALLS = 3
_semaphore: asyncio.Semaphore | None = None


def _get_semaphore() -> asyncio.Semaphore:
    global _semaphore
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(MAX_CONCURRENT_CALLS)
    return _semaphore


# ── Per-model sliding-window rate limiters ─────────────────────────────────────
# Each model gets its own semaphore sized to its RPM limit.
# Tokens auto-release after 60 s → at most rpm_limit calls per 60-second window.
_model_sems: dict[str, asyncio.Semaphore] = {}


def _get_model_sem(model_id: str, rpm_limit: int) -> asyncio.Semaphore:
    if model_id not in _model_sems:
        _model_sems[model_id] = asyncio.Semaphore(rpm_limit)
    return _model_sems[model_id]


async def _acquire_model_slot(model_id: str, rpm_limit: int) -> None:
    sem = _get_model_sem(model_id, rpm_limit)
    t0 = time.monotonic()
    await sem.acquire()
    waited = time.monotonic() - t0
    if waited > 0.5:
        logger.info("Rate limiter [%s]: waited %.1fs for slot (RPM %d cap)", model_id, waited, rpm_limit)
    asyncio.get_running_loop().call_later(60.0, sem.release)


# ── Daily-quota exhaustion tracking & model rotation ──────────────────────────
_exhausted_models: set[str] = set()
_exhaustion_date: str = ""


def _reset_exhaustion_if_new_day() -> None:
    global _exhausted_models, _exhaustion_date
    today = time.strftime("%Y-%m-%d")
    if today != _exhaustion_date:
        _exhaustion_date = today
        _exhausted_models = set()


def _active_model_config() -> tuple[str, int]:
    """Return (model_id, rpm_limit) for the first non-exhausted model in the chain."""
    _reset_exhaustion_if_new_day()
    for model_id, rpm, _rpd in GEMINI_MODEL_CHAIN:
        if model_id not in _exhausted_models:
            return model_id, rpm
    # All models exhausted today — fall back to primary and let it fail naturally
    logger.error("All models in GEMINI_MODEL_CHAIN exhausted for today. Quota resets at midnight.")
    return GEMINI_MODEL_CHAIN[0][0], GEMINI_MODEL_CHAIN[0][1]


def _mark_daily_exhausted(model_id: str) -> None:
    _exhausted_models.add(model_id)
    remaining = [m for m, _, _ in GEMINI_MODEL_CHAIN if m not in _exhausted_models]
    next_model = remaining[0] if remaining else "none — all exhausted"
    logger.warning("Daily quota exhausted for %s → switching to %s", model_id, next_model)


def _is_daily_quota_error(retry_delay: float) -> bool:
    """Retry delays >> 1 minute indicate a daily (not per-minute) quota hit."""
    return retry_delay > 300


def _parse_retry_delay(error_data: dict, message: str) -> float:
    """Extract retry delay (seconds) from a Gemini 429 error, or fall back."""
    details = error_data.get("error", {}).get("details", [])
    for d in details:
        if d.get("@type", "").endswith("RetryInfo"):
            raw = d.get("retryDelay", "")
            if raw.endswith("s"):
                try:
                    return float(raw[:-1])
                except ValueError:
                    pass
    match = re.search(r"retry in (\d+(?:\.\d+)?)s", message, re.IGNORECASE)
    if match:
        return float(match.group(1))
    return 30.0


def _prune_logs():
    now = time.time()
    # Keep last 60s for per-minute stats
    while _minute_log and now - _minute_log[0]["ts"] > 60:
        _minute_log.pop(0)
    # Keep last 24h for per-day stats
    while _day_log and now - _day_log[0] > 86400:
        _day_log.pop(0)


def get_usage() -> dict:
    _prune_logs()
    rpm = len(_minute_log)
    tpm = sum(e["prompt"] + e["completion"] for e in _minute_log)
    rpd = len(_day_log)
    return {
        **_usage,
        "rate_limits": {**_rate_limits},
        "rpm": rpm,
        "tpm": tpm,
        "rpd": rpd,
    }


def reset_usage():
    for k in _usage:
        if k == "model":
            continue
        _usage[k] = 0


class GeminiClient:
    def __init__(self, api_key: str, model: str | None = None):
        self.api_key = api_key
        # If caller names an explicit model, pin to it (no rotation).
        # Otherwise, rotate through GEMINI_MODEL_CHAIN automatically.
        self._explicit_model = model
        self.model = model or _active_model_config()[0]  # exposed for logging

    async def generate(self, prompt: str, json_mode: bool = False) -> str:
        """Call Gemini API and return the text response, rotating models on daily quota."""
        gen_config = {**GEMINI_GENERATION_CONFIG}
        if json_mode:
            gen_config["responseMimeType"] = "application/json"

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": gen_config,
            "safetySettings": GEMINI_SAFETY_SETTINGS,
        }

        tried_models: set[str] = set()

        # Outer loop: advance to next model when daily quota is exhausted.
        while True:
            if self._explicit_model:
                model_id = self._explicit_model
                # Derive rpm_limit from chain if it's listed there, else use a safe default
                rpm_limit = next(
                    (rpm for m, rpm, _ in GEMINI_MODEL_CHAIN if m == model_id), 4
                )
            else:
                model_id, rpm_limit = _active_model_config()

            if model_id in tried_models:
                raise RuntimeError(
                    "All Gemini models have exhausted their daily quota. Quota resets at midnight."
                )
            tried_models.add(model_id)
            self.model = model_id  # keep exposed attr current

            endpoint = f"{GEMINI_BASE_URL}/models/{model_id}:generateContent"

            # Reserve one sliding-window slot before firing.
            await _acquire_model_slot(model_id, rpm_limit)

            total_waited = 0.0
            response = None
            rotate_to_next = False

            for attempt in range(MAX_ATTEMPTS):
                async with _get_semaphore():
                    try:
                        async with httpx.AsyncClient(timeout=90.0) as client:
                            response = await client.post(
                                f"{endpoint}?key={self.api_key}",
                                json=payload,
                                headers={"Content-Type": "application/json"},
                            )
                    except httpx.ConnectError:
                        raise RuntimeError("Cannot connect to Gemini API. Check your network connection.")
                    except httpx.TimeoutException:
                        raise RuntimeError("Gemini API request timed out (90s). Try again or use a shorter resume/JD.")

                    _usage["total_requests"] += 1
                    _usage["model"] = model_id

                    headers = response.headers
                    for h in ["x-ratelimit-limit-requests", "x-ratelimit-remaining-requests",
                               "x-ratelimit-limit-tokens", "x-ratelimit-remaining-tokens",
                               "x-ratelimit-reset-requests", "x-ratelimit-reset-tokens"]:
                        if h in headers:
                            _rate_limits[h.replace("x-ratelimit-", "")] = headers[h]

                    remaining = _rate_limits.get("remaining-requests", "")
                    if remaining and remaining.isdigit() and int(remaining) < 3:
                        logger.warning("Gemini quota low [%s]: only %s requests remaining in window", model_id, remaining)

                if response.status_code == 200:
                    break

                if response.status_code not in RETRYABLE_STATUSES or attempt == MAX_ATTEMPTS - 1:
                    break

                try:
                    error_data = response.json()
                    msg = error_data.get("error", {}).get("message", "")
                except Exception:
                    error_data, msg = {}, ""

                if response.status_code == 429:
                    retry_delay = _parse_retry_delay(error_data, msg)
                    # Daily quota exhausted (delay >> 1 min): rotate to next model immediately.
                    if _is_daily_quota_error(retry_delay) and not self._explicit_model:
                        _mark_daily_exhausted(model_id)
                        rotate_to_next = True
                        break
                    base_delay = min(retry_delay, MAX_SLEEP_PER_ATTEMPT)
                    reason = "rate-limited (429)"
                else:
                    base_delay = min(2.0 * (2 ** attempt), MAX_SLEEP_PER_ATTEMPT)
                    reason = f"server error ({response.status_code})"

                delay = base_delay * (0.75 + random.random() * 0.5)
                if total_waited + delay > MAX_TOTAL_WAIT:
                    break

                logger.info("Gemini %s [%s] — retrying in %.1fs (attempt %d/%d)",
                            reason, model_id, delay, attempt + 1, MAX_ATTEMPTS)
                await asyncio.sleep(delay)
                total_waited += delay

            if rotate_to_next:
                continue  # pick next model from chain

            if response.status_code != 200:
                _usage["errors"] += 1
                try:
                    error_data = response.json()
                    msg = error_data.get("error", {}).get("message", "")
                except Exception:
                    msg = ""
                if not msg:
                    msg = f"HTTP {response.status_code}"
                if response.status_code == 400 and "API key" in msg:
                    raise RuntimeError(f"Invalid Gemini API key: {msg}")
                raise RuntimeError(f"Gemini API error: {msg}")

            break  # success — exit model rotation loop

        try:
            data = response.json()
        except Exception:
            raise RuntimeError("Gemini API returned non-JSON response")

        # Track token usage
        usage_meta = data.get("usageMetadata", {})
        prompt_tokens = usage_meta.get("promptTokenCount", 0)
        completion_tokens = usage_meta.get("candidatesTokenCount", 0)
        _usage["total_prompt_tokens"] += prompt_tokens
        _usage["total_completion_tokens"] += completion_tokens
        _usage["total_tokens"] += prompt_tokens + completion_tokens

        # Sliding window logs
        now = time.time()
        _minute_log.append({"ts": now, "prompt": prompt_tokens, "completion": completion_tokens})
        _day_log.append(now)

        candidates = data.get("candidates", [])
        if not candidates:
            # Check for safety block
            block_reason = data.get("promptFeedback", {}).get("blockReason", "")
            if block_reason:
                raise RuntimeError(f"Gemini blocked the request: {block_reason}")
            raise RuntimeError("Gemini returned no candidates (empty response)")

        try:
            text = candidates[0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError):
            finish_reason = candidates[0].get("finishReason", "unknown")
            if finish_reason == "SAFETY":
                raise RuntimeError("Gemini blocked the response due to safety filters")
            raise RuntimeError(f"Gemini returned unexpected response structure (finishReason: {finish_reason})")

        finish_reason = candidates[0].get("finishReason", "")
        if finish_reason == "MAX_TOKENS":
            prompt_hint = prompt[:80].replace('\n', ' ')
            logger.warning("Gemini response truncated (MAX_TOKENS). Output: %d chars. Prompt starts: '%s...'", len(text), prompt_hint)

        return self._clean_response(text)

    async def generate_json(self, prompt: str) -> dict:
        """Call Gemini and parse the response as JSON."""
        text = await self.generate(prompt, json_mode=True)
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.warning("Initial JSON parse failed: %s — attempting repair", e)
            repaired = self._repair_json(text)
            try:
                return json.loads(repaired)
            except json.JSONDecodeError:
                logger.error("JSON repair also failed.\nRaw text:\n%s", text[:2000])
                raise RuntimeError("Gemini returned invalid JSON. This sometimes happens — please retry.")

    def _repair_json(self, text: str) -> str:
        """Attempt to fix common JSON issues from LLM output."""
        s = text.strip()
        # Remove markdown fences
        s = re.sub(r'^```(?:json)?\s*\n?', '', s)
        s = re.sub(r'\n?```\s*$', '', s)
        # Remove trailing commas before } or ]
        s = re.sub(r',\s*([}\]])', r'\1', s)
        # Remove control characters (except newline/tab which are valid in strings)
        s = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', s)
        # Fix unescaped newlines inside string values — replace with \n
        # This handles the case where Gemini puts literal newlines in JSON string values
        lines = s.split('\n')
        fixed_lines = []
        in_string = False
        for line in lines:
            # Count unescaped quotes to track string state
            quote_count = 0
            i = 0
            while i < len(line):
                if line[i] == '\\':
                    i += 2
                    continue
                if line[i] == '"':
                    quote_count += 1
                i += 1
            if in_string:
                # We're continuing a string from previous line — escape this line into it
                fixed_lines[-1] = fixed_lines[-1] + '\\n' + line
            else:
                fixed_lines.append(line)
            # Odd number of quotes means we're now inside/outside a string
            if quote_count % 2 == 1:
                in_string = not in_string
        s = '\n'.join(fixed_lines)
        # Truncate at last valid closing brace if there's garbage after
        last_brace = s.rfind('}')
        if last_brace != -1 and last_brace < len(s) - 1:
            tail = s[last_brace + 1:].strip()
            if tail and not tail.startswith(']'):
                s = s[:last_brace + 1]

        # Handle truncated JSON (Gemini hit MAX_TOKENS mid-output)
        # Count unmatched braces/brackets and close them
        open_braces = 0
        open_brackets = 0
        in_str = False
        i = 0
        while i < len(s):
            c = s[i]
            if c == '\\' and in_str:
                i += 2
                continue
            if c == '"':
                in_str = not in_str
            elif not in_str:
                if c == '{': open_braces += 1
                elif c == '}': open_braces -= 1
                elif c == '[': open_brackets += 1
                elif c == ']': open_brackets -= 1
            i += 1

        # If we're inside a string, close it
        if in_str:
            s += '"'
        # Remove trailing comma before we close
        s = re.sub(r',\s*$', '', s)
        # Close unmatched brackets/braces
        s += ']' * max(0, open_brackets)
        s += '}' * max(0, open_braces)
        # Final trailing comma cleanup after closing
        s = re.sub(r',\s*([}\]])', r'\1', s)
        return s

    def _clean_response(self, text: str) -> str:
        """Remove markdown code fences if present."""
        cleaned = text.strip()
        cleaned = re.sub(r'^```(?:markdown|json|)?\s*\n', '', cleaned)
        cleaned = re.sub(r'\n```\s*$', '', cleaned)
        return cleaned.strip()
