"""Settings, read from the environment (.env). Nothing here calls an API."""
import os

from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

# The vision tool calls Gemini directly with the image bytes.
VISION_MODEL = os.getenv("VISION_MODEL", "gemini-3.1-flash-lite")
# The agents reason with this model, addressed through LiteLLM ("provider/model").
AGENT_MODEL = os.getenv("AGENT_MODEL", "gemini/gemini-3.1-flash-lite")

MAX_IMAGE_MB = float(os.getenv("MAX_IMAGE_MB", "10"))
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

CREW_VERBOSE = os.getenv("CREW_VERBOSE", "false").lower() == "true"
# A free key allows 15 requests per minute in total. The crew's own LLM calls are
# capped here; the vision tool's calls come on top, so keep headroom.
CREW_MAX_RPM = int(os.getenv("CREW_MAX_RPM", "6"))
# LiteLLM retries rate-limit (429) and overload (503) errors with backoff.
LLM_RETRIES = int(os.getenv("LLM_RETRIES", "4"))


def require_api_key() -> str:
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not set. Add it to .env (see .env.example).")
    return GEMINI_API_KEY
