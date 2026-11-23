# Plan 9: a captured note is never lost to the `request` route (2026-11-22) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop a capture that the model calls a `request` from vanishing without an item, first with a deterministic floor, then, only if a measurement supports it, with a local decision model (Nimble) that gives calibrated route probabilities.

**Architecture:** A route that the filing model calls `request` is accepted only when the text looks like a question (the floor, T3, in `Filer._ask`, so the live pipeline and `stash eval` both see it). Separately a throwaway spike (T1, T2) measures whether Nimble's probabilities separate real requests from captures that contain trigger words ("ask", "I just finished"). If they do, an optional gate (T4) lets a confident `request` through without the question shape, and any scorer failure falls back to the floor. Nothing in this plan changes the filing prompt (four rewrites on 2026-11-22 moved the failures around; see ADR 0004).

**Order:** T3 as soon as D1 is answered (no GPU, no live service; it protects items now). T1 and T2 whenever the owner frees the GPU, before or after T3. T4 only after T2 says PASS and T3 is in.

**Tech Stack:** Python >= 3.11, httpx, Ollama (system install 0.33.2, upgraded to a pinned >= 0.35.0 in T1), `nimble:9b-q4_K_M` (5.6 GB; the bare `nimble` tag is the 9.3 GB q8 build), `uv`, `ruff`, `mypy --strict`, pytest.

**Spec:** `docs/superpowers/specs/2026-11-02-stash-design.md` ("If the AI judges it a request, it answers and the raw copy is discarded"; "nothing is lost"). Evidence: `docs/adr/0004-local-model.md`, the 2026-11-21 eval and `evals/cases.jsonl` (cases t17, r10, r11 lose items; r12 to r19 are held-out).

## Global Constraints

- Mac sandbox blocks Ollama: the suite stays offline (fakes, `httpx.MockTransport`). Only the steps marked OWNER (T1, T2, T3 Step 7, T4 Step 5) touch a live service, on the PC.
- **The owner needs the GPU for games.** Live steps run only when the owner says the GPU is free, and they end with no model loaded (`ollama stop <model>` for each model `ollama ps` lists, then `ollama ps` is empty; the server keeps models 5 minutes otherwise, `OLLAMA_KEEP_ALIVE=5m`). Never start or stop `hermes-gateway-stash` or the system `ollama` unit without the owner; the upgrade in T1 needs the owner's sudo.
- Fake data only: the spike reads `evals/cases.jsonl`, never the live database.
- Layering: only `stash.app` imports adapters; a new HTTP adapter lives in `stash.llm` and is listed in `ADAPTER_MODULES` (`tests/architecture_guard.py`); `stash.llm` must not import `stash.filing` and `stash.filing` must not import `stash.gpu` (`tests/unit/test_architecture_layers.py:151-164`), so the scorer Protocol and its value type live in `stash.llm.port` and the GPU check reaches the Filer as `stash.llm.port.BusyCheck`.
- LLM output is untrusted: probabilities are validated and clamped at the boundary; a bad or missing answer means "no score", never an exception into the pipeline.
- `make check` green before every commit; one task per commit; stage named paths only (never `uv.lock`); commit trailer `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.
- Python on the PC is written test-first through `superpowers:subagent-driven-development` with the `general-purpose` agent; `branch-reviewer` before it goes to the Mac. Docs edits are inline.

## Review Focus

- A link with a query string (`https://www.youtube.com/watch?v=…`, cases t04, t08) is not a question: URLs are removed before the `?` test. Test in T3.
- A scorer that is down, slow or returns garbage (NaN, probabilities that do not sum to 1, a missing option): behaviour must equal the floor alone. Test in T4.
- GPU busy when the scorer would run (only reachable with `busy_fallback = "openrouter"` or a race; with `"wait"` the router already defers filing): skip the gate, use the floor; never load a second model while the owner games. Test in T4.
- Capture text that tries to steer the decision model ("answer request"): the scorer only picks among three fixed options and its output is only ever used to *accept* a request, so the worst case is the floor's behaviour. Test in T4.
- A progress report with no question shape ("finished <saved book>") must still be reachable: one tap on "That was a question →" on a single confirmation, or a `?` prefix. A multi-item reply (`capture/burst.py:27`, `delivery/retry.py`) has no buttons, so its unsure line says to resend with `?`. T3 pins both.
- A question without `?` ("What should I do this weekend") must stay a request. T3 pins it.

