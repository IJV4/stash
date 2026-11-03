from collections.abc import Iterable

from stash.domain._validation import frozen_strings, require_safe_media_path


def safe_media_paths(name: str, paths: Iterable[str]) -> tuple[str, ...]:
    frozen = frozen_strings(name, paths)
    for path in frozen:
        require_safe_media_path(path)
    return frozen
