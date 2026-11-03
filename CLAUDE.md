# stash

Personal Telegram organizer: a Hermes Agent plugin over a Hermes-free core.
The **spec** (`docs/superpowers/specs/2026-11-02-stash-design.md`) is the
source of truth for behaviour; the current **plan** is the newest file in
`docs/superpowers/plans/`. Read both before changing behaviour.

## Gate

`make check` is the only gate (format, lint, `mypy --strict src tests/fakes`,
default tests, then `-m integration`). Green before every commit.

## Where code runs

- Written and unit-tested on an Apple-managed Mac whose sandbox blocks
  Telegram, Ollama and OpenRouter: the suite is **offline** (fakes,
  `httpx.MockTransport`), always.
- Runs on the owner's Windows PC in WSL2 (`docs/deploy/wsl-setup.md`). Anything
  needing a live service is verified there via `docs/spike-m0.md`.
- **Fake data only** in this repo — tests, evals, examples. The owner's real
  items never touch this machine.

## Architecture

- Layers: `stash.domain` (shared kernel) → ports (`stash.store.port`, …) →
  adapters → features → `stash.rendering` → `stash.app` (sole composition root) → entry points
  (`stash.cli`, `stash.hermes_adapter`). `tests/unit/test_architecture.py`
  enforces that only `stash.app` imports adapters.
- `stash.hermes_adapter` is the only Hermes-aware package; it imports Hermes
  lazily. If the M0 go/no-go fails, only it is replaced.
- Every incoming message is saved raw **before** any AI step. A capture must
  exist before `save_item` (FK; `UnknownCaptureError`).

## Gotchas

- Ollama `/v1` ignores `tool_choice` and cannot set context length: stash's own
  LLM calls use `response_format` JSON schema; 64k context is the server env
  `OLLAMA_CONTEXT_LENGTH`.
- OpenRouter can return `{"error": …}` with HTTP 200 — treat as failure.
- SQLite: set `journal_mode=WAL` before any transaction.
- Telegram `callback_data` ≤ 64 bytes; message text ≤ 4096 chars.
- LLM output and link metadata are untrusted: validate and clamp at the boundary.
- Hermes facts (plugin API, hooks, buttons, cron) are from source @ 43a35e8,
  pinned v0.22.6; the PyPI `hermes-agent` (0.19) is stale — never depend on it.
