from __future__ import annotations

import argparse
import json
import unicodedata
import zipfile
from pathlib import Path

from meal_schedule_parser import parse_meal_workbook


def build_meal_schedule(paths: list[str | Path]) -> dict:
    days: dict[str, dict] = {}
    sources: list[dict] = []
    for path in paths:
        for payload in parse_meal_workbook(path):
            sources.append(payload["meta"])
            for date, meals in payload["days"].items():
                days.setdefault(date, {}).update(meals)
    return {"meta": {"sources": sources}, "days": dict(sorted(days.items()))}


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a date-indexed meal menu JSON file from meal plan XLSX workbooks.")
    parser.add_argument("xlsx_path", nargs="*", help="Source meal plan workbooks. If omitted, scans the current directory.")
    parser.add_argument("--output", default="webapp/assets/meal_schedule.json")
    args = parser.parse_args()
    paths = (
        [Path(path) for path in args.xlsx_path]
        if args.xlsx_path
        else sorted(
            path
            for path in Path(".").glob("*.xlsx")
            if not unicodedata.normalize("NFC", path.name).startswith("~$")
            and "식단표" in unicodedata.normalize("NFC", path.name)
            and zipfile.is_zipfile(path)
        )
    )
    bundle = build_meal_schedule(paths)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(output.resolve())


if __name__ == "__main__":
    main()
