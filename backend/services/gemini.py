import httpx
import json
import re
import logging
from backend.config import (
    GEMINI_ENDPOINT,
    GEMINI_GENERATION_CONFIG,
    GEMINI_SAFETY_SETTINGS,
)

logger = logging.getLogger("godcv.gemini")


class GeminiClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.endpoint = GEMINI_ENDPOINT

    async def generate(self, prompt: str, json_mode: bool = False) -> str:
        """Call Gemini API and return the text response."""
        gen_config = {**GEMINI_GENERATION_CONFIG}
        if json_mode:
            gen_config["responseMimeType"] = "application/json"

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": gen_config,
            "safetySettings": GEMINI_SAFETY_SETTINGS,
        }

        try:
            async with httpx.AsyncClient(timeout=90.0) as client:
                response = await client.post(
                    f"{self.endpoint}?key={self.api_key}",
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )
        except httpx.ConnectError:
            raise RuntimeError("Cannot connect to Gemini API. Check your network connection.")
        except httpx.TimeoutException:
            raise RuntimeError("Gemini API request timed out (90s). Try again or use a shorter resume/JD.")

        if response.status_code != 200:
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

        try:
            data = response.json()
        except Exception:
            raise RuntimeError("Gemini API returned non-JSON response")

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

        return self._clean_response(text)

    async def generate_json(self, prompt: str) -> dict:
        """Call Gemini and parse the response as JSON."""
        text = await self.generate(prompt, json_mode=True)
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse Gemini JSON response: %s\nRaw text: %s", e, text[:500])
            # Try to extract JSON from markdown fences or partial response
            json_match = re.search(r'\{[\s\S]*\}', text)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass
            raise RuntimeError(f"Gemini returned invalid JSON. This sometimes happens — please retry.")

    def _clean_response(self, text: str) -> str:
        """Remove markdown code fences if present."""
        cleaned = text.strip()
        cleaned = re.sub(r'^```(?:markdown|json|)?\s*\n', '', cleaned)
        cleaned = re.sub(r'\n```\s*$', '', cleaned)
        return cleaned.strip()
