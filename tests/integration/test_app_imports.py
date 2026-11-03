import subprocess
import sys

import pytest

HEAVY_MODULES = ("PIL", "pytesseract", "yt_dlp")
PROBE = (
    "import sys\n"
    "import stash.app, stash.cli\n"
    f"print(sorted(name for name in {HEAVY_MODULES!r} if name in sys.modules))\n"
)


@pytest.mark.integration
def test_importing_the_composition_root_and_the_cli_loads_no_imaging_or_extraction_library() -> (
    None
):
    # Execute
    completed = subprocess.run(
        [sys.executable, "-c", PROBE], capture_output=True, text=True, check=True, timeout=30
    )

    # Assert
    assert completed.stdout.strip() == "[]"
