"""HTTP API: POST a photo, get the typed PlantHealthReport back.

    uvicorn api:app --reload
    curl -F "file=@leaf.jpg" http://127.0.0.1:8000/analyze
"""
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile

import config
from agents import analyze

app = FastAPI(title="Plant Health Crew")


@app.get("/health")
def health():
    return {"status": "ok", "agent_model": config.AGENT_MODEL, "vision_model": config.VISION_MODEL}


@app.post("/analyze")
def analyze_photo(file: UploadFile = File(...)):
    # A plain `def` endpoint: FastAPI runs it in a worker thread, so the slow crew
    # run does not block other requests.
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in config.SUPPORTED_EXTENSIONS:
        raise HTTPException(415, f"unsupported file type {suffix or '(none)'}")
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / f"upload{suffix}"
        path.write_bytes(file.file.read())
        try:
            return analyze(str(path))
        except ValueError as exc:
            raise HTTPException(422, str(exc))
        except RuntimeError as exc:
            raise HTTPException(502, str(exc))
