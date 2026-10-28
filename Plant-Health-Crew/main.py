"""Command line: python main.py path/to/plant.jpg"""
import argparse
import json
import sys
from pathlib import Path

from agents import analyze


def main() -> int:
    # CrewAI prints emoji; the default Windows console code page cannot encode them.
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Analyse a plant photo with the plant health crew.")
    parser.add_argument("image_path", help="Path to a .jpg, .png or .webp plant photo")
    args = parser.parse_args()

    try:
        out = analyze(args.image_path)
    except (ValueError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(out, indent=2))
    reports = Path("reports")
    reports.mkdir(exist_ok=True)
    target = reports / f"{Path(args.image_path).stem}.json"
    target.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nsaved {target}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