## Open decisions

| # | Decision | Recommendation |
|---|---|---|
| D1 | Accept that a message without a question shape is never handed to the agent on the model's word alone? It is filed as an unsure inbox item instead. This covers progress reports ("finished X", spike #25's "I finished <book>, 4 stars"), imperatives ("list my books", "find my ramen places") and the spec's own examples "I have 2 h free Saturday" and "books I read this year". The owner taps "That was a question →" (it deletes the untouched item and hands the text over; `capture/fixes.py:120-130`) or starts with `?`. | **Decided yes 2026-11-22**: the owner accepts the cost and will start a progress report or imperative with `?`. **Yes.** A stray inbox item until the tap is cheaper than a lost note. Costs: the button's hand-over is unmeasured live (spike #14b, #23), and English-only word lists (a question in another language needs `?`). The alternatives are a store lookup or the gate (T4). |
| D2 | Build the gate (T4)? | **Decided by the T2 result** against the pass criteria below, not by preference. |

---

## T1: Upgrade the system Ollama to a pinned >= 0.35 and pull Nimble (PC, OWNER present, no code)

- [ ] **Step 1 (OWNER): say the GPU is free.** `stash gpu status` prints `GPU free`; the gateway is stopped (the installer restarts `ollama`).
- [ ] **Step 2: Record the way back and the baseline.** `ollama --version` (0.33.2 today), `systemctl cat ollama > ~/ollama-unit-before.txt`, `ollama list > ~/ollama-models-before.txt`, `stash eval --providers ollama --thinking off > ~/eval-before-upgrade.txt` (the 2026-11-22 route numbers are not recorded in the repo). Rollback is `curl -fsSL https://ollama.com/install.sh | OLLAMA_VERSION=0.33.2 sh` (syntax from docs.ollama.com/linux).
- [ ] **Step 3 (OWNER, sudo): upgrade in place to one named version.** `curl -fsSL https://ollama.com/install.sh | OLLAMA_VERSION=<v> sh`, `<v>` the newest 0.35.x patch (the smallest jump with decision models; latest is 0.40.x; record `<v>`). The installer rewrites `/etc/systemd/system/ollama.service` and restarts the unit but leaves the `ollama.service.d` drop-in alone. Passed: `ollama --version` prints `<v>`; `ollama list` matches the file from Step 2; `systemctl cat ollama` still shows the override; `ollama ps` after one request shows `CONTEXT 65536` (if 4096, reapply per `wsl-setup.md` section 3).
- [ ] **Step 4: Prove nothing regressed.** Run the Step 2 eval again. Passed: type, stage and date 100%, no errors, route within 2 cases of `~/eval-before-upgrade.txt` (route is noisy), text p50 under 3 s (thinking off still works; ADR 0004 verified it on 0.33.2 only). Then (OWNER) start the gateway and send "? what is on my list": one agent answer (spike #7). If anything differs, stop, roll back, record it in `docs/spike-m0.md` row #33.
- [ ] **Step 5: Pull Nimble and prove the endpoint.** `ollama pull nimble:9b-q4_K_M`. `curl http://localhost:11434/v1/systemone` with `{"model": "nimble:9b-q4_K_M", "state": "<a fake capture>", "questions": {"route": {"type": "choice", "instructions": "…", "criteria": {"capture": "…", "request": "…", "unsure": "…"}}}}` (shape from `https://docs.ollama.com/capabilities/decision.md`). Passed: `answers.route` has `choice`, `probabilities` summing to about 1 and `confidence`; record the exact response shape and whether a `keep_alive` field is accepted (the doc does not mention it). Failed: record the error text in row #33 and stop.
- [ ] **Step 6: Unload.** `ollama stop` every model `ollama ps` lists; `ollama ps` is empty.

## T2: The measurement spike (PC, throwaway script, ends with a decision)

**Files:**
- Create (not committed, outside the repo so it survives): `~/spikes/nimble_route_spike.py`
- Modify: `docs/spike-m0.md` (row #33, with the script path and the request body), this plan (the decision line below)

**Interfaces:**
- Consumes: `evals/cases.jsonl` (`id`, `text`), the T1 Step 5 request shape.
- Produces: a table of per-case probabilities and the decision below. No product code.

- [ ] **Step 1: Write the script.** Ground truth is fixed here, not read from `expect.route` (T3 changes some expectations): **requests the floor would drop** = r06, r07, r08, r09 (tuning), r18, r19 (held-out); **must never be accepted** = every capture-expected case plus r05. For every text case send one `choice` question `route` with options `capture`, `request`, `unsure` and a one-line description each (the filing prompt's Routes block without the example phrases). Run it twice: real option names, and neutral names `a`, `b`, `c` mapped back (label words bias answers). Print per case: id, group, the three probabilities, `confidence`, latency.
- [ ] **Step 2: Run it** on all text cases. Record cold and warm latency, `nvidia-smi` VRAM and `ollama ps` (PROCESSOR column) while Nimble is loaded, and the round trip back: the time of one `qwen3.5` filing request right after a Nimble call (the two do not fit in 12 GB together at 64k context, so every gate call swaps both ways).
- [ ] **Step 3: Choose the threshold on the tuning cases only** (t01 to t19, r01 to r11), then evaluate once on the held-out r12 to r19. Report, for the chosen `tau`: never-accept cases with p(request) >= `tau` (must be 0 on both sets), floor-dropped requests at or above `tau`, and p(request) for `t17`, `r10`, `r11`.
- [ ] **Step 4: Apply the pass criteria** (fixed here, before the run): PASS only if, at one `tau`, **(a)** no never-accept case in either set reaches `tau`, **(b)** at least 5 of the 6 floor-dropped requests reach it (only r18, r19 are held out; say so), and **(c)** warm latency is under 1 s and the Nimble-then-`qwen3.5` round trip under 10 s. The set is tiny (about 40 cases against the ~100 the papers use), so a PASS is weak evidence: the gate ships off by default. Write `PASS` or `FAIL` with the numbers and `tau` on the line `**T2 result:**` below, plus row #33.
- [ ] **Step 5: Clean up and commit.** `ollama stop nimble:9b-q4_K_M` (and any other model listed); `ollama ps` empty; `nvidia-smi` shows the GPU free. Commit only the docs: `docs: spike #33, Nimble route probabilities (Plan 9 T2)`.

**T2 result:** _not run yet._

## T3: The question-shape floor (waits for D1; no live service until Step 7)

**Files:**
- Create: `src/stash/filing/question_shape.py`
- Modify: `src/stash/filing/filer.py` (`_ask`), `src/stash/capture/replies.py` (`_bullet`), `src/stash/delivery/retry.py` (filed unsure lines), `evals/cases.jsonl`, `tests/unit/evaluation/test_shipped_cases.py`, `tests/acceptance/test_eval_comparison.py`, `tests/acceptance/test_delivery.py` (the two tests at ~466 and ~482), `tests/acceptance/test_hermes_capture.py` (the burst test at ~226); docs: the spec's "Message routing" section, `docs/usage.md` (lines 14-15, 27), `docs/spike-m0.md` #25 (start the message with `?`), the Mac handoff list, ADR 0004
- Test: `tests/acceptance/test_filing.py`, `tests/acceptance/test_capture_requests_and_fixes.py`, `tests/unit/filing/test_question_shape.py`

**Interfaces:**
- Produces: `looks_like_question(text: str) -> bool` in `stash.filing.question_shape`. First every URL found by `stash.enrich.urls.extract_urls` is removed. Then it is true when the rest contains `?`; or its first word (first run of letters, case-folded, so leading whitespace, emoji and punctuation are skipped) is in `QUESTION_WORDS = ("what", "which", "who", "whom", "when", "where", "why", "how")` and the next word is not in `NOT_A_QUESTION_AFTER = ("i", "a", "an", "to")` ("what I learned…", "how to fold…", "what a view" are statements); or its first two words are an auxiliary from `AUXILIARIES = ("should", "can", "could", "do", "did", "have", "is", "are", "will", "would")` followed by one of `("i", "we", "you", "there")`; or it starts with `show me`. Imperatives (find, tell, list, read) are not question shapes. No separate leading-`?` rule: a `?` message is forced to the agent before the Filer (`capture/routing.py`, `pipeline.py` `process`).
- Consumes: `Filing.without_request() -> Filing` (`domain/item.py:134`).

| Text | Shape | Outcome when the model says `request` |
|---|---|---|
| r01 "what can I do Saturday afternoon?", r02 "which books did I read this year?", r03 "show me my kept recipes", "What should I do this weekend", "what ramen places do I have saved" | yes | request |
| r04 "Saturday afternoon hike?" | yes (`?`) | request (the floor cannot help; expected stays `unsure`) |
| r06, r07, r08 "what I learned…", r09, r18, r19 (progress reports), "list my books", "I have 2 h free Saturday" | no | unsure, button or `?` |
| every capture-expected case, incl. t04/t08 (`watch?v=`), t17 ("ask"), r12 to r17 | no | unsure |

- [ ] **Step 1: Write the failing tests.** In `tests/acceptance/test_filing.py`, `build_filer` with `FakeChatModel(reply=a_request_answer())` (`tests/capture_builders.py:82`): `test_a_request_with_a_question_mark_stays_a_request`, `test_a_request_starting_with_a_question_word_stays_a_request` ("What should I do this weekend"), `test_a_request_without_a_question_shape_becomes_unsure` ("finished Tidewater Notes last night, loved the ending"), `test_a_question_mark_inside_a_link_does_not_make_a_request` ("try this for lunch https://www.youtube.com/watch?v=fake0001"), `test_a_trigger_word_alone_does_not_make_a_request` (t17's text), `test_an_image_note_without_a_question_shape_becomes_unsure` (`file_image`). In `test_capture_requests_and_fixes.py`: `test_a_progress_report_judged_a_request_is_filed_unsure_with_the_question_button`. Unit tests for `looks_like_question`: each rule and each table row, plus `test_every_shipped_capture_case_has_no_question_shape` and `test_every_shipped_request_case_has_a_question_shape` (read `evals/cases.jsonl` via `eval_files.SHIPPED_CASES`).
- [ ] **Step 2: Run them** (`uv run pytest tests/acceptance/test_filing.py tests/acceptance/test_capture_requests_and_fixes.py tests/unit/filing -q`); expect failures.
- [ ] **Step 3: Implement `looks_like_question` and apply it once in `Filer._ask`** after `parse_filing` (covers `file`, `file_image` and every eval arm): `request` plus no question shape returns `filing.without_request()`. The prompt is not touched. Agent captures are unaffected (`process_agent` already demotes).
- [ ] **Step 4: Multi-item replies.** A filed unsure bullet in `summary` and in the retry summary ends with `ASK_AGAIN`; a test for each. Give the three existing tests that pair `a_request_answer` with a shapeless text ("Ramen N", "message 2") a question-shaped text so they keep testing requests.
- [ ] **Step 5: Update the eval cases.** r06, r07, r08, r09, r18, r19 from `request` to `unsure` (commit message lists them; r03 keeps `request`). Add three held-out routing cases: "which restaurants have I saved" (`request`), "tell Sam about the ferry times" (`capture`), "loved the Harbor Lights podcast I saved, the last episode was the best" (`unsure`). Counts: routing 22 = request 4, unsure 9, capture 9 (rename the count-named tests); text arm 41 cases.
- [ ] **Step 6: Docs and commit.** Spec "Message routing": a request verdict without a question shape is filed as unsure. `usage.md`: what counts as a question, and that a report like "finished X" needs the button or `?`. Spike #25: the messages start with `?`. Mac handoff entry. `make check`; commit `fix: a request without a question shape is filed as unsure, never dropped (Plan 9 T3)`.
- [ ] **Step 7 (OWNER, GPU free): live eval.** `stash eval --providers ollama --thinking off`, then unload. Passed: no capture-expected case reported `got request`. Record the route accuracy in ADR 0004 as one line labelled "with the question-shape floor (product route, not comparable with earlier raw-model numbers)"; commit it as docs.

## T4: The route gate (conditional: only if T2 says PASS)

**Files:**
- Create: `src/stash/llm/systemone.py` (the adapter), `src/stash/filing/route_gate.py`
- Modify: `src/stash/llm/port.py` (Protocol and value type), `src/stash/filing/filer.py`, `src/stash/config/model.py` and `loader.py` (`[llm.route_gate]`), `src/stash/app/build.py` and `providers.py` (wiring), `src/stash/evaluation/arms.py` (`build_arms` takes the gate), `src/stash/app/doctor_checks.py`, `tests/architecture_guard.py` and `tests/unit/test_architecture.py` (the new adapter), `deploy/stash.toml.example`, `docs/deploy/wsl-setup.md`
- Test: `tests/acceptance/test_filing.py`, `tests/unit/llm/test_systemone.py`, `tests/unit/config/test_loader_route_gate.py`, `tests/fakes/scripted_route_scorer.py`

**Interfaces:**
- Produces in `stash.llm.port`: `RouteProbabilities` (frozen, slots: `capture: float`, `request: float`, `unsure: float`; `__post_init__` rejects non-finite, negative or a sum outside `1 ± PROBABILITY_SUM_TOLERANCE`) and `RouteScorer` Protocol `score(text: str) -> RouteProbabilities | None` (None means no usable score; never raises).
- `SystemOneRouteScorer(settings: ProviderSettings, model: str, client: httpx.Client)` in `stash.llm.systemone`: posts to `settings.endpoint("systemone")` with the T2 winning option wording, `state` clipped to `SCORED_TEXT_LIMIT` (4000 characters, as the filing prompt), timeout `SCORE_TIMEOUT` (a module constant from T2's cold latency); HTTP errors, timeouts, an `{"error": …}` body and malformed answers return None and log the error type only (never the text). No `keep_alive` unless T1 Step 5 showed it is accepted.
- `RouteGate(scorer: RouteScorer, busy: BusyCheck, request_threshold: float)` in `stash.filing.route_gate` with `accepts(text: str, now: datetime) -> bool`: false when busy or the score is None, else `request >= request_threshold`. `Filer(router, clock, timezone, gate: RouteGate | None = None)`: the gate is asked only for a `request` verdict without a question shape.
- `RouteGateConfig(enabled: bool = False, model: str = NIMBLE_MODEL, request_threshold: float = T2_THRESHOLD)` in `stash.config.model`, `NIMBLE_MODEL = "nimble:9b-q4_K_M"`, `T2_THRESHOLD` the T2 `tau`; field `LlmConfig.route_gate`; the threshold is validated to (0, 1]; `enabled = true` without `[llm.ollama]` is a `ConfigError`. The gate uses `[llm.ollama]`'s `base_url`.

- [ ] **Step 1: Failing tests.** The Filer with `a_request_answer()` and a shapeless text: `test_a_confident_request_without_a_question_shape_is_accepted` (request 0.97, threshold 0.9), `test_an_unconfident_request_without_a_question_shape_becomes_unsure` (0.6), `test_a_missing_score_falls_back_to_the_floor` (None), `test_a_busy_gpu_skips_the_scorer` (`FakeBusy`; the scorer is not called), `test_a_question_shaped_request_never_calls_the_scorer`. Adapter tests with `httpx.MockTransport`: a normal answer maps to `RouteProbabilities`; a 500, a timeout, an `{"error": …}` with 200, `NaN`, negative, summing to 0, and a missing option return None. Config tests: default `enabled = False`; an unknown key, a threshold outside (0, 1], and enabled without `[llm.ollama]` raise `ConfigError`.
- [ ] **Step 2: Run them**; expect failures.
- [ ] **Step 3: Implement** the types, the adapter, `RouteGate`, the config table, the Filer step, the wiring in `stash.app` only (the pipeline's Filer and `build_arms` get the same gate when enabled), and the doctor line: an optional `route gate` check reusing `OllamaProbe` with the Nimble model, present only when enabled.
- [ ] **Step 4: `make check`; commit** `feat: an optional decision-model gate lets a confident request through (Plan 9 T4)`.
- [ ] **Step 5 (OWNER, GPU free): live check.** `stash eval` with the gate on, then unload. Passed: the set of cases reported `got request` equals T2's accepted set at `tau` (with the gate on, r06 to r09, r18, r19 show as mismatches against `unsure` by design). Record the added latency per gated message (it runs inside `SerializedPipeline`'s lock and the hook, spike #23).
- [ ] **Step 6: Docs.** `wsl-setup.md`: the pinned Ollama upgrade is an owner step, the gate is off by default, the model swap cost. Mac handoff entry. Commit as docs.

## Verification

- `make check` green after T3 and T4. Report `wc -l` for src and tests added (tests at most about 2x the source, rule R15).
- T3 offline: every shipped capture case has no question shape (unit test). T3 live: no capture-expected case `got request`.
- T2/T4 live: only with the owner present and the GPU free; each ends with `ollama ps` empty.

## Findings not planned

- Hosted Jev (no free tier, waitlist, US-hosted, undefined retention) and Laya (an encoder that needs fine-tuning and a new dependency) are not options for private notes.
- Moving item type and stage to a decision model, a duplicate check and tool-call gating are possible later uses; they wait for the route result.

## Audit 2026-11-22

Full audit: the session scratchpad `plan9-audit.md`. Changes made above:

1. `?` in a URL counted as a question (t04, t08 `watch?v=`): URLs removed first (`enrich/urls.py` `extract_urls`).
2. "Seven expectations change" was wrong: r03 matches `show me`; r08 matched "what". The rule now excludes WH + I/a/an/to, so six change (r06-r09, r18, r19). Counts were checked against `test_shipped_cases.py:42` and `test_eval_comparison.py:61`.
3. Three existing tests pair `a_request_answer` with shapeless text through the real Filer (`test_delivery.py:466,482`, `test_hermes_capture.py:226`): added to T3.
4. Multi-item replies have no buttons (`capture/burst.py:27`, `replies.py:51-63` vs `summary`): the unsure bullet says to resend with `?`.
5. D1 named only progress reports. It now also names the spec's own examples (spec:238-239), imperatives and spike #25. Spec, usage, #25 and handoff edits added.
6. T4 types in `stash.filing` would make `stash.llm` import filing (layers test :161-164): moved to `stash.llm.port`. The GPU check uses `BusyCheck`, not `stash.gpu` (:151-155).
7. `RouteGateConfig` had a non-default field after a default one, and its model default `nimble` = 9.3 GB q8: fixed. `base_url` comes from `[llm.ollama]`, and timeout and keep_alive are now owned by the adapter.
8. `stash eval` could not see a gate (`arms.py:86`): `build_arms` takes it; the live check compares against T2, not against eval pass/fail.
9. Doctor wiring is `app/doctor_checks.py` plus `OllamaProbe`, not `doctor_probes.py`. The new adapter needs `ADAPTER_MODULES`.
10. Spike rows #31 and #32 exist: row #33.
11. The baseline "30/38" is not in the repo: a pre-upgrade eval is now in T1 Step 2. Route tolerance and a thinking-off latency and agent-turn smoke test added. The installer is pinned to one version.
12. `keep_alive` is undocumented for `/v1/systemone`: cleanup by `ollama stop`. T1 now unloads too.
13. T2 read ground truth from `expect.route`, which T3 changes: fixed id groups. Criterion (b) is now the floor-dropped set (5 of 6). The VRAM swap round trip is measured.
14. The spike script was in the scratchpad: now `~/spikes/`. Steps that carried two actions (T3 Step 5, T4 Step 2) were split. T3 no longer waits on T1/T2.

Not verified: the Nimble response field shapes beyond the doc summary (T1 Step 5 records them); whether the installer configures systemd before its WSL2 GPU exit (the Step 3 checks catch it); spike #14b (the button's hand-over) on the live gateway.
