from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Write webapp version metadata.")
    parser.add_argument("--output", default="webapp/assets/version.json")
    parser.add_argument("--version", default="")
    args = parser.parse_args()

    version = args.version.strip() or datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    payload = {
        "version": version,
        "generatedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
