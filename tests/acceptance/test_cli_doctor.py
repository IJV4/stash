from pathlib import Path

from cli_rig import build_cli_rig
from fakes.installed_modules import InstalledModules

PASSING_REPORT = [
    "✔ config — provider ollama, data directory {data}",
    "✔ database — ready at {data}/stash.db",
    "✔ ollama — model local-model is available",
    "✔ openrouter — key is valid; limit remaining: 10",
    "✔ openrouter model — model cloud/model is offered by OpenRouter",
    "! nvidia-smi — no NVIDIA GPU found (nvidia-smi missing or failed)",
    "✔ yt-dlp — installed",
    "! deno — not found on PATH (yt-dlp needs a JavaScript runtime for some sites)",
    "! tesseract — not found on PATH (needed for the OCR eval arm)",
]


def test_with_a_reachable_ollama_that_has_the_model_every_required_line_passes_and_exits_0(
    tmp_path: Path,
) -> None:
    # Setup
    rig = build_cli_rig(tmp_path)
    rig.smi.installed = False

    # Execute
    result = rig.run("doctor")

    # Assert
    expected = [line.format(data=rig.data_dir) for line in PASSING_REPORT]
    assert (result.exit_code, result.lines()) == (0, expected)


def test_a_rejected_openrouter_key_prints_invalid_key_and_exits_1(tmp_path: Path) -> None:
    # Setup
    rig = build_cli_rig(tmp_path, provider="openrouter")
    rig.providers.openrouter_key_valid = False

    # Execute
    result = rig.run("doctor")

    # Assert
    failed = [line for line in result.lines() if line.startswith("✖")]
    assert (result.exit_code, failed) == (
        1,
        ["✖ openrouter — invalid key", "✖ openrouter model — OpenRouter answered HTTP 401"],
    )


def test_an_ollama_model_that_is_not_pulled_prints_how_to_pull_it_and_exits_1(
    tmp_path: Path,
) -> None:
    # Setup
    rig = build_cli_rig(tmp_path)
    rig.providers.ollama_models = ["other-model"]

    # Execute
    result = rig.run("doctor")

    # Assert
    failed = [line for line in result.lines() if line.startswith("✖")]
    assert (result.exit_code, failed) == (
        1,
        ["✖ ollama — model local-model is not pulled (ollama pull local-model)"],
    )


def test_an_openrouter_model_that_openrouter_does_not_list_exits_1(tmp_path: Path) -> None:
    # Setup
    rig = build_cli_rig(tmp_path, provider="openrouter")
    rig.providers.openrouter_models = ["other/model"]

    # Execute
    result = rig.run("doctor")

    # Assert
    failed = [line for line in result.lines() if line.startswith("✖")]
    assert (result.exit_code, failed) == (
        1,
        ["✖ openrouter model — model cloud/model is not offered by OpenRouter"],
    )


def test_a_configured_but_unused_provider_that_fails_is_an_optional_line_and_exits_0(
    tmp_path: Path,
) -> None:
    # Setup
    rig = build_cli_rig(tmp_path)
    rig.providers.openrouter_key_valid = False

    # Execute
    result = rig.run("doctor")

    # Assert
    unused = [line for line in result.lines() if line.startswith("! openrouter")]
    assert (result.exit_code, unused) == (
        0,
        ["! openrouter — invalid key", "! openrouter model — OpenRouter answered HTTP 401"],
    )


def test_a_missing_yt_dlp_package_is_an_optional_line_and_the_exit_code_stays_0(
    tmp_path: Path,
) -> None:
    # Setup
    rig = build_cli_rig(tmp_path)
    rig.modules = InstalledModules()

    # Execute
    result = rig.run("doctor")

    # Assert
    line = [line for line in result.lines() if line.startswith("! yt-dlp")]
    assert (result.exit_code, line) == (0, ["! yt-dlp — not installed"])
