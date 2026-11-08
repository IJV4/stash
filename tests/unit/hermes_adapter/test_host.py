import logging

from fakes.stub_secret_scope import (
    SECRET_SCOPE_MODULE,
    StubSecretScope,
    importer_without_hermes,
)
from log_records import recording_logs

from stash.hermes_adapter.host import hermes_secret, resolved_environment

LOGGER = "stash.hermes_adapter.host"


def test_a_secret_is_read_from_the_hermes_secret_scope() -> None:
    # Setup
    scope = StubSecretScope({"OPENROUTER_API_KEY": "sk-fake"})

    # Execute
    value = hermes_secret("OPENROUTER_API_KEY", scope.import_module)

    # Assert
    assert value == "sk-fake"


def test_the_secret_scope_module_is_imported_by_its_hermes_name() -> None:
    # Setup
    scope = StubSecretScope({})

    # Execute
    hermes_secret("OPENROUTER_API_KEY", scope.import_module)

    # Assert
    assert scope.imported == [SECRET_SCOPE_MODULE]


def test_a_secret_the_scope_does_not_know_is_none() -> None:
    # Setup
    scope = StubSecretScope({})

    # Execute
    value = hermes_secret("OPENROUTER_API_KEY", scope.import_module)

    # Assert
    assert value is None


def test_a_secret_is_none_when_hermes_is_not_importable() -> None:
    # Execute
    value = hermes_secret("OPENROUTER_API_KEY", importer_without_hermes)

    # Assert
    assert value is None


def test_a_secret_is_none_when_the_scope_raises() -> None:
    # Setup
    scope = StubSecretScope({"OPENROUTER_API_KEY": "sk-fake"}, failure=RuntimeError("unscoped"))

    # Execute
    value = hermes_secret("OPENROUTER_API_KEY", scope.import_module)

    # Assert
    assert value is None


def test_an_empty_secret_is_none() -> None:
    # Setup
    scope = StubSecretScope({"OPENROUTER_API_KEY": ""})

    # Execute
    value = hermes_secret("OPENROUTER_API_KEY", scope.import_module)

    # Assert
    assert value is None


def test_a_whitespace_only_secret_is_none() -> None:
    # Setup
    scope = StubSecretScope({"OPENROUTER_API_KEY": "  \n"})

    # Execute
    value = hermes_secret("OPENROUTER_API_KEY", scope.import_module)

    # Assert
    assert value is None


def test_a_secret_keeps_its_surrounding_whitespace_untouched() -> None:
    # Setup
    scope = StubSecretScope({"TELEGRAM_ALLOWED_USERS": " 42 "})

    # Execute
    value = hermes_secret("TELEGRAM_ALLOWED_USERS", scope.import_module)

    # Assert
    assert value == " 42 "


def test_the_scope_is_asked_for_the_requested_name() -> None:
    # Setup
    scope = StubSecretScope({})

    # Execute
    hermes_secret("TELEGRAM_ALLOWED_USERS", scope.import_module)

    # Assert
    assert scope.requested == ["TELEGRAM_ALLOWED_USERS"]


def test_only_the_requested_secrets_are_read() -> None:
    # Setup
    scope = StubSecretScope({"OPENROUTER_API_KEY": "sk-fake", "OTHER": "x"})

    # Execute
    resolved_environment(
        {}, lambda name: hermes_secret(name, scope.import_module), ("OPENROUTER_API_KEY",)
    )

    # Assert
    assert scope.requested == ["OPENROUTER_API_KEY"]


def test_a_scope_that_raises_is_logged_by_secret_name_and_exception_type_only() -> None:
    # Setup
    scope = StubSecretScope({}, failure=RuntimeError("sk-leaked-value"))

    # Execute
    with recording_logs(LOGGER) as logs:
        hermes_secret("OPENROUTER_API_KEY", scope.import_module)

    # Assert
    assert logs.entries() == [
        (logging.WARNING, "could not read Hermes secret OPENROUTER_API_KEY: RuntimeError")
    ]


def test_a_hermes_that_is_not_importable_is_logged_by_secret_name_and_exception_type() -> None:
    # Execute
    with recording_logs(LOGGER) as logs:
        hermes_secret("TELEGRAM_ALLOWED_USERS", importer_without_hermes)

    # Assert
    assert logs.entries() == [
        (logging.WARNING, "could not read Hermes secret TELEGRAM_ALLOWED_USERS: ImportError")
    ]


def test_a_secret_the_scope_does_not_know_logs_nothing() -> None:
    # Setup
    scope = StubSecretScope({})

    # Execute
    with recording_logs(LOGGER) as logs:
        hermes_secret("OPENROUTER_API_KEY", scope.import_module)

    # Assert
    assert logs.entries() == []


def test_a_blank_secret_logs_nothing() -> None:
    # Setup
    scope = StubSecretScope({"OPENROUTER_API_KEY": "  "})

    # Execute
    with recording_logs(LOGGER) as logs:
        hermes_secret("OPENROUTER_API_KEY", scope.import_module)

    # Assert
    assert logs.entries() == []
