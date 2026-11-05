# Hermes adapter fixes from the PC (spike #7, hot-reload, link details) — implementation plan

> **For agentic workers:** Python is written as `CLAUDE.md` § "Writing Python" says for the
> machine you are on (Mac: the `python-development` orchestrator; PC/WSL: subagent-driven
> development with TDD). The main loop commits. Run with superpowers:subagent-driven-development.
> Steps use checkbox (`- [ ]`) syntax. A follow-up from the PC (`docs/adr/0001-hermes-gate.md`
> row 7; handoff note "Updates", 2026-11-04). Build **after** `2026-11-04-thinking-control.md`,
> because the hook now waits for classification.

**Goal (Task 1):** Questions reach the Hermes agent again. The hook saves the message raw, classifies it,
and answers `allow` for a request, so Hermes runs a normal agent turn on the owner's own message.
It answers `skip` for everything else. Nothing is injected on the normal path.

**Architecture:** `MessageIntake.on_dispatch` stops spawning `_process` in the background. It
awaits `steps.process(capture)` (in a thread) and turns the result into the verdict. The
`inject_message` path stays only for the "That was a question →" button. Hermes refuses it when
no human message has been admitted, so the apology tells the owner how to re-ask. A question
found late by `/stash_retry` is not injected: its `request` line tells the owner to send it again
starting with `?`. A message starting with `?` is a forced question: it is
saved raw and answered `allow` with no LLM call.

**Tech Stack:** unchanged.

**Spec:** design doc → Message routing (capture vs request), Hermes facts #6; ADR 0001 #7/#14.

## Global Constraints

- Raw-first is unchanged: `steps.receive` (the raw save) completes before any classification,
  and a save failure still apologises and answers `skip`.
- Verdicts:
  - `Filed` → `skip` (bursts unchanged).
  - `Deferred` → `skip` (the "saved, will file later" reply is unchanged).
  - `Duplicate` → `skip`.
  - `IsRequest` → `allow`.
  - An exception while processing → log it and answer `skip`. The capture stays pending and
    retryable.
  - Commands and non-owner messages are unchanged (`allow`).
- The forced-question prefix is the constant `QUESTION_PREFIX = "?"` (after stripping leading
  whitespace). The capture is saved raw, then marked as a request through the pipeline's existing
  request path (the same status `IsRequest` sets). Hermes receives the message unchanged, with
  the `?` still in it.
- New apology text, for both refused injections: the constant
  `APOLOGY = Reply("I couldn't pass that on to the assistant. Send it again starting with ? and I'll hand it over.")`.
