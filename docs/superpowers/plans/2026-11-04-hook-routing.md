# Route questions inside the hook (spike #7 fix) — implementation plan

> **For agentic workers:** Python is written as `CLAUDE.md` § "Writing Python" says for the
> machine you are on (Mac: the `python-development` orchestrator; PC/WSL: subagent-driven
> development with TDD). The main loop commits. Run with superpowers:subagent-driven-development.
> Steps use checkbox (`- [ ]`) syntax. A follow-up from the PC (`docs/adr/0001-hermes-gate.md`
> row 7; handoff note "Updates", 2026-11-04). Build **after** `2026-11-04-thinking-control.md`,
> because the hook now waits for classification.

**Goal:** Questions reach the Hermes agent again. The hook saves the message raw, classifies it,
and answers `allow` for a request, so Hermes runs a normal agent turn on the owner's own message.
It answers `skip` for everything else. Nothing is injected on the normal path.

**Architecture:** `MessageIntake.on_dispatch` stops spawning `_process` in the background. It
awaits `steps.process(capture)` (in a thread) and turns the result into the verdict. The
`inject_message` path stays only for the "That was a question →" button and for questions filed
late by `/stash_retry`. Hermes refuses those when no human message has been admitted, so the
apology tells the owner how to re-ask. A message starting with `?` is a forced question: it is
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
  - Whether Hermes times out a `pre_gateway_dispatch` hook that takes 25–45 s (thinking on).
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
