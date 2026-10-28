# Plant Health Crew

A multi-agent workflow (CrewAI + Gemini) that looks at a plant photo, matches what it sees against a curated reference of plant conditions, and returns a typed care report.

```
photo ──> Inspector ──(inspect_plant_image: Gemini vision)──> what is visible
              │ context
          Pathologist ──(lookup_plant_conditions: curated reference)──> likely conditions, cited by id
              │ context
          Advisor ──> PlantHealthReport (Pydantic, typed JSON)
```

## Quick start
```bash
pip install -r requirements.txt
cp .env.example .env          # paste a Gemini key (free: https://aistudio.google.com/apikey)
python main.py samples/Tomato___Early_blight.jpg
python eval.py                # score the crew on the labelled samples
python -m pytest -q           # 13 offline tests, no key needed
uvicorn api:app --reload      # POST a photo to /analyze
```

## What was wrong with the first version, and the fix

The first version (commit `dba6dae`) looked like a crew, but it was not an agentic workflow:

| Problem in v1 | Effect | Fix in v2 |
|---|---|---|
| The five tools were defined but **never attached to an agent** | Agents had no way to see the photo | Each agent gets the tool for its job (`tools=[...]`) |
| Task text never used `{image_path}` | `kickoff(inputs=...)` was silently ignored | The inspection task contains `{image_path}`, so the path reaches the agent |
| Tools took the **whole image as base64 text** through the LLM | Megabytes of text: could never work | The agent passes a file *path*; the tool reads the bytes itself |
| Result | The saved report described the 612×612 photo as *"a 5x5 pixel representation"*, an analysis invented without seeing the image | The agent's answer is built from tool observations |
| `main.py` called Gemini directly and string-matched `"rectangle"` | Bypassed the crew | `main.py` only runs the crew |
| Every image sent as `image/jpeg`; Gemini key copied into `OPENAI_API_KEY`; retired model | Fragile | MIME type from the file; key passed to `crewai.LLM`; models set in `.env` |
| Free-text output | Hard to use from an app | `output_pydantic=PlantHealthReport` gives typed JSON |
| README claimed 5 agents | The code had 2 | README describes the code |

## Design decisions (and why)

- **Three agents with one job each.** Seeing (inspector), diagnosing (pathologist) and advising (advisor) are separate, so each prompt is small and each failure is easy to locate.
- **Tools return JSON facts, not prose.** The vision tool asks Gemini for a fixed JSON schema (`is_plant`, `image_quality`, symptom list). The inspector is told to report only what the tool returned.
- **Seeing and naming are split on purpose.** The vision tool describes symptoms and is told *not* to name diseases. The pathologist names conditions only by matching those symptoms to the reference, and cites each by `kb_id`. Every diagnosis traces back to an observation and a reference entry.
- **Grounded answers.** `knowledge/plant_conditions.json` holds 14 conditions (signs, crops, care steps), written from standard extension-service descriptions. Care actions must come from the cited entries. The lookup is a transparent keyword-overlap score; with a large reference you would swap it for embedding search, and the tool interface would stay the same.
- **Validate before spending tokens.** File existence, format, size and image integrity are checked in plain Python before any LLM call.
- **Honest uncertainty.** The report carries a confidence per issue and `needs_expert`. Several leaf diseases look alike in a photo, and the crew is told to say "low confidence" rather than guess.
- **Cost control.** Repeated tool calls on the same photo are cached; `max_rpm` keeps the crew inside free-tier rate limits; each run records latency, tokens and request count.

## Evaluation
`eval.py` runs the crew on 15 labelled leaf photos (one per condition, from the PlantVillage dataset) and checks whether the reference id it cites matches the label.

Run on 28 Oct 2026 with `gemini-3.1-flash-lite` on a free API key:

| Photo | Label | Crew cited (most likely first) | Label ranked |
|---|---|---|---|
| Pepper_bell___Bacterial_spot | `bacterial_spot` | `bacterial_spot, early_blight` | first |
| Pepper_bell___healthy | `healthy` | `bacterial_spot, leaf_mold` | miss |
| Potato___Early_blight | `early_blight` | `early_blight, target_spot` | first |
| Potato___healthy | `healthy` | `healthy` | first |
| Potato___Late_blight | `late_blight` | `early_blight, target_spot` | miss |
| Tomato___Bacterial_spot | `bacterial_spot` | `early_blight, bacterial_spot` | second |
| Tomato___Early_blight | `early_blight` | `bacterial_spot, early_blight` | second |
| Tomato___healthy | `healthy` | failed: empty model reply (twice) | n/a |
| Tomato___Late_blight | `late_blight` | `late_blight, bacterial_spot` | first |
| Tomato___Leaf_Mold | `leaf_mold` | `healthy` | miss |
| Tomato___Septoria_leaf_spot | `septoria_leaf_spot` | `bacterial_spot, early_blight` | miss |
| Tomato___Spider_mites_Two-spotted_spider_mite | `spider_mites` | `yellow_leaf_curl_virus, powdery_mildew` | miss |
| Tomato___Target_Spot | `target_spot` | `yellow_leaf_curl_virus` | miss |
| Tomato___Tomato_mosaic_virus | `mosaic_virus` | `yellow_leaf_curl_virus, mosaic_virus` | second |
| Tomato___Tomato_Yellow_Leaf_Curl_Virus | `yellow_leaf_curl_virus` | `yellow_leaf_curl_virus, nitrogen_deficiency` | first |

- **Completed:** 14 of 15 photos (one failed twice with an empty model reply).
- **Label cited first:** 5 of 14. **Label among the top two:** 8 of 14. Random choice among 14 conditions would be right about 1 time in 14.
- **Cost per photo:** about 53.1 s; the agents used 6 LLM requests and about 5,013 tokens (the 2 vision-tool calls are not in that count). The time includes waiting for the free tier's 15-requests-per-minute limit.
- **Where it fails:** look-alike leaf spots (bacterial spot, early blight, Septoria, target spot) get confused, spider-mite stippling was read as a virus, and one healthy pepper was flagged as diseased. Next steps: show the vision tool reference photos of each condition, ask the inspector for more specific features (ring patterns, spot size, halo colour), and test on far more photos.

This is a smoke test, not a benchmark: one photo per condition is far too few for an accuracy claim. It shows that the agents look at the image and cite the reference, and what a run costs. A real evaluation needs dozens of photos per condition.

## Files
```
agents/crew.py            agents, tasks, report schema, validation, analyze()
tools/vision.py           inspect_plant_image: Gemini vision with JSON output, retries, cache
tools/knowledge.py        lookup_plant_conditions: search over the curated reference
knowledge/                plant_conditions.json (14 conditions)
main.py, api.py           command line and FastAPI entry points
eval.py                   scoring on labelled samples (raw run: results/eval_2026-10-28.json)
tests/test_offline.py     13 tests, including one per v1 bug
samples/                  15 PlantVillage leaves + 2 photos from the KRISHIBODH robot
```

Sample leaf images come from the PlantVillage dataset (Hughes & Salathé, 2015). The two `robot_plant_*` photos were taken by the KRISHIBODH gantry robot.
