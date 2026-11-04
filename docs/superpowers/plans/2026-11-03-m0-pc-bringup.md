# M0 PC Bring-up and Mac Handoff Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
> This is an operations plan, run on the PC by the owner and the assistant together.
> It is **not** the "current plan" for code (that is the newest `plan-N` file); the Mac
> keeps building from `plan-2`…`plan-6`. Steps marked **(owner)** need sudo, a Telegram
> account or a secret, which the assistant must not handle.

**Goal:** Run the M0 spike on the PC, record the Hermes go/no-go, pick the local model, and hand the results to the Mac so it can continue Plans 2–6.

**Architecture:** Nothing in `src/` changes except spike fixes. Results land in `docs/adr/` and `docs/superpowers/notes/`; the Mac receives them as a git branch it merges. The go/no-go (spike #1 and #6) is done first so a "no-go" is found before any other work.

**Tech Stack:** WSL2 Ubuntu, systemd, Ollama 0.33.2, Hermes (git checkout `b7736eca98`), python-telegram-bot 22.x (inside Hermes), `uv`, `stash` CLI.

**Spec:** `docs/superpowers/specs/2026-11-02-stash-design.md`; checks in `docs/spike-m0.md`; findings in `docs/superpowers/notes/2026-11-03-pc-setup-findings.md`.

## Global Constraints

- Real items never touch the Mac or this repo; spike messages use fake data. (`CLAUDE.md`)
- Hermes needs ≥ 64k context: `OLLAMA_CONTEXT_LENGTH=65536`; `ollama ps` must show `CONTEXT 65536`.
- Do not run `hermes update`. Record any Hermes commit change in `docs/adr/`.
- `make check` stays green; Python changes on the PC follow `CLAUDE.md` § "Writing Python" (PC row: no orchestrator here; test-first, reviewed by `branch-reviewer` before the Mac sees them).
- Secrets (`TELEGRAM_BOT_TOKEN`, `OPENROUTER_API_KEY`) live only in `~/.hermes/.env`, never in the repo.
- GPU: the LLM and Whisper never load at the same time.

## Review Focus

- Ollama still at 4096 context after a restart → Hermes truncates silently; `ollama ps` check in Task 1.
- Message from a Telegram account that is not the owner → no reply, nothing stored (spike #17).
- Message while Ollama is stopped → saved raw, "📥 Saved" reply (spike #6).
- Bot added to a group chat → decide ignore/allow (spike #16); default ignore.
- Hermes drift: tested commit differs from the one recorded in ADR 0001.

---

### Task 1: Server settings and PATH (owner)

**Files:** none in the repo; system `ollama.service.d/override.conf`; `~/.zshrc`.

**Interfaces:** Produces: Ollama serving 64k context; `deno` on PATH.

- [x] **Step 1 (owner):** `sudo systemctl edit ollama`, paste `deploy/systemd/ollama.override.conf`, then `sudo systemctl restart ollama`.
- [x] **Step 2:** Add `export PATH="$HOME/.deno/bin:$PATH"` to `~/.zshrc`; open a new shell.
- [x] **Step 3: Verify.** Send one chat request to `qwen3.5:latest`; run `ollama ps`. Expected: `CONTEXT 65536`, `100% GPU`. Run `stash doctor`. Expected: `✔ deno`, `✔ tesseract`, `✔ ollama`.

### Task 2: Candidate models

**Files:** `docs/adr/0004-local-model.md` (record sizes).

**Interfaces:** Produces: `gemma4:12b` (fits) and `qwen3:8b` (rejected: context cap 40960, CPU spill) pulled; results in ADR 0004.

- [x] **Step 1 (owner or assistant):** `ollama pull gemma4:12b` and `ollama pull qwen3:8b`.
- [x] **Step 2:** For each, request with `num_ctx=65536` and read `ollama ps`. Expected: fits fully on GPU. If `gemma4:12b` spills to CPU, mark it "does not fit 64k" in ADR 0004 and skip it in Task 6.

### Task 3: Telegram bot and Hermes gateway (owner)

**Files:** `~/.hermes/.env`, `~/.hermes/config.yaml` (merge `deploy/hermes/config.yaml.example`).

**Interfaces:** Produces: a running Hermes gateway that answers the owner's account only.

- [x] **Step 1 (owner):** Create the bot with @BotFather; get your numeric Telegram user id.
- [x] **Step 2 (owner):** `hermes gateway setup` → Telegram, paste token and user id, accept the systemd user unit.
- [x] **Step 3:** Merge the example config; keep the existing `model:` block unless it conflicts, and set Hermes' provider to local Ollama at the same model as `stash.toml`.
- [x] **Step 4: Verify.** Send "hello" from the owner account. Expected: a reply. From a second account: no reply.

### Task 4: Plugin install and the go/no-go checks

**Files:** `docs/adr/0001-hermes-gate.md`, `docs/spike-m0.md` (fix wrong expectations in place).

**Interfaces:** Consumes: Task 3 gateway. Produces: ADR 0001 with a Go or No-go decision.

- [x] **Step 1:** `ln -s ~/projects/stash/deploy/hermes-plugin/stash ~/.hermes/plugins/stash`; `hermes plugins validate ~/.hermes/plugins/stash`; `hermes plugins enable stash`; `hermes gateway restart`. Expected: `hermes plugins` lists stash enabled.
- [x] **Step 2: Check #6 first.** `sudo systemctl stop ollama`; send a fake message. Expected: the message is a pending capture (`status=pending`, no item; `stash list` will not show it) and the bot replies "📥 Saved — I'll file it once the AI is reachable." Then `sudo systemctl start ollama`.
- [x] **Step 3: Check #1.** Share a fake link; tap **Type**. Expected: type menu appears and the message edits.
- [x] **Step 4:** If both pass, write **Go** in ADR 0001 with the Hermes commit hash. If either fails, write **No-go** and stop this plan: the Mac replaces only `src/stash/hermes_adapter/` with a python-telegram-bot bot.

### Task 5: Remaining spike checks

**Files:** `docs/adr/0001-hermes-gate.md` (results table), `docs/usage.md` (command names from #15).

**Interfaces:** Consumes: Task 4 Go. Produces: observed result for each of the 18 checks.

- [ ] **Step 1:** Run checks #2, #3, #4, #7, #8, #13–#18 in order of `docs/spike-m0.md`. Record observed behaviour per check in ADR 0001, including the scheduler mechanism that works for #2 (Plan 3 Task 6 depends on it).
- [ ] **Step 2:** Run #9 (YouTube, Instagram, article, and `http://localhost:11434/` which must never be fetched). Needs deno on PATH.
- [ ] **Step 3:** Update `docs/usage.md` with the real names of `/list`, `/gpu`, `/retry` (#15).

### Task 6: Model eval and OpenRouter

**Files:** `docs/adr/0004-local-model.md`, `docs/adr/0003-ocr-optional.md`, `~/.config/stash/stash.toml`.

**Interfaces:** Consumes: Task 2 models. Produces: chosen model; OCR keep/drop decision.

- [ ] **Step 1:** For each fitting model set `[llm.ollama] model` and run `stash eval --providers ollama --arms text,vision,ocr` (fake cases only). Record score and latency.
- [ ] **Step 2 (owner):** Create an OpenRouter key; put it in `~/.hermes/.env` and the environment stash runs in. Pick a real model id (one `:free`, one cheap paid) and set `[llm.openrouter] model`. Run `stash doctor`. Expected: `✔ openrouter model`. (spike #11, #10)
- [ ] **Step 3:** Run the eval with `--providers ollama,openrouter`. Expected: no HTTP 400 on `response_format` (#10).
- [ ] **Step 4:** Fill ADR 0004 with the winner. Fill ADR 0003: keep the OCR extra only if the OCR arm clearly beats vision; otherwise mark it "dropped" and tell the Mac to remove the extra.

### Task 7: NAS backups (can wait)

**Files:** `/etc/fstab`, `~/.config/systemd/user/stash-backup.{service,timer}`.

- [ ] **Step 1 (owner):** Follow `wsl-setup.md` section 9. Verify: `systemctl --user start stash-backup.service` writes `stash-YYYYMMDD.db` on the NAS.

### Task 8: Hand the results to the Mac

**Files:** commit on a branch `pc-m0`.

**Interfaces:** Produces: branch `pc-m0` on the Mac's repo containing ADRs, notes, doc fixes, the `ocr` extra and its test. `uv.lock` is **excluded**.

- [x] **Step 1:** `git switch -c pc-m0`; run `make check` with the local `uv.lock` in place. Expected: green. Keep `uv.lock` in the working tree but never `git add` it, because it only works on this PC. `pyproject.toml` changes (the `ocr` extra) do need the Mac to re-lock.
- [x] **Step 2:** Commit in small commits (ADRs and notes, ocr extra with test, doc fixes), each staged by explicit path so `uv.lock` stays out. Verify with `git show --stat HEAD` per commit.
- [ ] **Step 3 (owner approves):** `git push origin pc-m0`. This creates a branch on the Mac's repo; it does not touch `main`.
- [ ] **Step 4 (Mac):** merge `pc-m0` into `main`, regenerate `uv.lock` with `uv lock --default-index https://pypi.org/simple` (confirm the Mac can reach public PyPI), run `make check`, then start Plan 2 (Plan 3 once ADR 0001 records the scheduler mechanism; Plan 5 once the eval is done).

### Follow-ups from the branch review (for the Mac, not done here)
- `make_ocr` falls back to `NoOcr` silently; log a warning, or have `stash doctor` mention the `ocr` extra (a present binary with a missing extra shows ✔ tesseract but every OCR-arm case fails).
- `tests/unit/app/test_ocr.py` and `test_build_app.py` import `TesseractOcr` at module level and `tests/integration/test_tesseract_ocr.py` has no `importorskip`; without the extra they fail at collection.
- `plugin.py` ignores the result of registering the `stash-<name>` alias; check it and log the name the user types.
- `docs/usage.md` (OCR arm) should say the arm needs the `ocr` extra.
- Add a per-task thinking setting for filing (ADR 0004) and have `stash eval` score it.

---

## Self-review notes
- Spec coverage: M0 spike items (#1–#18), gate, model choice, NAS backup, and the Mac handoff each have a task. The "pin Hermes" decision from the spec's builder list is covered by Task 4 Step 4.
- Open owner decision: let the Mac start Plan 2 now, in parallel with Tasks 1–5. Plan 2's code sits in the Hermes-free core (a no-go replaces only `hermes_adapter/`), but any Plan 2 task that adds Telegram buttons touches the adapter and should wait for Task 4.
