import ast

from architecture_guard import forbidden_imports_in, imports_outside_allowed, sources_named

ACCESS = "stash.library_access"
SERVER = "stash.library_server"
DISK_ACCESS = ("pathlib", "os", "shutil", "glob")
SERVING_MACHINERY = ("http", "socket", "socketserver", "logging")
PROBE = "stash.library_server_probe"
FILE_SERVING_HANDLER = "http.server.SimpleHTTPRequestHandler"
LAYERS_ABOVE = ("stash.app", "stash.cli", "stash.rendering", "stash.library_html")
TOKEN_COMPARISON = "compare_digest"


def test_neither_library_server_module_imports_a_disk_access_module() -> None:
    # Execute
    offenders = forbidden_imports_in(sources_named(ACCESS, SERVER), DISK_ACCESS)

    # Assert
    assert offenders == []


def test_neither_library_server_module_imports_the_file_serving_request_handler() -> None:
    # Execute
    offenders = forbidden_imports_in(sources_named(ACCESS, SERVER), (FILE_SERVING_HANDLER,))

    # Assert
    assert offenders == []


def test_no_library_server_module_imports_a_layer_above_the_adapters() -> None:
    # Execute
    offenders = forbidden_imports_in(sources_named(ACCESS, SERVER, PROBE), LAYERS_ABOVE)

    # Assert
    assert offenders == []


def test_the_access_module_imports_only_the_standard_library_and_no_serving_machinery() -> None:
    # Execute
    offenders = forbidden_imports_in(sources_named(ACCESS), SERVING_MACHINERY)
    outsiders = imports_outside_allowed(sources_named(ACCESS), ())

    # Assert
    assert (offenders, outsiders) == ([], [])


def test_the_access_module_compares_tokens_with_compare_digest() -> None:
    # Setup
    tree = ast.parse(sources_named(ACCESS)[ACCESS])

    # Execute
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == TOKEN_COMPARISON
    ]

    # Assert
    assert len(calls) == 1
