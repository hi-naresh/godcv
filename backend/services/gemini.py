import httpx
import json
import re
from backend.config import (
    GEMINI_ENDPOINT,
    GEMINI_GENERATION_CONFIG,
    GEMINI_SAFETY_SETTINGS,
)


class GeminiClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.endpoint = GEMINI_ENDPOINT

    async def generate(self, prompt: str, json_mode: bool = False) -> str:
        """Call Gemini API and return the text response.
        If json_mode=True, adds instruction to return valid JSON and parses response."""
        gen_config = {**GEMINI_GENERATION_CONFIG}
        if json_mode:
            gen_config["responseMimeType"] = "application/json"

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": gen_config,
            "safetySettings": GEMINI_SAFETY_SETTINGS,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.endpoint}?key={self.api_key}",
                json=payload,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code != 200:
                error_data = response.json()
                msg = error_data.get("error", {}).get("message", f"API error {response.status_code}")
                raise RuntimeError(f"Gemini API error: {msg}")

            data = response.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            return self._clean_response(text)

    async def generate_json(self, prompt: str) -> dict:
        """Call Gemini and parse the response as JSON."""
        text = await self.generate(prompt, json_mode=True)
        return json.loads(text)

    def _clean_response(self, text: str) -> str:
        """Remove markdown code fences if present."""
        cleaned = text.strip()
        cleaned = re.sub(r'^```(?:markdown|json|)?\s*\n', '', cleaned)
        cleaned = re.sub(r'\n```\s*$', '', cleaned)
        return cleaned.strip()
