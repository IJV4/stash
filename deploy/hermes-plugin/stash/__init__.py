import sys
from pathlib import Path
from typing import Any

SOURCE_ROOT = Path(__file__).resolve().parents[3] / "src"


def register(ctx: Any) -> None:
    if str(SOURCE_ROOT) not in sys.path:
        sys.path.insert(0, str(SOURCE_ROOT))
    from stash.hermes_adapter.plugin import register as register_plugin

    register_plugin(ctx)
