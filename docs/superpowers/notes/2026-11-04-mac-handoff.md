# Mac handoff — continue stash development (from the PC, 2026-11-04)

Read this file first. It is written for the Claude session on the Mac. It is a brief, not a plan:
the code plans are `docs/superpowers/plans/2026-11-0*-plan-N-*.md` (Plan 1 is built).

## Updates since your last merge (newest first; re-read this list every time you merge `pc-m0`)

- **2026-11-04, answer for Plan 3 Task 6 (ticker).** Use the plan's in-process `Ticker`, started from the
  platform-handler factory via `ctx.spawn_task` (verified live: running loop, supervised task survives).
  Requirements: (1) a **once-only guard**, because Hermes re-runs the factory on every rebuilt Telegram
  client; (2) cancel cleanly on unload (spawn_task tasks are cancelled for you). Keep `stash tick`
  (cron `--no-agent`) as the fallback: it prints nothing when nothing is due and Hermes then stays
  silent (verified), but its output has no buttons and gets Hermes's "Cronjob Response" wrapper.
  Do not build a cron-plus-direct-send variant. See ADR 0001 rows 2, 2b, 2c.
- **2026-11-04, spike #7 failed (not a no-go).** Questions never reach the Hermes agent because the
  hook returns `SKIP` for every message. Fix is in the adapter: classify inside the hook and return
  `ALLOW` for requests. Details in section 3 ("Questions do not reach the agent yet") and
  `docs/adr/0001-hermes-gate.md` row 7. Check #14 waits for that fix. Land the per-task thinking
  setting (ADR 0004) first, because the hook will wait for classification.
- **2026-11-04, first handoff.** Everything else in this file.

How to pick up an update while you are mid-work: finish or commit your current task, make sure the
tree is clean (`git status`), then `git merge pc-m0` (a normal merge is fine if `main` has moved; the
PC touched docs, `plugin.py`, `ocr.py`, `pyproject.toml` and their tests, so conflicts should be rare).
Run `make check`, then read the new entries above and adjust the plan you are on.

## 1. Get the PC's work in (do this before anything else)

1. `git merge pc-m0` (branch is in this repo; fast-forwards from `main` at `3d969d8`).
2. Regenerate the lockfile — `pyproject.toml` dependencies changed (OCR is now an optional extra):
   `uv lock --default-index https://pypi.org/simple`
   A plain `uv lock` re-pins `pypi.apple.com`, which does not resolve on the PC. Check this Mac can
   reach public PyPI first. Never commit the PC's own `uv.lock`.
3. `make check` must be green before new work (PC result on the branch: 3036 unit, 60 integration).
4. More PC commits may arrive on `pc-m0` (remaining spike checks, model eval). Merge it again
   before starting each new plan.

## 2. What the PC proved (live Telegram bot, fake data)

Full table in `docs/adr/0001-hermes-gate.md`. Summary:

- **Hermes decision: GO.** #1 (inline buttons) and #6 (raw save before the LLM) passed.
- #2 scheduled code without an agent turn: **works** — Hermes cron `--no-agent --script`.
- #13 plain message → hook `skip`, item saved; #17 strangers blocked by Hermes before stash;
  #12 Tesseract OCR works; #10 Ollama accepts the filing schema (OpenRouter half untested);
  #16 groups ignored (mechanism unconfirmed); #18 PTB 22.8 in Hermes's cache (likely).
- Not run yet on the PC: #3, #4, #5 (full model eval), #7, #8, #9 (YouTube/Instagram/localhost),
  #11, #14, and the OpenRouter half of #10.

## 3. Facts that change the code

- **Command aliases:** the Hermes gateway looks plugin commands up as `name.replace("_", "-")`.
  A refused `/retry` is registered as `stash-retry` (typed `/stash_retry`). Already fixed on the branch.
  The offline fake context did not model this; consider making `tests/fakes/hermes_ctx.py` do the
  same normalisation so the next such bug fails offline.
- **Filing is slow because the model thinks.** Live filing took 25–46 s per message. Ollama's `/v1`
  accepts `"reasoning_effort": "none"` (measured: 4.7 s → 0.2 s on a small prompt). stash sends no
  thinking control. Add a per-task setting (filing off by default) and let `stash eval` compare
  quality before making it the default (ADR 0004).
