# stash

Personal Telegram organizer: a Hermes Agent plugin over a Hermes-free core.
The **spec** (`docs/superpowers/specs/2026-11-02-stash-design.md`) is the
source of truth for behaviour; the current **plan** is the newest `plan-N` file in
`docs/superpowers/plans/` (other files there, like the M0 PC bring-up ops plan, are not code plans). Read both before changing behaviour.

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

## Writing Python

Who writes it depends on the machine. **Check what is installed; do not assume.**

| Machine | Python source is written by | Review |
|---|---|---|
| **Mac** (main development) | The `python-development:python-coding-orchestrator` agent (owner's global rule): one orchestrator per task group, the main loop commits. Docs, TOML/YAML, SQL and this file may be written by the main loop. | Plan's own review step |
| **PC / WSL** (live-service work, spike fixes) | That plugin is **not installed here**. Use `superpowers:subagent-driven-development` with the `general-purpose` agent as implementer and `superpowers:test-driven-development` for every task. Small spike fixes may be done inline only if they are test-first and listed in the commit message. | `branch-reviewer` agent on the branch before it goes to the Mac; `/simplify` and `/code-review` as needed |

If the orchestrator plugin becomes available on a machine, use it there. Either way:
the gate is `make check`, one task per commit, and work from the plan file.

Conventions (matched to the existing code; follow them, the architecture tests enforce
the layering):

- **Tooling:** `ruff` (rules `E F I UP B SIM RUF`, line length 100), `mypy --strict` on
  `src` and `tests/fakes`, Python ≥ 3.11, dependencies via `uv`. `# type: ignore` and
  `noqa` are not used in `src` (a few test helpers have them); fix the typing instead.
- **Values:** all dataclasses are `frozen=True, slots=True`; closed sets are `StrEnum`;
  ports are `Protocol`s in the feature package; validation happens at the boundary
  (`stash.domain._validation`), not scattered.
- **Names, not numbers:** magic values become `UPPER_SNAKE` module constants.
- **Comments and docstrings:** almost none. Code is named so it reads on its own. A comment
  is for an unverified assumption about a live service (state what must be checked) or a
  non-obvious "why".
- **Tests:** offline always (fakes, `httpx.MockTransport`). Test names are sentences
  describing behaviour; bodies use `# Setup` / `# Execute` / `# Assert`. Shared helpers
  are builders, rigs and fakes at the root of `tests/` (not per-test copies). Integration
  tests are marked `integration` and still need no network.
- **Optional dependencies** (`ocr` now; `transcribe` is planned in Plan 5) import lazily, inside the factory that
  needs them, and fall back cleanly when absent (see `stash.app.ocr`).
- **Fake data only**, including examples and eval cases.

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
  pinned v0.22.6 (the PC tested b7736eca98, 412 commits later; ADR 0001); the PyPI `hermes-agent` (0.19) is stale — never depend on it.
