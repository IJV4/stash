# 0002 — Python as the implementation language

**Status:** Accepted (2026-11-03)

## Context
stash must run as a Hermes plugin, call Ollama/OpenRouter, read link metadata, and later
transcribe audio. It is a single-user tool on a WSL2 box; the bottleneck is the LLM and
network, not CPU. Deployment is `uv sync` in WSL. The owner maintains Python.

## Options
| Option | For | Against |
|---|---|---|
| **Python 3.11+** | Hermes plugins are Python (the adapter loads in-process); `yt-dlp`, `faster-whisper`, `python-telegram-bot` are native Python; `mypy --strict` gives static checks | Weaker types than a compiled language; a runtime to manage |
| TypeScript (Node/Bun) | Good types; strong Telegram libraries | Cannot be an in-process Hermes plugin; would shell out to `yt-dlp` and Whisper |
| Go | Single binary, fast | Same plugin and ecosystem gaps; more code for LLM/schema work; nothing here needs the speed |

## Decision
Python (`requires-python >=3.11`), dependencies via `uv`, with `ruff` and
`mypy --strict` inside `make check`.

## Consequences
- The Hermes-free core stays language-agnostic in design, but rewriting it elsewhere
  would lose the plugin integration and the media tooling; revisit only if the M0 gate
  fails and the custom bot replaces Hermes.
- Static checking depends on discipline at the boundaries (untyped `yt_dlp` is
  overridden in `pyproject.toml`).
