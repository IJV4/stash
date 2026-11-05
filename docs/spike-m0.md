# M0 spike — verify Hermes before building on it

Run on the PC after `docs/deploy/wsl-setup.md`. For each point, do the check,
write what you observed, and record the outcome in `docs/adr/0001-hermes-gate.md`.
Facts below come from the Hermes source at commit 43a35e8 (v0.22.6 era); the
spike confirms they behave that way at runtime.

| # | Question | How to check | Expected |
|---|----------|--------------|----------|
| 1 | Can a plugin send inline buttons and receive their presses? | Share a link; tap **Type** on the confirmation. | Type menu appears; choosing one edits the message. Telegram's own Hermes buttons (e.g. approvals) still work. |
| 2 | Can scheduled code run without an agent turn? | `hermes cron create "every 5m" --no-agent --script stash_tick.py --deliver telegram` with a script that prints a line (script must be in `$HERMES_HOME/scripts/`). Also try `ctx.spawn_task` from the plugin. | The line arrives in Telegram without an LLM call (check `ollama ps` stays idle). Note which mechanism works; Plan 3 uses it. |
| 3 | How do Android shares arrive? | Share from Instagram, YouTube and Chrome to the bot. | Plain message text containing the URL (plus caption, sometimes). |
| 4 | What transcribes voice notes? | Send a voice note; check Hermes logs/config. | Note the backend; decide if faster-whisper can be shared in Plan 5. |
| 5 | Which local model is good enough? | `stash eval --providers ollama[,openrouter]` per candidate model. | A model with acceptable scores and latency within 12 GB VRAM at 64k context. |
| 6 | Does stash see every message **before** the LLM? | Stop Ollama (`sudo systemctl stop ollama`), send a message. | The message is stored as a **pending capture** (no item yet; `stash list` will not show it) and the bot answers "📥 Saved — I'll file it once the AI is reachable." |
| 7 | Does `inject_message` hand questions to the agent? | Ask "what can I do Saturday?" | The agent answers using `stash_search`/`stash_list`. |
| 8 | Is the tool scope locked down? | Ask the bot to run a shell command. | It refuses / has no terminal tool. |
| 9 | Do the real link inspectors work? (the suite only fakes yt-dlp and the page fetch) | Share a YouTube link, an Instagram link and a plain article; check the confirmation detail and the item note. | YouTube gets title/uploader/duration via yt-dlp; Instagram falls back to the page title or nothing (the note covers it); articles get their `<title>`. A link to `http://localhost:11434/` is never fetched. |
| 10 | Do both providers accept the filing schema? (`details` is an object of strings) | `stash eval` text arm against Ollama and OpenRouter. | No HTTP 400 on `response_format`; if a strict provider rejects `additionalProperties` on `details`, change `details` to a list of key/value pairs in `stash.filing.schema` and `parse_filing`. |
| 11 | Does `stash doctor` read OpenRouter's model list correctly? (assumed `GET /api/v1/models` → `{"data":[{"id": …}]}`) | With `OPENROUTER_API_KEY` set, run `stash doctor`. | `✔ openrouter model — …`. If it fails although the model exists, fix the parser in `stash.llm.probes`. |
| 12 | Does real OCR work? (tesseract was absent on the dev Mac; its test skipped) | `stash eval --arms ocr --providers ollama`. | The three fake PNGs produce readable text; image cases score on the OCR arm. |
| 13 | Do hook results behave as assumed? | Send a plain message, then `/list`. | Plain message: no agent turn (`skip`), item saved. `/list`: handled by stash's command (`allow`). If the hook ever errors, the adapter fails open (message reaches Hermes unsaved) — check logs. |
| 14 | Does a handed-off question loop back? (`inject_message` with `origin`) | Ask a question; watch `stash list --stage inbox` and the logs. | One agent answer in the same chat; the injected text is **not** captured as a new item (`event.internal` is True or the hook doesn't fire). |
| 15 | Which command names registered? | Look at the Telegram command menu. | `/list` and `/gpu` under their own names; `/retry` probably clashes with a Hermes built-in and appears as `/stash_retry`. Update `docs/usage.md` to match. **Observed 2026-11-04:** the gateway looks plugin commands up as `name.replace("_", "-")`, so the alias must be *registered* as `stash-retry` (typed as `/stash_retry`); registering it with an underscore gave "unknown command". |
| 16 | Group chats? (platform/chat_type are not checked) | Add the bot to a group, send a message as the owner. | Decide: ignore groups (add a guard in `hermes_adapter/events.py`) or allow. Default expectation: ignore. |
| 17 | Secrets and allowed users resolve? | `stash doctor`; send a message from another Telegram account. | `OPENROUTER_API_KEY` / `TELEGRAM_ALLOWED_USERS` resolve via `agent.secret_scope` or env; strangers get no reply and nothing is stored. Empty owner list ⇒ stash ignores everyone and logs one warning. |
| 18 | Hermes' pinned python-telegram-bot matches? (tests bind to PTB 22.8) | `~/.hermes/hermes-agent` Python: `python -c "import telegram; print(telegram.__version__)"`. | 22.x; if not, re-run the adapter's PTB contract tests against that version. |
| 19 | Does thinking off keep filing quality? (ADR 0004) | `stash eval --providers ollama --thinking default,off` for the chosen model. | Compare the two columns' scores and p50 latency; read `t10` and `i02` in the `### cases` sections. Record the result and the chosen `filing` default in ADR 0004. Re-run whenever the model changes. |
| 20 | Does OpenRouter accept its off field? (`"reasoning": {"effort": "none"}`, schema only) | Per candidate model: `stash eval --providers openrouter --arms text --thinking default,off`; compare reasoning tokens on the OpenRouter activity page. | No HTTP 400 on the off run, and reasoning tokens drop. Record per model in ADR 0004. |
| 21 | What does a model without thinking do with the off field? | Pick a non-thinking model (e.g. `gemma4:12b`), set `[llm.thinking] filing = "off"`, then share a message and run `stash eval --providers ollama --thinking off`. | The field is accepted or ignored, with no error. If it errors, keep `filing` at `default` for that model. |
| 22 | Is the PC's SQLite new enough? (the store's queries use window functions, SQLite ≥ 3.25) | In stash's venv: `python3 -c "import sqlite3; print(sqlite3.sqlite_version)"`. | 3.25 or later. If older, the library and done-between queries (`LIBRARY`, `DONE_BETWEEN` in `stash.store._sql`) fail; use a Python built with a newer SQLite. |

## Go / no-go

**Go (keep Hermes)** only if **#1** (buttons + callbacks) and **#6** (raw save
before the LLM) both pass.

**No-go:** switch to the custom bot (python-telegram-bot + stash's own
LLM client and scheduler). Only `src/stash/hermes_adapter/` is replaced; the
core is unchanged. Gmail later uses the Google API directly.

#7 failing is not a no-go: route synchronously inside the hook instead (await
the filer, then return `allow` for questions so Hermes runs a normal agent turn).
