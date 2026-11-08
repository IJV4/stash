from pathlib import Path

import pytest
from cli_rig import LIBRARY_TOKEN, CliRig, build_cli_rig
from fakes.recording_library_servers import SERVING, SHUT_DOWN, RecordingLibraryServers

TOKEN_VAR = "STASH_LIBRARY_TOKEN"
TOKEN_GENERATOR = 'python3 -c "import secrets; print(secrets.token_urlsafe(32))"'


def rig_with_a_token(directory: Path) -> CliRig:
    rig = build_cli_rig(directory)
    rig.env[TOKEN_VAR] = LIBRARY_TOKEN
    return rig


def test_serve_announces_the_address_with_a_token_placeholder_and_never_prints_the_token(
    tmp_path: Path,
) -> None:
    # Setup
    rig = rig_with_a_token(tmp_path)

    # Execute
    result = rig.run("serve")

    # Assert
    assert (result.exit_code, result.out, result.err) == (
        0,
        "Serving the library on http://0.0.0.0:8765/?k=<STASH_LIBRARY_TOKEN>\n",
        "",
    )


def test_serve_announces_the_configured_bind_and_port(tmp_path: Path) -> None:
    # Setup
    rig = rig_with_a_token(tmp_path)
    rig.listening_on("192.168.1.5", 9000)

    # Execute
    result = rig.run("serve")

    # Assert
    assert result.out == "Serving the library on http://192.168.1.5:9000/?k=<STASH_LIBRARY_TOKEN>\n"


def test_serve_starts_the_server_with_the_configured_token_bind_and_port(tmp_path: Path) -> None:
    # Setup
    rig = rig_with_a_token(tmp_path)
    rig.listening_on("192.168.1.5", 9000)

    # Execute
    rig.run("serve")

    # Assert
    created = rig.library_servers.created[0]
    assert (created.token, created.bind, created.port) == (LIBRARY_TOKEN, "192.168.1.5", 9000)


def test_serve_gives_the_server_a_page_source_that_renders_the_stored_items(
    tmp_path: Path,
) -> None:
    # Setup
    rig = rig_with_a_token(tmp_path)
    rig.filed_as("a film to watch", title="Dune")
    pages: list[str] = []
    servers = RecordingLibraryServers(
        while_serving=lambda: pages.append(servers.created[0].snapshot_source())
    )
    rig.library_servers = servers

    # Execute
    rig.run("serve")

    # Assert
    assert "Dune" in pages[0]


@pytest.mark.parametrize(
    "serving_ends_with", [None, KeyboardInterrupt()], ids=["returns", "ctrl-c"]
)
def test_serve_stops_normally_and_shuts_the_server_down_when_serving_ends(
    tmp_path: Path, serving_ends_with: BaseException | None
) -> None:
    # Setup
    rig = rig_with_a_token(tmp_path)
    rig.library_servers = RecordingLibraryServers(serving_ends_with=serving_ends_with)

    # Execute
    result = rig.run("serve")

    # Assert
    assert (result.exit_code, result.err, rig.library_servers.events) == (
        0,
        "",
        [SERVING, SHUT_DOWN],
    )


def test_serve_without_a_token_exits_2_and_starts_no_server(tmp_path: Path) -> None:
    # Setup
    rig = build_cli_rig(tmp_path)

    # Execute
    result = rig.run("serve")

    # Assert
    assert (result.exit_code, result.out, rig.library_servers.created) == (2, "", [])


@pytest.mark.parametrize("hint", [TOKEN_VAR, "24", "A-Z a-z 0-9 - . _ ~", TOKEN_GENERATOR])
def test_serve_without_a_token_says_how_to_set_it_on_standard_error(
    tmp_path: Path, hint: str
) -> None:
    # Setup
    rig = build_cli_rig(tmp_path)

    # Execute
    result = rig.run("serve")

    # Assert
    assert hint in result.err


def test_serve_reports_an_address_it_cannot_listen_on_and_exits_1(tmp_path: Path) -> None:
    # Setup
    rig = rig_with_a_token(tmp_path)
    rig.library_servers = RecordingLibraryServers(bind_failure=OSError("Address already in use"))

    # Execute
    result = rig.run("serve")

    # Assert
    assert (result.exit_code, result.out, result.err) == (
        1,
        "",
        "cannot listen on 0.0.0.0:8765: Address already in use\n",
    )
