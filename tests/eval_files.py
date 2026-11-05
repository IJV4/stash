import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

REPOSITORY = Path(__file__).resolve().parents[1]
SHIPPED_CASES = REPOSITORY / "evals" / "cases.jsonl"
SHIPPED_IMAGES = REPOSITORY / "evals" / "images"
FAKE_IMAGE_BYTES = b"fake png bytes"


def write_cases(directory: Path, *cases: Mapping[str, Any], image: str = "card.png") -> Path:
    path = directory / "cases.jsonl"
    path.write_text("\n".join(json.dumps(case) for case in cases) + "\n")
    (directory / image).write_bytes(FAKE_IMAGE_BYTES)
    return path
