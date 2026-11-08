import asyncio
import logging
from datetime import datetime
from pathlib import Path

from app_builders import an_app
from builders import LOS_ANGELES
from clocks import EVENING_IN_LOS_ANGELES
from config_builders import a_stash_config
from fakes.store_factories import FreshStore
from hermes_events import OWNER_ID
from hermes_registration_rig import RegisteredStash, register_stash
from hermes_rig import called
from library_html_rig import rendered, store_of_kept_items
from log_records import recording_logs

LIBRARY_FILE_LOGGER = "stash.hermes_adapter.library_file"
LIBRARY_FILENAME = "stash-library-2026-11-02.html"
LIBRARY_CAPTION = "📚 Your stash library"


def connected_stash(
    tmp_path: Path,
    store: FreshStore | None = None,
    clock: datetime = EVENING_IN_LOS_ANGELES,
    owner_ids: str = OWNER_ID,
) -> RegisteredStash:
    app = an_app(
        store=store or store_of_kept_items(2),
        config=a_stash_config(data_dir=tmp_path),
        clock=lambda: clock,
    )
    plugin = register_stash(app, owner_ids=owner_ids)
    plugin.connect_telegram()
    return plugin


def library_command(plugin: RegisteredStash, arguments: str) -> str:
    return asyncio.run(called(plugin.ctx.commands["library"], arguments))


def test_library_html_sends_one_document_named_for_the_local_date_with_the_caption(
    tmp_path: Path,
) -> None:
    # Setup
    plugin = connected_stash(tmp_path)

    # Execute
    library_command(plugin, "html")

    # Assert
    assert [(sent.chat_id, sent.filename, sent.caption) for sent in plugin.bot.documents] == [
        (OWNER_ID, LIBRARY_FILENAME, LIBRARY_CAPTION)
    ]


def test_library_html_sends_the_html_the_renderer_produces_for_the_local_time(
    tmp_path: Path,
) -> None:
    # Setup
    store = store_of_kept_items(2)
    plugin = connected_stash(tmp_path, store)
    expected = rendered(store, EVENING_IN_LOS_ANGELES.astimezone(LOS_ANGELES))

    # Execute
    library_command(plugin, "html")

    # Assert
    assert [sent.document for sent in plugin.bot.documents] == [expected.encode("utf-8")]


def test_library_html_keeps_the_sent_bytes_as_the_only_file_in_the_local_library_directory(
    tmp_path: Path,
) -> None:
    # Setup
    plugin = connected_stash(tmp_path)

    # Execute
    library_command(plugin, "html")

    # Assert
    kept = {path.name: path.read_bytes() for path in (tmp_path / "library").iterdir()}
    assert kept == {"latest.html": plugin.bot.documents[0].document}


def test_library_html_confirms_with_a_short_reply(tmp_path: Path) -> None:
    # Setup
    plugin = connected_stash(tmp_path)

    # Execute
    reply = library_command(plugin, "html")

    # Assert
    assert reply == "Library sent."


def test_library_html_before_telegram_is_up_logs_the_failure_and_replies_with_an_error_line(
    tmp_path: Path,
) -> None:
    # Setup
    plugin = register_stash(
        an_app(store=store_of_kept_items(1), config=a_stash_config(data_dir=tmp_path))
    )

    # Execute
    with recording_logs(LIBRARY_FILE_LOGGER) as logs:
        reply = library_command(plugin, "html")

    # Assert
    assert (reply, logs.entries()) == (
        "Could not send the library file.",
        [(logging.ERROR, f"could not send the library file to chat {OWNER_ID}")],
    )


def test_library_html_keeps_the_local_copy_when_sending_fails(tmp_path: Path) -> None:
    # Setup
    plugin = register_stash(
        an_app(store=store_of_kept_items(1), config=a_stash_config(data_dir=tmp_path))
    )

    # Execute
    library_command(plugin, "html")

    # Assert
    assert (tmp_path / "library" / "latest.html").exists()


def test_library_html_without_an_owner_chat_says_so_and_sends_nothing(tmp_path: Path) -> None:
    # Setup
    plugin = connected_stash(tmp_path, owner_ids="")

    # Execute
    reply = library_command(plugin, "html")

    # Assert
    assert (reply, plugin.bot.documents) == (
        "No owner chat is set, so there is nowhere to send the library file.",
        [],
    )


def test_library_without_arguments_still_lists_the_kept_items_as_text(tmp_path: Path) -> None:
    # Setup
    plugin = connected_stash(tmp_path, store_of_kept_items(1))

    # Execute
    reply = library_command(plugin, "")

    # Assert
    assert (reply, plugin.bot.documents) == ("📚 Places: Item 0 · ⭐4", [])
