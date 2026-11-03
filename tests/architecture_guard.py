import ast
import sys
from functools import cache
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1] / "src"
ADAPTER_MODULES = (
    "stash.store.sqlite",
    "stash.http_client",
    "stash.llm.openai_compat",
    "stash.llm.probes",
    "stash.gpu.probe",
    "stash.enrich.ytdlp",
    "stash.enrich.html_meta",
)


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