- **Dates are the weak spot.** Baseline eval (`qwen3.5`, thinking on): route 91%, type 100%, stage
  94%, details 100%, **date 0%**. Both date-bearing cases fail: `t10` (text, expects stage `planned`,
  date `2027-03-14`) and `i02` (poster image; OCR reads the text correctly but the case errors).
  The eval report shows only aggregates, so first make it print each case's model output and
  expected values, reproduce `t10`, then try thinking off. See ADR 0004.
- **Questions do not reach the agent yet (spike #7 failed).** `MessageIntake.on_dispatch` returns
  `SKIP` for every message and later calls `inject_message` for requests; Hermes refuses
  ("has no human message admitted yet; a plugin can continue a chat, not open one"), so the user gets
  "I couldn't pass that on to the assistant." The raw capture is saved first, so nothing is lost.
  Fix (the spec's own fallback): decide inside the hook. Save raw, classify, return `ALLOW` for
  requests so Hermes runs a normal agent turn, `SKIP` for captures. The hook then waits for
  classification, which is 25-45 s with thinking on and well under a second with it off, so land the
  thinking setting first. Spike #14 (no loop-back) can only be checked after this.
- **Pending captures are not items.** A message saved while the AI is down is a capture with
  `status=pending` and no item; `stash list` will not show it. It is filed by `/stash_retry`
  (no automatic retry exists in Plan 1).
- **Cron output format:** Hermes wraps cron output in a "Cronjob Response" header and a
  "send me a message to stop this job" footer. Delivery needs an explicit target
  (`telegram:<chat id>`) because no home channel is set.
- **Telegram menu limit:** Hermes registers 60 commands and hides 66 more; whether stash's
  commands appear in the visible menu is unverified (they work when typed).
- **Hermes version:** the PC runs git checkout `b7736eca98` (412 commits past the pin `43a35e8`);
  its `--version` label is stale. The plugin APIs stash uses are present in that source.
- **Optional OCR:** `make_ocr` falls back to `NoOcr` if the `tesseract` binary or the `ocr` extra is
  missing. Keep or drop the extra after the vision-vs-OCR eval (ADR 0003).

## 4. What to build now (offline; fake data only)

Rules: follow `CLAUDE.md` ("Writing Python": use the `python-development` orchestrator here;
`make check` is the gate; one task per commit). Every assumption about a live service gets a short
comment saying what the PC must verify.

| Plan | Status |
|---|---|
| Plan 2 — lifecycle | Build now. Button flows are confirmed on the live bot. |
| Plan 3 — planning & nudges | Build now, **including Task 6**: use the Hermes cron `--no-agent` mechanism (#2). |
| Plan 4 — people | Build now (needs Plans 2–3). |
| Plan 6 — HTML library | Build now (needs Plan 2). |
| Plan 5 — transcripts & images | **Wait** for the PC's model eval (image reader choice, Whisper VRAM). |

Small follow-ups from the branch review (do alongside, not first):
- `make_ocr` falls back silently: log a warning, or have `stash doctor` mention the `ocr` extra.
- `tests/unit/app/test_ocr.py` and `test_build_app.py` import `TesseractOcr` at module level, and
  `tests/integration/test_tesseract_ocr.py` has no `importorskip`; they fail at collection without the extra.
- `plugin.py` ignores the result of registering the `stash-<name>` alias; check it and log the
  name the user types.
- `docs/usage.md` (OCR arm) should say the arm needs the `ocr` extra.

## 5. What stays on the PC

Anything that needs Telegram, Ollama, the GPU, OpenRouter keys, `yt-dlp` on real sites, Whisper,
the NAS or systemd: the remaining spike checks, the model/vision eval, OpenRouter, backups, and
installing the gateway as a service. The PC will push results as ADR edits on `pc-m0`.

## 6. Do not

- Put real personal items, tokens, chat IDs or the PC's `uv.lock` in this repo.
- Run `hermes update` on the PC's behalf or change the Hermes pin without recording it in `docs/adr/`.
- Depend on the PyPI `hermes-agent` package (stale).
