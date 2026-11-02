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
| 6 | Does stash see every message **before** the LLM? | Stop Ollama (`sudo systemctl stop ollama`), send a message. | `stash list --stage inbox` shows it; the bot answers "📥 Saved — I'll file it once the AI is reachable." |
| 7 | Does `inject_message` hand questions to the agent? | Ask "what can I do Saturday?" | The agent answers using `stash_search`/`stash_list`. |
| 8 | Is the tool scope locked down? | Ask the bot to run a shell command. | It refuses / has no terminal tool. |

## Go / no-go

**Go (keep Hermes)** only if **#1** (buttons + callbacks) and **#6** (raw save
before the LLM) both pass.

**No-go:** switch to the custom bot (python-telegram-bot + stash's own
LLM client and scheduler). Only `src/stash/hermes_adapter/` is replaced; the
core is unchanged. Gmail later uses the Google API directly.

#7 failing is not a no-go: route synchronously inside the hook instead (await
the filer, then return `allow` for questions so Hermes runs a normal agent turn).
