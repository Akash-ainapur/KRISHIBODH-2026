"""Score the crew on labelled leaf photos (PlantVillage samples in samples/).

The label is in the file name, e.g. Tomato___Early_blight.jpg -> early_blight.
A small smoke-test set (one photo per condition), NOT a benchmark: it shows
whether the agents look at the image and cite the right reference entry, and
what a run costs in time and tokens.

    python eval.py            -> prints a table, writes reports/eval.json
"""
import json
import sys
import time
from pathlib import Path

from agents import analyze

LABELS = {
    "Bacterial_spot": "bacterial_spot",
    "Early_blight": "early_blight",
    "Late_blight": "late_blight",
    "Leaf_Mold": "leaf_mold",
    "Septoria_leaf_spot": "septoria_leaf_spot",
    "Spider_mites_Two-spotted_spider_mite": "spider_mites",
    "Target_Spot": "target_spot",
    "Tomato_Yellow_Leaf_Curl_Virus": "yellow_leaf_curl_virus",
    "Tomato_mosaic_virus": "mosaic_virus",
    "healthy": "healthy",
}


def expected_id(path: Path):
    return LABELS.get(path.stem.split("___")[-1])


def predicted_ids(report: dict) -> list:
    ids = [i["kb_id"] for i in report["issues"] if i.get("kb_id")]
    return ids or ["healthy"]  # no issues reported = called healthy


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")
    photos = sorted(p for p in Path("samples").glob("*.jpg") if expected_id(p))
    rows = []
    for p in photos:
        want = expected_id(p)
        try:
            try:
                out = analyze(str(p))
            except Exception:  # usually the per-minute quota: wait it out and try once more
                time.sleep(65)
                out = analyze(str(p))
            got = predicted_ids(out["report"])
            rows.append({"image": p.name, "expected": want, "predicted": got,
                         "top1": got[0] == want, "top2": want in got[:2],
                         "seconds": out["seconds"], "tokens": out["tokens"], "requests": out["llm_requests"]})
        except Exception as exc:  # one failed photo must not lose the whole run
            rows.append({"image": p.name, "expected": want, "error": str(exc)[:200]})
        r = rows[-1]
        print(f"{p.name:48} want {want:24} got {','.join(r.get('predicted', ['ERROR'])):34} "
              f"{'top1' if r.get('top1') else 'top2' if r.get('top2') else 'miss'}", flush=True)
        time.sleep(3)  # stay under free-tier rate limits

    ok = [r for r in rows if "error" not in r]
    summary = {
        "photos": len(rows),
        "completed": len(ok),
        "top1_correct": sum(r["top1"] for r in ok),
        "top2_correct": sum(r["top2"] for r in ok),
        "mean_seconds": round(sum(r["seconds"] for r in ok) / len(ok), 1) if ok else None,
        "mean_tokens": round(sum(r["tokens"] or 0 for r in ok) / len(ok)) if ok else None,
    }
    print("\n" + json.dumps(summary, indent=2))
    Path("reports").mkdir(exist_ok=True)
    Path("reports/eval.json").write_text(json.dumps({"summary": summary, "rows": rows}, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
