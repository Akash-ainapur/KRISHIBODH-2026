"""Tool: look at the actual plant photo with Gemini vision.

The old version expected the agent to pass megabytes of base64 text as a tool
argument, so the LLM never really saw the image. Here the agent passes only a
file PATH; the tool reads the bytes itself and sends them to Gemini as an
image part, asking for JSON so the agent receives facts, not prose.
"""
import base64
import json
import mimetypes
import os
import time
from typing import Literal, Type

import requests
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

import config

API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

PROMPTS = {
    "overview": (
        "Look at this photo. Say whether it shows a real plant, which plant it most likely is, which "
        "parts are visible, and how usable the image is for diagnosis. Describe only what you can see."
    ),
    "symptoms": (
        "Look closely at the leaves, stems and fruit in this photo. List every visible symptom "
        "(spots, colour changes, coatings, curling, wilting, pests, webbing). For each, give where it "
        "is and how much of the plant it covers. If the plant looks healthy, return an empty list. "
        "Describe only what you can see; do not name diseases."
    ),
}

SCHEMAS = {
    "overview": {
        "type": "OBJECT",
        "properties": {
            "is_plant": {"type": "BOOLEAN"},
            "plant_type": {"type": "STRING"},
            "visible_parts": {"type": "ARRAY", "items": {"type": "STRING"}},
            "image_quality": {"type": "STRING", "enum": ["good", "fair", "poor"]},
            "summary": {"type": "STRING"},
        },
        "required": ["is_plant", "plant_type", "image_quality", "summary"],
    },
    "symptoms": {
        "type": "OBJECT",
        "properties": {
            "symptoms": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "description": {"type": "STRING"},
                        "location": {"type": "STRING"},
                        "extent": {"type": "STRING", "enum": ["mild", "moderate", "severe"]},
                    },
                    "required": ["description", "location", "extent"],
                },
            },
            "overall_colour": {"type": "STRING"},
        },
        "required": ["symptoms", "overall_colour"],
    },
}


class InspectInput(BaseModel):
    image_path: str = Field(..., description="File path of the plant photo, exactly as given in the task.")
    focus: Literal["overview", "symptoms"] = Field(
        "overview", description="'overview': is it a plant, which one, image quality. 'symptoms': visible damage."
    )


class PlantImageInspector(BaseTool):
    name: str = "inspect_plant_image"
    description: str = (
        "Looks at the real plant photo and returns JSON observations. Call it with focus='overview' "
        "first, then focus='symptoms'. It reports what is visible; it does not diagnose."
    )
    args_schema: Type[BaseModel] = InspectInput

    # Same photo + same focus = same answer. Agents sometimes repeat a tool call; don't pay twice.
    _cache: dict = {}

    def _run(self, image_path: str, focus: str = "overview") -> str:
        try:
            path = os.path.abspath(image_path)
            key = (path, os.path.getmtime(path), focus)
        except OSError:
            return json.dumps({"error": f"cannot read image file: {image_path}"})
        if key not in self._cache:
            self._cache[key] = self._ask_gemini(path, focus)
        return self._cache[key]

    @staticmethod
    def _ask_gemini(path: str, focus: str) -> str:
        mime = mimetypes.guess_type(path)[0] or "image/jpeg"  # the old code sent every image as JPEG
        with open(path, "rb") as f:
            data = base64.b64encode(f.read()).decode("ascii")
        payload = {
            "contents": [{"role": "user", "parts": [
                {"text": PROMPTS[focus]},
                {"inline_data": {"mime_type": mime, "data": data}},
            ]}],
            "generationConfig": {"temperature": 0, "responseMimeType": "application/json",
                                 "responseSchema": SCHEMAS[focus]},
        }
        headers = {"x-goog-api-key": config.require_api_key()}
        url = API_URL.format(model=config.VISION_MODEL)

        last = "unknown error"
        for attempt in range(3):  # retry overload/rate limit; anything else will not fix itself
            try:
                resp = requests.post(url, json=payload, headers=headers, timeout=60)
            except requests.RequestException as exc:
                last = f"network error: {exc}"
            else:
                if resp.status_code == 200:
                    try:
                        text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
                        return json.dumps(json.loads(text))  # validate it really is JSON
                    except (KeyError, IndexError, ValueError):
                        return json.dumps({"error": "vision model returned no usable answer"})
                last = f"HTTP {resp.status_code}"
                if resp.status_code not in (429, 500, 503):
                    break
            time.sleep(2 * (attempt + 1))
        return json.dumps({"error": f"vision request failed ({last})"})
