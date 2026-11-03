import ast
import sys
from functools import cache
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1] / "src"
ADAPTER_MODULES = (
    "stash.store.sqlite",
    "stash.store.backup",
    "stash.http_client",
    "stash.llm.openai_compat",
    "stash.llm.probes",
    "stash.gpu.probe",
    "stash.enrich.ytdlp",
    "stash.enrich.html_meta",
    "stash.evaluation.tesseract",
)
HERMES_MODULES = (
    "gateway",
    "hermes_cli",
    "hermes_constants",
    "agent",
    "plugins",
    "tools",
    "hermes",
)
TELEGRAM = "telegram"


def module_name(path: Path) -> str:
    parts = list(path.relative_to(SOURCE_ROOT).with_suffix("").parts)
    return ".".join(parts[:-1] if parts[-1] == "__init__" else parts)


@cache
def imported_modules(source: str) -> frozenset[str]:
    imported: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                raise ValueError("relative imports are not supported by the architecture guard")
            base = node.module or ""
            imported.update([base, *(f"{base}.{alias.name}" for alias in node.names)])
    return frozenset(imported)


@cache
def _read_sources(relative: tuple[str, ...]) -> tuple[tuple[str, str], ...]:
    paths = sorted(SOURCE_ROOT.joinpath("stash", *relative).rglob("*.py"))
    if not paths:
        raise ValueError(f"no source files found under {relative or 'stash'}")
    return tuple((module_name(path), path.read_text(encoding="utf-8")) for path in paths)


def project_sources(*relative: str) -> dict[str, str]:
    return dict(_read_sources(relative))


def is_within(module: str, package: str) -> bool:
    return module == package or module.startswith(f"{package}.")


def is_storage_free(module: str) -> bool:
    if is_within(module, "sqlite3"):
        return False
    return module.split(".")[0] in sys.stdlib_module_names or is_within(module, "stash.domain")


def storage_dependencies_in(sources: dict[str, str]) -> list[str]:
    return sorted(
        f"{name} -> {module}"
        for name, source in sources.items()
        for module in imported_modules(source)
        if not is_storage_free(module)
    )


def importers_outside(target: str, allowed: tuple[str, ...], sources: dict[str, str]) -> list[str]:
    return [
        name
        for name, source in sources.items()
        if any(is_within(module, target) for module in imported_modules(source))
        and not any(is_within(name, root) for root in allowed)
    ]


def forbidden_imports_in(sources: dict[str, str], forbidden: tuple[str, ...]) -> list[str]:
    return sorted(
        f"{name} -> {banned}"
        for name, source in sources.items()
        for banned in forbidden
        if any(is_within(module, banned) for module in imported_modules(source))
    )


def sources_named(*modules: str) -> dict[str, str]:
    everything = project_sources()
    missing = [module for module in modules if module not in everything]
    if missing:
        raise ValueError(f"no source found for modules {missing}")
    return {module: everything[module] for module in modules}


def _names_imported_by(node: ast.AST) -> list[str]:
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    if isinstance(node, ast.ImportFrom):
        if node.level:
            raise ValueError("relative imports are not supported by the architecture guard")
        base = node.module or ""
        return [base, *(f"{base}.{alias.name}" for alias in node.names)]
    return []


def _is_type_checking_guard(node: ast.If) -> bool:
    test = node.test
    return (isinstance(test, ast.Name) and test.id == "TYPE_CHECKING") or (
        isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING"
    )


def _module_level_imports(source: str, *, skip_type_checking: bool) -> frozenset[str]:
    imported: set[str] = set()
    pending: list[ast.AST] = list(ast.iter_child_nodes(ast.parse(source)))
    while pending:
        node = pending.pop()
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda):
            continue
        if skip_type_checking and isinstance(node, ast.If) and _is_type_checking_guard(node):
            pending.extend(node.orelse)
            continue
        imported.update(_names_imported_by(node))
        pending.extend(ast.iter_child_nodes(node))
    return frozenset(imported)


def module_level_imports(source: str) -> frozenset[str]:
    return _module_level_imports(source, skip_type_checking=False)


def runtime_module_level_imports(source: str) -> frozenset[str]:
    return _module_level_imports(source, skip_type_checking=True)


def runtime_import_offenders(sources: dict[str, str], banned: tuple[str, ...]) -> list[str]:
    return sorted(
        f"{name} -> {package}"
        for name, source in sources.items()
        for package in banned
        if any(is_within(module, package) for module in runtime_module_level_imports(source))
    )


def line_count(source: str) -> int:
    return len(source.splitlines())
