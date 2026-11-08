import pytest
from architecture_guard import (
    HERMES_MODULES,
    TELEGRAM,
    forbidden_imports_in,
    importers_outside,
    project_sources,
    runtime_import_offenders,
    runtime_module_level_imports,
)

HERMES_ADAPTER = "stash.hermes_adapter"
LAZY_TELEGRAM_IMPORT = "def attach():\n    from telegram.ext import CallbackQueryHandler\n"


def test_a_plain_module_level_import_is_a_runtime_import() -> None:
    # Execute
    imported = runtime_module_level_imports("import telegram")

    # Assert
    assert TELEGRAM in imported


def test_an_import_under_a_type_checking_guard_is_not_a_runtime_import() -> None:
    # Setup
    source = "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    import telegram\n"

    # Execute
    imported = runtime_module_level_imports(source)

    # Assert
    assert TELEGRAM not in imported


def test_an_import_under_a_qualified_type_checking_guard_is_not_a_runtime_import() -> None:
    # Setup
    source = "import typing\nif typing.TYPE_CHECKING:\n    import telegram\n"

    # Execute
    imported = runtime_module_level_imports(source)

    # Assert
    assert TELEGRAM not in imported


def test_an_import_in_the_else_branch_of_a_type_checking_guard_is_a_runtime_import() -> None:
    # Setup
    source = "if TYPE_CHECKING:\n    pass\nelse:\n    import telegram\n"

    # Execute
    imported = runtime_module_level_imports(source)

    # Assert
    assert TELEGRAM in imported


def test_an_import_under_another_module_level_condition_is_a_runtime_import() -> None:
    # Setup
    source = "if SOMETHING_ELSE:\n    import telegram\n"

    # Execute
    imported = runtime_module_level_imports(source)

    # Assert
    assert TELEGRAM in imported


def test_an_import_inside_a_function_is_not_a_runtime_module_level_import() -> None:
    # Execute
    imported = runtime_module_level_imports(LAZY_TELEGRAM_IMPORT)

    # Assert
    assert imported == frozenset()


def test_the_hermes_adapter_importing_a_hermes_module_is_not_an_outside_importer() -> None:
    # Setup
    sources = {"stash.hermes_adapter.host": "def secret():\n    import agent\n"}

    # Execute
    offenders = importers_outside("agent", (HERMES_ADAPTER,), sources)

    # Assert
    assert offenders == []


def test_a_hermes_module_reached_through_importlib_is_not_a_static_import() -> None:
    # Setup
    source = 'import importlib\nimportlib.import_module("agent.secret_scope")\n'
    sources = {"stash.hermes_adapter.host": source}

    # Execute
    offenders = forbidden_imports_in(sources, HERMES_MODULES)

    # Assert
    assert offenders == []


def test_the_hermes_adapter_importing_telegram_is_not_an_outside_importer() -> None:
    # Setup
    sources = {"stash.hermes_adapter.telegram_io": LAZY_TELEGRAM_IMPORT}

    # Execute
    offenders = importers_outside(TELEGRAM, (HERMES_ADAPTER,), sources)

    # Assert
    assert offenders == []


def test_a_module_named_like_telegram_but_inside_stash_is_not_the_telegram_package() -> None:
    # Setup
    sources = {"stash.hermes_adapter.fine": "from stash.hermes_adapter import telegram_io"}

    # Execute
    offenders = importers_outside(TELEGRAM, (), sources)

    # Assert
    assert offenders == []


@pytest.mark.parametrize("module", HERMES_MODULES)
def test_no_module_outside_the_hermes_adapter_imports_a_hermes_module(module: str) -> None:
    # Execute
    offenders = importers_outside(module, (HERMES_ADAPTER,), project_sources())

    # Assert
    assert offenders == []


def test_no_module_of_the_hermes_adapter_imports_a_hermes_module_statically() -> None:
    # Execute
    offenders = forbidden_imports_in(project_sources("hermes_adapter"), HERMES_MODULES)

    # Assert
    assert offenders == []


def test_no_module_of_the_hermes_adapter_imports_telegram_at_runtime_module_level() -> None:
    # Execute
    offenders = runtime_import_offenders(project_sources("hermes_adapter"), (TELEGRAM,))

    # Assert
    assert offenders == []


def test_telegram_is_imported_nowhere_outside_the_hermes_adapter() -> None:
    # Execute
    offenders = importers_outside(TELEGRAM, (HERMES_ADAPTER,), project_sources())

    # Assert
    assert offenders == []