- **Unverified, PC must check (spike-m0 #23):**
  - Whether Hermes times out a `pre_gateway_dispatch` hook that takes up to ~100 s for a shared link (inspection ≤ 25 s + filing 62–82 s with thinking on, ADR 0001 #9).
  - Whether a slow hook delays other messages.
  - Whether `inject_message` is accepted once the chat has had any admitted human message.
  
  Put a one-line comment at the await saying so.

## Review Focus

1. **A burst of 5 messages with one question among them.** Exactly one `allow`, four `skip`s, and
   one combined confirmation for the four captures.
2. **The AI goes down between the raw save and classification.** The verdict is `skip`, the
   capture stays pending, and nothing reaches the agent.
3. **`?` alone, `"  ? what can I do"`, and a URL containing `?`** (`https://x.test/a?b=1`). Only
   a message *starting* with `?` is forced. The first two are forced; the URL is classified
   normally.
4. **Hermes redelivers a question** (same message id). The second delivery is a `Duplicate` and
   gets `skip`, so the agent answers once.
5. **The fake Hermes context models the real refusal.** `tests/fakes/hermes_ctx.py`'s
   `inject_message` returns False unless the chat has had an `allow`ed message. Without that, an
   offline test can pass while the live bot fails, as happened with #7.

---

### Task 1: Classify in the hook; `?` forces a question; honest apology

**Files:**
- Modify: `src/stash/hermes_adapter/{intake,assistant,events}.py`, `src/stash/capture/pipeline.py`
  (only if the request-marking step is not already reachable), `tests/fakes/hermes_ctx.py`.
- Modify docs: `docs/usage.md` ("Telegram through Hermes", statements 1 and 7: `allow` for
  questions; the `?` prefix), `docs/spike-m0.md` (#7 re-run, #14, new #23).
- Test: `tests/acceptance/test_hermes_capture.py` (additions), `tests/unit/hermes_adapter/test_intake_routing.py`.

**Interfaces:**
- Consumes: `IntakeSteps.receive/process`, `ProcessResult` variants, `Verdict`, `Bursts`,
  `Assistant`.
- Produces: the verdict mapping in Global Constraints; `QUESTION_PREFIX`; the new `APOLOGY`; the
  fake context's admitted-chat rule (RF5); and an `IntakeSteps.mark_request(capture) -> None`
  method if the pipeline has no public way to record a forced request.
  **Superseded by the controller's follow-up rulings (2026-11-04):** the `?` rule is core
  pipeline routing (`stash.capture.forces_request`; `process()` returns `IsRequest` for it,
  first time or on retry), so there is no `mark_request`. A forced question whose
  processing fails answers `allow`. In short, the `?` rule moved from the adapter into the core
  pipeline and `mark_request` was removed.
- [ ] **Step 1: Failing tests:**
  - Acceptance:
    - "What can I do this Saturday?" classified as a request → the hook answers `allow`, nothing
      is injected, and no item is created.
    - A capture → `skip` and the usual confirmation.
    - RF1–RF4, each as one test.
    - The reroute button on a chat with no admitted message → `APOLOGY`.
    - The reroute button after an `allow`ed question in the same chat → injected.
  - Unit: the verdict for each `ProcessResult` and for a raised exception.
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement. **Step 4:** `make check`.
- [ ] **Step 5:** Update the docs named above. Spike #23 covers: hook latency with thinking on and
  off, whether a long hook blocks a second message, and injection after an admitted message.
- [ ] **Step 6: Commit** `fix(hermes): route questions with an allow verdict instead of injecting (spike #7)`.

### Task 2: Survive a plugin hot-reload (outbox and buttons keep working)

> From the PC, 2026-11-04 (ADR 0001, "stash breaks after a plugin hot-reload"). After any
> `hermes plugins enable/disable` on a running gateway, Hermes re-runs `register()` but **skips**
> stash's Telegram handler factory, because factories are deduplicated by `(plugin, function
> qualname)`. The new `LateBoundOutbox` is never bound, and every reply fails with
> `OutboxUnavailable` until a gateway restart. Buttons are probably dead too.

**Files:**
- Modify: `src/stash/hermes_adapter/plugin.py` and the state it builds (`wiring.py`,
  `telegram_io.py` as needed).
- Modify: `tests/fakes/hermes_ctx.py`.
- Modify docs: `docs/usage.md` ("Telegram through Hermes"), `docs/spike-m0.md` (new #24).
- Test: `tests/acceptance/test_hermes_registration.py` (additions).

**Interfaces / behaviour:**
- A second `register(ctx)` in the same process leaves stash fully working:
  - The hook in force after the second `register` can send replies.
  - Button presses are handled.
  - Commands answer.
  
  This holds even though the Telegram factory is **not** called again.
- Fix direction (implementer's choice of mechanism): keep the outbox binding and the button
  attachment in process-wide adapter state that a later `register()` reuses, or re-bind from
  `register()` itself when a Telegram application is already known. Either way:
  - At most one `StashApp` (one database connection) stays open after re-registration. Close
    or reuse the old one, and never leak it.
  - This state is the same place Plan 3 Task 6's once-only ticker guard will live, so keep it
    a small named object, not scattered module globals.
- The fake context models Hermes's dedupe. `register_platform_handler` ignores a factory whose
  `(plugin, qualname)` was already registered, and a test helper simulates "connect" by calling
  the stored factories once. Without this, an offline test can pass while the live bot fails.
- [ ] **Step 1: Failing acceptance test:**
  - `register` → connect (factory called) → `register` again on the same context. The deduped
    factory is not called again.
  - A captured message's confirmation is delivered, and a button press edits its message.
  - One app is open.
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement. **Step 4:** `make check`.
- [ ] **Step 5:** Docs:
  - Usage: re-registration is safe.
  - Spike #24: `hermes plugins enable <other>` on the running gateway, then send a link. The
    confirmation arrives and its buttons work, with no restart. Until #24 passes, the deploy doc's
    "restart after plugins enable/disable" stays (ADR 0005).
- [ ] **Step 6: Commit** `fix(hermes): keep the outbox and buttons bound across a plugin hot-reload`.

### Task 3: Save link title, uploader and duration deterministically

> From the PC, 2026-11-04 (spike #9). The link inspector finds the title, uploader and duration,
> but they reach the item only if the model copies them into `details`. On YouTube it omitted
> both.

**Files:**
- Modify: `src/stash/capture/pipeline.py`, or the filing step that turns a `Filing` plus
  `LinkInfo` into an `Item` (wherever the item is built).
- Modify: `src/stash/domain` only if a named key constant is needed.
- Modify docs: `docs/usage.md` (the link section).
- Test: `tests/acceptance/test_link_inspection_app.py` (additions) and a unit test next to the
  code that merges the values.

**Interfaces / behaviour:**
- When a capture has a link and inspection returned values, the saved item's `details` gets:
  - `link_title`, from `LinkInfo.title`;
  - `uploader`, from `LinkInfo.uploader`;
  - `duration`, from `LinkInfo.duration_s`, formatted `H:MM:SS`, or `M:SS` under an hour.
  
  Each key is added only if the value is known.
- These values **override** any model-written value for the same key, because they are facts
  from the source. The model's own `title` field is unchanged.
- The values are untrusted. `LinkInfo` already clamps them; also apply the existing details
  value limit and the collapse-whitespace rule. A 0-second duration is stored as `0:00`.
- No link, or `LinkInfo.unknown` → `details` are exactly what the model returned.
- [ ] **Step 1: Failing tests:**
  - A fake YouTube inspection (title "Knife skills 101", uploader "Test Kitchen", 754 s), with
    the model omitting all three, gives details `link_title`, `uploader` and `duration="12:34"`.
  - The model writing `uploader="someone else"` is overridden.
  - 3 723 s → `"1:02:03"`.
  - Unknown link → details unchanged.
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement. **Step 4:** `make check`.
- [ ] **Step 5: Commit** `feat(capture): keep link title, uploader and duration on the item`.
