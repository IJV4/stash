from pathlib import Path

import pytest
from cli_rig import build_cli_rig

from stash.app import build_app
from stash.config import ProviderName
from stash.config.loader import load_config


@pytest.mark.integration
def test_an_app_built_without_a_client_makes_its_own_and_still_wires_every_provider(
    tmp_path: Path,
) -> None:
    # Setup
    rig = build_cli_rig(tmp_path)
    config = load_config(rig.config_file, rig.env)

    # Execute
    app = build_app(config, run=rig.smi, which=rig.search_path, clock=lambda: rig.now)

    # Assert
    assert {target.choice.provider for target in app.eval_targets.targets} == {
        ProviderName.OLLAMA,
        ProviderName.OPENROUTER,
    }
    app.close()


@pytest.mark.integration
def test_closing_an_app_that_made_its_own_client_closes_that_client(tmp_path: Path) -> None:
    # Setup
    rig = build_cli_rig(tmp_path)
    app = build_app(
        load_config(rig.config_file, rig.env),
        run=rig.smi,
        which=rig.search_path,
        clock=lambda: rig.now,
    )

    # Execute
    app.close()

    # Assert
    [ollama] = [line for line in app.doctor.run().lines if line.name == "ollama"]
    assert "client has been closed" in ollama.detail
