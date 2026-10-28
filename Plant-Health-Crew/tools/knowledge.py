"""Tool: look up observed symptoms in a small curated reference of plant conditions.

Grounding: the pathologist agent must match symptoms against this reference
and cite entry ids, instead of naming diseases from memory. The search is a
simple keyword-overlap score: transparent, offline and deterministic. With a
large reference you would swap this for embedding search; the tool interface
would not change.
"""
import json
import re
from pathlib import Path
from typing import Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

KB_PATH = Path(__file__).resolve().parent.parent / "knowledge" / "plant_conditions.json"


def load_conditions(path: Path = KB_PATH) -> list:
    return json.loads(path.read_text(encoding="utf-8"))


def _words(text: str) -> set:
    return set(re.findall(r"[a-z]+(?:-[a-z]+)?", text.lower()))


def search_conditions(query: str, conditions: list, top_k: int = 3) -> list:
    """Rank conditions by how many query words appear in their keywords and signs."""
    q = _words(query)
    scored = []
    for c in conditions:
        vocab = _words(" ".join(c["keywords"] + c["signs"]))
        matched = sorted(q & vocab)
        if matched:
            scored.append((len(matched), c, matched))
    scored.sort(key=lambda s: (-s[0], s[1]["id"]))
    return [
        {"id": c["id"], "name": c["name"], "crops": c["crops"], "matched_terms": m,
         "typical_signs": c["signs"], "care": c["care"]}
        for _, c, m in scored[:top_k]
    ]


class LookupInput(BaseModel):
    symptoms: str = Field(..., description="Observed symptoms in plain words, e.g. 'brown spots with rings and a "
                                           "yellow halo on lower leaves'.")


class PlantConditionLookup(BaseTool):
    name: str = "lookup_plant_conditions"
    description: str = (
        "Searches a curated reference of common plant conditions (diseases, pests, nutrient and water "
        "problems, and 'healthy') and returns the best matches with their typical signs and care steps. "
        "Use the returned 'id' when you cite a condition."
    )
    args_schema: Type[BaseModel] = LookupInput

    def _run(self, symptoms: str) -> str:
        matches = search_conditions(symptoms, load_conditions())
        if not matches:
            return json.dumps({"matches": [], "note": "no reference entry matches these words; describe the "
                                                      "symptoms differently or report low confidence"})
        return json.dumps({"matches": matches})
