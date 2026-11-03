from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[1]
SHIPPED_CASES = REPOSITORY / "evals" / "cases.jsonl"
SHIPPED_IMAGES = REPOSITORY / "evals" / "images"
