"""Plant health crew: three agents, two tools, one typed report.

    Inspector ──(inspect_plant_image)──> what is visible
        │ context
    Pathologist ──(lookup_plant_conditions)──> likely conditions, cited by id
        │ context
    Advisor ──> PlantHealthReport (validated by Pydantic)

What makes it agentic, and what was missing before:
  - each agent has a TOOL that returns real observations (the old agents had none,
    so they invented an analysis of an image they never saw)
  - the task text contains {image_path}, so kickoff(inputs=...) actually reaches
    the agents (before, the inputs were silently ignored)
  - later agents receive earlier results through `context`
  - the final answer is a Pydantic model, so the API returns typed JSON, not prose
"""
import time
from pathlib import Path
from typing import List, Literal, Optional

from crewai import LLM, Agent, Crew, Process, Task
from PIL import Image
from pydantic import BaseModel, Field

import config
from tools import PlantConditionLookup, PlantImageInspector


class Issue(BaseModel):
    condition: str = Field(description="Condition name, or 'healthy'")
    kb_id: Optional[str] = Field(description="id from lookup_plant_conditions, or null if none fits")
    evidence: str = Field(description="The visible symptoms that support this condition")
    confidence: Literal["low", "medium", "high"]


class PlantHealthReport(BaseModel):
    is_plant: bool
    plant_type: str
    health_rating: Literal["Excellent", "Good", "Fair", "Poor", "Critical", "Not a plant", "Unclear image"]
    issues: List[Issue] = Field(description="Most likely first; empty if healthy")
    recommended_actions: List[str]
    urgency: Literal["none", "low", "medium", "high"]
    needs_expert: bool = Field(description="True when confidence is low or the problem is serious")
    notes: str


def validate_image(image_path: str) -> Path:
    """Cheap checks in plain Python BEFORE any LLM call: never spend tokens on a bad file."""
    path = Path(image_path)
    if not path.is_file():
        raise ValueError(f"image not found: {image_path}")
    if path.suffix.lower() not in config.SUPPORTED_EXTENSIONS:
        raise ValueError(f"unsupported format {path.suffix}; use {sorted(config.SUPPORTED_EXTENSIONS)}")
    size_mb = path.stat().st_size / (1024 * 1024)
    if size_mb > config.MAX_IMAGE_MB:
        raise ValueError(f"image is {size_mb:.1f} MB; limit is {config.MAX_IMAGE_MB} MB")
    try:
        with Image.open(path) as img:
            img.verify()  # catches truncated or fake image files
    except Exception as exc:
        raise ValueError(f"not a readable image: {exc}") from exc
    return path


def build_crew() -> Crew:
    llm = LLM(model=config.AGENT_MODEL, api_key=config.require_api_key(), temperature=0,
              num_retries=config.LLM_RETRIES)  # passed through to LiteLLM

    inspector = Agent(
        role="Plant Image Inspector",
        goal="Report exactly what is visible in the plant photo, using the inspection tool.",
        backstory="A careful field technician. You never guess beyond what the photo shows.",
        tools=[PlantImageInspector()],
        llm=llm, allow_delegation=False, max_iter=4, verbose=config.CREW_VERBOSE,
    )
    pathologist = Agent(
        role="Plant Pathologist",
        goal="Match the observed symptoms to the most likely conditions in the reference, citing their ids.",
        backstory="A plant doctor who only diagnoses from evidence and says 'low confidence' when unsure.",
        tools=[PlantConditionLookup()],
        llm=llm, allow_delegation=False, max_iter=4, verbose=config.CREW_VERBOSE,
    )
    advisor = Agent(
        role="Crop Care Advisor",
        goal="Turn the findings into a short, practical care report for a farmer.",
        backstory="An extension officer who gives clear, prioritised advice and flags when an expert is needed.",
        llm=llm, allow_delegation=False, verbose=config.CREW_VERBOSE,
    )

    inspect = Task(
        description=(
            "Inspect the plant photo at '{image_path}'.\n"
            "1. Call inspect_plant_image with this exact path and focus='overview'.\n"
            "2. If is_plant is true and image_quality is not 'poor', call it again with focus='symptoms'.\n"
            "Report only what the tool returned. Do not add details of your own."
        ),
        expected_output="The tool's observations: is_plant, plant_type, image_quality, and the symptom list.",
        agent=inspector,
    )
    diagnose = Task(
        description=(
            "Using the inspector's observations, find the most likely conditions.\n"
            "- If the photo is not a plant, or the image is poor, say so and do not diagnose.\n"
            "- If no symptoms were seen, call lookup_plant_conditions with 'healthy uniform green no spots'.\n"
            "- Otherwise call lookup_plant_conditions with the observed symptoms in plain words.\n"
            "Choose at most 2 conditions that the evidence supports, cite each by its reference id, and give "
            "low/medium/high confidence. Several conditions look alike; when unsure, say low confidence."
        ),
        expected_output="Up to 2 candidate conditions with reference ids, supporting evidence and confidence.",
        agent=pathologist,
        context=[inspect],
    )
    advise = Task(
        description=(
            "Write the final report from the inspector's observations and the pathologist's diagnosis.\n"
            "- Recommended actions must come from the care steps of the cited reference entries.\n"
            "- health_rating 'Not a plant' or 'Unclear image' when the inspector says so; then issues is empty.\n"
            "- needs_expert is true when confidence is low or the condition spreads fast or has no cure."
        ),
        expected_output="A PlantHealthReport.",
        agent=advisor,
        context=[inspect, diagnose],
        output_pydantic=PlantHealthReport,
    )

    return Crew(
        agents=[inspector, pathologist, advisor],
        tasks=[inspect, diagnose, advise],
        process=Process.sequential,
        memory=False,
        max_rpm=config.CREW_MAX_RPM,
        verbose=config.CREW_VERBOSE,
    )


def analyze(image_path: str) -> dict:
    """Validate, run the crew, and return the typed report plus cost and latency."""
    path = validate_image(image_path)
    crew = build_crew()
    started = time.perf_counter()
    result = crew.kickoff(inputs={"image_path": str(path)})
    seconds = time.perf_counter() - started
    report = result.pydantic
    if report is None:
        raise RuntimeError(f"the advisor did not return a valid report: {result.raw[:300]}")
    usage = crew.usage_metrics
    return {
        "image": str(path),
        "report": report.model_dump(),
        "seconds": round(seconds, 1),
        "tokens": getattr(usage, "total_tokens", None),
        "llm_requests": getattr(usage, "successful_requests", None),
    }
