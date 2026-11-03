# stash

A personal organizer for things I want to do: capture a link or a thought in
two taps, have an LLM file it, and get nudged to act on it.

The design lives in `docs/superpowers/specs/2026-11-02-stash-design.md`; how it
behaves from the owner's side is in `docs/usage.md`.

## Development

    make install   # uv sync
    make check     # ruff format --check, ruff check, mypy --strict src, pytest

Only fake data belongs in this repo; the test suite never touches the network.
