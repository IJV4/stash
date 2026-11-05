# 0001 — Keep Hermes as the Telegram host (M0 go/no-go)

**Status:** **Go (keep Hermes)** — gate checks #1 and #6 passed on 2026-11-04. Remaining spike checks are still open (below); they do not change this decision.

## Context
stash is a Hermes Agent plugin over a Hermes-free core (spec: "Approach 1"). The
alternative is a custom bot on python-telegram-bot with stash's own LLM client and
scheduler (spec: "Approach 2"). Only `src/stash/hermes_adapter/` differs between them.

## Gate
- **Go (keep Hermes)** only if spike #1 (inline buttons and callbacks) and #6 (raw save
  before the LLM) both pass.
- **No-go:** switch to the custom bot. #7 failing alone is not a no-go.

## Spike results
Hermes `b7736eca98`, gateway in polling mode, local `qwen3.5:latest` at 64k, test messages (one public web-page link).

| # | Result | Evidence |
|---|---|---|
| 1 | **Pass (gate)** | Shared a link; the confirmation had a **Type** button; the menu opened and, per the owner, choosing "Plans" changed the message. DB confirms `item_type=plan`. **Not tested:** that Hermes's own buttons (e.g. approvals) still work. |
| 2 | **Pass (mechanism: Hermes cron `--no-agent`)** | `hermes cron create "every 2m" --no-agent --script stash_tick.py --deliver telegram:<owner id> --repeat 2`; script in `~/.hermes/scripts/`. The printed line arrived in Telegram at 13:04:41 as a "Cronjob Response" (Hermes adds a header and a "send me a message to stop this job" footer). Ollama got 0 requests during the run and the model stayed unloaded; `hermes cron runs` shows `completed`. The script (`~/.hermes/scripts/stash_tick.py`, not in the repo) only printed `stash spike #2: scheduled script ran at HH:MM:SS - no agent turn`. `ctx.spawn_task` from the plugin was **not** tested (not needed). Plan 3 Task 6 can use this mechanism. `--deliver telegram` alone needs a home channel (none set), so use `telegram:<chat id>`. |
| 2b | **Pass (in-process ticker is viable)** | A throwaway plugin's `telegram` handler factory ran inside a live event loop (`_UnixSelectorEventLoop`); `ctx.spawn_task` started a supervised task that ran 5 heartbeats ~20 s apart (14:48:24-14:49:48) without being cancelled. This went through Hermes's late-load re-wire path, not the first `connect()`, but it is the same call site (`gateway/platforms/base.py:_wire_plugin_handlers`, called from the async `connect()`). **Hermes re-runs a factory whenever the native Telegram client is rebuilt (reconnect)**, so a ticker started from the factory needs a once-only guard or it will be duplicated. Not tested live: a real reconnect. |
| 2c | **Pass** | Cron `--no-agent` job whose script prints nothing: Hermes logged `empty stdout - silent run ... skipping delivery`; no message reached Telegram; both runs `completed`. So a `stash tick` cron fallback that prints nothing when nothing is due is silent (no per-minute spam). |
| 6 | **Pass (gate)** | Ollama stopped; message saved as a pending capture (`status=pending`, no item), gateway log shows `pre_gateway_dispatch skip`, bot replied "saved", log `deferred: ai_unavailable`. After restart, `/stash_retry` filed it (`media / want_to`). |
| 10 | Ollama half **passes** | 22 text cases through the filing schema (`response_format`) against local Ollama: 0 errors, no HTTP 400. OpenRouter half not run (needs a key). |
| 12 | **Pass** | Tesseract 5.3.4 read all three fake PNGs correctly; the eval OCR arm ran on all three (2 scored fine, 1 errored after OCR; see ADR 0004). |
| 7 | **Fail (as the spec anticipated; not a no-go)** | Asked "What can I do this Saturday?": stash saved the raw capture (`status=request`, so raw-first held) and classified it as a request, but the handoff failed and the bot replied "I couldn't pass that on to the assistant." Gateway log: `Plugin message injection refused: plugin=stash origin=telegram/… has no human message admitted yet; a plugin can continue a chat, not open one`. Cause: `MessageIntake.on_dispatch` returns `SKIP` for every message, so Hermes never admits the human message, and `inject_message` can only *continue* a chat. The hook's verdicts are `skip`, `allow` and `rewrite` (`gateway/run_inbound_hooks.py`). Fix (spec fallback): decide inside the hook, i.e. save raw, classify, return `ALLOW` for requests so Hermes runs a normal agent turn, `SKIP` for captures. See the Mac handoff note. |
| 14 | Blocked by #7 | Cannot be tested until questions reach the agent. |
| – | **Finding: stash breaks after a plugin hot-reload** | Enabling then disabling an unrelated plugin made Hermes hot-reload plugins and re-run stash's `register()`. The new copy handled messages (hook replaced; message saved and filed) but its `LateBoundOutbox` stayed unbound: Hermes's late-wire step skipped stash's Telegram handler factory because factories are keyed by `(plugin, qualname)` and the new lambda has the same qualname as the old one. Result: `OutboxUnavailable: the Telegram connection is not up yet`, no replies, and (probably) dead buttons, until the gateway was restarted. Log: re-registrations at 14:48:24/25/40 and 15:12:49/50; the failed send at 15:45:13. Caused by the spike's own probe, but any `hermes plugins enable/disable` while the gateway runs can trigger it. |
| 13 | Pass (plain-message half) | Plain message: the Hermes gateway log shows `pre_gateway_dispatch skip` (stash itself does not log the verdict), no agent turn, item saved. `/list` → allow and the fail-open case are not yet checked. |
| 9 | **Pass, with one gap** | Four link kinds through the live bot (fake/public links only). **Instagram post:** filed `media / want_to`; title, uploader and hashtags captured. **YouTube video:** filed `media / want_to` with the real video title and tags from yt-dlp (also confirmed directly: uploader and duration are available with and without deno on PATH), but the item's `details` held only `{"platform": "youtube"}`. **Article:** `learn / want_to`, title from the page `<title>`. **`http://localhost:11434/`:** log line `page fetch skipped a non-public link: host localhost`; item titled from the URL; Ollama's log shows no `GET /` (only stash's own `/api/ps` and `/api/tags` probes). **Gap:** stash passes uploader and duration to the model, but `details` is whatever the model writes, so they are not stored reliably (Instagram happened to include the uploader). Store link metadata deterministically. Filing latency for links: 62-82 s with thinking on. |
| 15 | Resolved, with a bug fixed | Hermes refuses `/retry` (built-in). The alias was registered as `stash_retry`, but the gateway looks plugin commands up as `name.replace("_", "-")`, so Telegram's `/stash_retry` was "unknown command". Fixed by registering `stash-retry` (typed `/stash_retry`); test-first, `make check` green. `set_my_commands` succeeded with the hyphenated alias (60 commands; Hermes hides 66 more over Telegram's 60-command limit, so whether stash's commands are in the visible menu is still to eyeball; they work when typed). |
| 16 | Ignored, **mechanism unconfirmed** | Owner sent a message in a group containing the bot: no capture, no Hermes "blocked" line, no dispatch line, so it never reached stash. Probably Telegram's default bot privacy mode (groups deliver only commands and mentions) rather than any stash guard; `hermes_adapter/events.py` still does not check chat type. If privacy mode is ever turned off, add the guard. Not confirmed that the bot was a full member. |
| 17 | **Pass** | A second account messaged the bot in a private chat: the gateway logged `Blocked unauthorized user … in chat …` twice (13:54), no reply was seen, nothing was stored (capture count unchanged). Done by Hermes's allowed-users check, before stash. |
| 18 | Likely pass | `python_telegram_bot-22.8` is in Hermes's package cache, matching the adapter tests' binding (22.8). Not confirmed by importing it inside the gateway interpreter. |
| – | Note | Spike #6's "`stash list --stage inbox` shows it" is wrong: a deferred message is a pending capture, not an item. Doc to be corrected. |
| – | Finding | Filing latency 25–46 s warm/cold; thinking mode is the cost. See ADR 0004. |

Hermes config changed from defaults to: local `qwen3.5:latest` at 64k, Telegram toolset
`[web, stash]`, terminal/file/code/browser/delegation disabled. Backup of the original:
`~/.hermes/backups/pre-stash-*`.

Not yet run: #3, #4, #5 (baseline done for qwen3.5 only), #8, #10 (OpenRouter half), #11. #7 failed (above); #14 waits for its fix.

## Notes before the spike
- The installed Hermes checkout (`b7736eca98`, 2026-11-03) is 412 commits past the pin
  `43a35e8`. Its source has `inject_message(origin=…)`, `spawn_task`, hooks,
  `register_command` and `pre_gateway_dispatch`. The `--version` label (v0.21.0 /
  `git.b7736ec`) does not match the "v0.22.6" in the spec; trust the commit hash.
- Decide at the end of the spike whether to pin the tested commit or `43a35e8`.
