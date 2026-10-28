"""Offline tests: no API key, no network. Run with: python -m pytest -q"""
import base64
import json
import os

import pytest
from PIL import Image

os.environ.setdefault("GEMINI_API_KEY", "test-key-not-real")

import config  # noqa: E402
from agents import PlantHealthReport, build_crew, validate_image  # noqa: E402
from tools import PlantConditionLookup, PlantImageInspector  # noqa: E402
from tools.knowledge import load_conditions, search_conditions  # noqa: E402


@pytest.fixture
def png(tmp_path):
    p = tmp_path / "leaf.png"
    Image.new("RGB", (8, 8), (40, 160, 40)).save(p)
    return p


# ---- knowledge tool ---------------------------------------------------------

def test_reference_entries_are_well_formed():
    conditions = load_conditions()
    ids = [c["id"] for c in conditions]
    assert len(ids) == len(set(ids)), "duplicate ids"
    for c in conditions:
        assert c["signs"] and c["keywords"] and c["care"], c["id"]


@pytest.mark.parametrize("symptoms, expected", [
    ("brown spots with concentric rings and a yellow halo on older lower leaves", "early_blight"),
    ("white powdery coating on the leaves", "powdery_mildew"),
    ("fine speckling and webbing under the leaves, bronze colour", "spider_mites"),
    ("light and dark green mottled mosaic pattern, distorted leaves", "mosaic_virus"),
    ("healthy uniform green no spots", "healthy"),
])
def test_lookup_ranks_the_matching_condition_first(symptoms, expected):
    assert search_conditions(symptoms, load_conditions())[0]["id"] == expected


def test_lookup_tool_reports_no_match_instead_of_guessing():
    out = json.loads(PlantConditionLookup()._run("zzz qqq"))
    assert out["matches"] == [] and "note" in out


# ---- vision tool ------------------------------------------------------------

class FakeResponse:
    def __init__(self, status, body):
        self.status_code = status
        self._body = body

    def json(self):
        return self._body


def gemini_reply(obj):
    return {"candidates": [{"content": {"parts": [{"text": json.dumps(obj)}]}}]}


def test_vision_tool_sends_real_image_bytes_with_correct_mime(png, monkeypatch):
    sent = {}

    def fake_post(url, json=None, headers=None, timeout=None):
        sent.update(url=url, payload=json, headers=headers)
        return FakeResponse(200, gemini_reply({"is_plant": True, "plant_type": "tomato",
                                               "image_quality": "good", "summary": "a leaf"}))

    monkeypatch.setattr("tools.vision.requests.post", fake_post)
    out = json.loads(PlantImageInspector()._run(str(png), "overview"))

    assert out["plant_type"] == "tomato"
    image_part = sent["payload"]["contents"][0]["parts"][1]["inline_data"]
    assert image_part["mime_type"] == "image/png"                    # old code: always image/jpeg
    assert base64.b64decode(image_part["data"]) == png.read_bytes()  # the actual file, not a description
    assert sent["payload"]["generationConfig"]["responseMimeType"] == "application/json"
    assert sent["headers"]["x-goog-api-key"] == config.GEMINI_API_KEY


def test_vision_tool_caches_repeat_calls(png, monkeypatch):
    calls = []

    def fake_post(*a, **k):
        calls.append(1)
        return FakeResponse(200, gemini_reply({"symptoms": [], "overall_colour": "green"}))

    monkeypatch.setattr("tools.vision.requests.post", fake_post)
    tool = PlantImageInspector()
    tool._run(str(png), "symptoms")
    tool._run(str(png), "symptoms")
    assert len(calls) == 1


def test_vision_tool_returns_error_json_instead_of_raising(png, monkeypatch):
    monkeypatch.setattr("tools.vision.requests.post", lambda *a, **k: FakeResponse(400, {}))
    out = json.loads(PlantImageInspector()._run(str(png), "overview"))
    assert "error" in out  # the agent can read this and report it


def test_vision_tool_handles_missing_file():
    assert "error" in json.loads(PlantImageInspector()._run("does/not/exist.png", "overview"))


# ---- validation before any LLM call -----------------------------------------

def test_validate_rejects_missing_unsupported_and_fake_images(tmp_path, png):
    assert validate_image(str(png)) == png
    with pytest.raises(ValueError, match="not found"):
        validate_image(str(tmp_path / "nope.jpg"))
    txt = tmp_path / "notes.txt"
    txt.write_text("hi")
    with pytest.raises(ValueError, match="unsupported"):
        validate_image(str(txt))
    fake = tmp_path / "fake.jpg"
    fake.write_bytes(b"not really a jpeg")
    with pytest.raises(ValueError, match="not a readable image"):
        validate_image(str(fake))


# ---- crew wiring (the bugs in the original version) -------------------------

def test_crew_is_wired_correctly():
    crew = build_crew()
    inspector, pathologist, advisor = crew.agents
    inspect, diagnose, advise = crew.tasks

    assert [t.name for t in inspector.tools] == ["inspect_plant_image"]       # old agents had no tools
    assert [t.name for t in pathologist.tools] == ["lookup_plant_conditions"]
    assert "{image_path}" in inspect.description                               # old tasks ignored the inputs
    assert diagnose.context == [inspect]
    assert advise.context == [inspect, diagnose]
    assert advise.output_pydantic is PlantHealthReport                        # typed output, not prose
    assert not crew.memory
