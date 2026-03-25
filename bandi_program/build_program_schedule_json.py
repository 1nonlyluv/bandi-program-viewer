from __future__ import annotations

import argparse
import json
from pathlib import Path

from program_schedule_normalizer import normalize_payload
from program_schedule_parser import parse_program_sheet


def main() -> None:
    parser = argparse.ArgumentParser(description="Build program schedule JSON from a weekly XLSX workbook.")
    parser.add_argument("xlsx_path", help="Source XLSX path.")
    parser.add_argument(
        "--output",
        default="webapp/assets/program_schedule.json",
        help="Output JSON path.",
    )
    args = parser.parse_args()

    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    parsed = normalize_payload(parse_program_sheet(args.xlsx_path))
    output_path.write_text(json.dumps(parsed, ensure_ascii=False, indent=2), encoding="utf-8")
    print(output_path)


if __name__ == "__main__":
    main()
