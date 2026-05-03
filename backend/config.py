import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "") or os.environ.get("GODCV_GEMINI_API_KEY", "")
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

# Model rotation chain — ordered by preference.
# Format: (api_model_id, rpm_self_limit, rpd_limit)
# rpm_self_limit is set 1 below Google's stated limit to leave headroom.
# Model IDs sourced from https://ai.google.dev/gemini-api/docs/models
GEMINI_MODEL_CHAIN: list[tuple[str, int, int]] = [
    ("gemini-3.1-flash-lite-preview", 14, 500),  # 15 RPM, 500 RPD  ← primary
    ("gemini-2.5-flash-lite",          9,  20),  # 10 RPM,  20 RPD  (stable)
    ("gemini-2.5-flash",               4,  20),  #  5 RPM,  20 RPD  (stable)
]
GEMINI_DEFAULT_MODEL = GEMINI_MODEL_CHAIN[0][0]
GEMINI_ENDPOINT = f"{GEMINI_BASE_URL}/models/{GEMINI_DEFAULT_MODEL}:generateContent"
GEMINI_GENERATION_CONFIG = {
    "temperature": 0.7,
    "topK": 40,
    "topP": 0.95,
    "maxOutputTokens": 16384,
}
GEMINI_SAFETY_SETTINGS = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
]

DB_PATH = str(BASE_DIR / "data" / "godcv.db")
FRONTEND_DIST = str(BASE_DIR / "frontend" / "dist")
