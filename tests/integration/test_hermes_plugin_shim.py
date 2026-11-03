import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SHIM_DIRECTORY = REPO_ROOT / "deploy" / "hermes-plugin" / "stash"
SUBPROCESS_TIMEOUT_SECONDS = 30

LOAD_THROUGH_SYMLINK = """
import importlib.util
import json
import sys

link = sys.argv[1]
spec = importlib.util.spec_from_file_location(
    "hermes_plugins.stash", link + "/__init__.py", submodule_search_locations=[link]
)
shim = importlib.util.module_from_spec(spec)
sys.modules["hermes_plugins.stash"] = shim
spec.loader.exec_module(shim)


class RecordingContext:
    def __init__(self, config_path):
        self.config_path = config_path
        self.calls = []

    def get_config(self, key, default=None):
        return self.config_path

    def __getattr__(self, name):
        def record(*args, **kwargs):
            self.calls.append(name)

        return record


def register_capturing_failure(ctx):
    try:
        shim.register(ctx)
    except Exception as error:
        return f"{type(error).__name__}: {error}"
    return None
"""

PRINT_SOURCE_ROOT = "print(shim.SOURCE_ROOT)"

REGISTER_TWICE_COUNTING_PATH_ENTRIES = """
ctx = RecordingContext(sys.argv[2])
register_capturing_failure(ctx)
register_capturing_failure(ctx)
print(sys.path.count(str(shim.SOURCE_ROOT)))
"""

REGISTER_WITH_MISSING_CONFIG = """
ctx = RecordingContext(sys.argv[2])
failure = register_capturing_failure(ctx)
print(json.dumps({"failure": failure, "calls": ctx.calls}))
"""


def link_shim(tmp_path: Path) -> Path:
    plugins = tmp_path / "plugins"
    plugins.mkdir()
    link = plugins / "stash"
    link.symlink_to(SHIM_DIRECTORY, target_is_directory=True)
    return link


def run_through_symlink(tmp_path: Path, body: str, config_path: Path) -> str:
    link = link_shim(tmp_path)
    home = tmp_path / "home"
    home.mkdir()
    completed = subprocess.run(
        [sys.executable, "-I", "-c", LOAD_THROUGH_SYMLINK + body, str(link), str(config_path)],
        env={"HOME": str(home), "PATH": os.environ.get("PATH", "")},
        capture_output=True,
        text=True,
        check=False,
        timeout=SUBPROCESS_TIMEOUT_SECONDS,
    )
    assert completed.returncode == 0, completed.stderr
    return completed.stdout.strip()


@pytest.mark.integration
def test_the_shim_loaded_through_a_symlink_points_its_source_root_at_the_repository_src(
    tmp_path: Path,
) -> None:
    # Setup
    config_path = tmp_path / "missing.toml"

    # Execute
    printed = run_through_symlink(tmp_path, PRINT_SOURCE_ROOT, config_path)

    # Assert
    assert Path(printed) == (REPO_ROOT / "src").resolve()


@pytest.mark.integration
def test_registering_twice_puts_the_source_root_on_the_import_path_only_once(
    tmp_path: Path,
) -> None:
    # Setup
    config_path = tmp_path / "missing.toml"

    # Execute
    printed = run_through_symlink(tmp_path, REGISTER_TWICE_COUNTING_PATH_ENTRIES, config_path)

    # Assert
    assert printed == "1"


@pytest.mark.integration
def test_registering_with_a_missing_config_file_fails_naming_that_file(tmp_path: Path) -> None:
    # Setup
    config_path = tmp_path / "absent" / "stash.toml"

    # Execute
    printed = run_through_symlink(tmp_path, REGISTER_WITH_MISSING_CONFIG, config_path)

    # Assert
    assert str(config_path) in json.loads(printed)["failure"]


@pytest.mark.integration
def test_registering_with_a_missing_config_file_registers_nothing_on_the_host(
    tmp_path: Path,
) -> None:
    # Setup
    config_path = tmp_path / "absent" / "stash.toml"

    # Execute
    printed = run_through_symlink(tmp_path, REGISTER_WITH_MISSING_CONFIG, config_path)

    # Assert
    assert json.loads(printed)["calls"] == []
