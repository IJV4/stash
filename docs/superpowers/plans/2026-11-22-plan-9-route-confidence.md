# Plan 9: a captured note is never lost to the `request` route (2026-11-22) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop a capture that the model calls a `request` from vanishing without an item, first with a deterministic floor, then, only if a measurement supports it, with a local decision model (Nimble) that gives calibrated route probabilities.

**Architecture:** A route that the filing model calls `request` is accepted only when the text looks like a question (the floor, T3). Separately a throwaway spike (T1, T2) measures whether Nimble's probabilities separate real requests from captures that contain trigger words ("ask", "I just finished"). If they do, an optional gate (T4) lets a confident `request` through without the question shape, and any scorer failure falls back to the floor. Nothing in this plan changes the filing prompt (four rewrites on 2026-11-22 moved the failures around; see ADR 0004).

**Tech Stack:** Python >= 3.11, httpx, Ollama (system install 0.33.2, upgraded to >= 0.35.0 in T1), `nimble:9b-q4_K_M`, `uv`, `ruff`, `mypy --strict`, pytest.

**Spec:** `docs/superpowers/specs/2026-11-02-stash-design.md` ("If the AI judges it a request, it answers and the raw copy is discarded"; "nothing is lost"). Evidence: `docs/adr/0004-local-model.md`, the 2026-11-21 eval and `evals/cases.jsonl` (cases t17, r10, r11 lose items; r12 to r19 are held-out).

## Global Constraints

- Mac sandbox blocks Ollama: the suite stays offline (fakes, `httpx.MockTransport`). Only T1 and T2 touch a live service, on the PC.
- **The owner needs the GPU for games.** T1 and T2 run only when the owner says the GPU is free, and they end with no model loaded. Never start or stop `hermes-gateway-stash` or the system `ollama` unit without the owner; the upgrade in T1 needs the owner's sudo.
- Fake data only: the spike reads `evals/cases.jsonl`, never the live database.
- Layering: only `stash.app` imports adapters; a new HTTP adapter lives in `stash.llm`; the Filer depends on a Protocol, not on the adapter.
- LLM output is untrusted: probabilities are validated and clamped at the boundary; a bad or missing answer means "no score", never an exception into the pipeline.
- `make check` green before every commit; one task per commit; stage named paths only (never `uv.lock`); commit trailer `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.
- Python on the PC is written test-first through `superpowers:subagent-driven-development` with the `general-purpose` agent; `branch-reviewer` before it goes to the Mac. Docs edits are inline.

## Review Focus

- A scorer that is down, slow or returns garbage (NaN, probabilities that do not sum to 1, a missing option): behaviour must equal the floor alone. Test in T4.
- GPU busy when the scorer would run: skip the gate, use the floor; never load a second model while the owner games. Test in T4.
- Capture text that tries to steer the decision model ("answer request"): the scorer only picks among three fixed options and its output is only ever used to *accept* a request, so the worst case is the floor's behaviour. Test in T4.
- A progress report with no question mark ("finished <saved book>") must still be reachable: one tap on "That was a question →" or a `?` prefix. T3 pins the reply carries the button.
- A question without `?` ("What should I do this weekend") must stay a request. T3 pins it.

## Open decisions

| # | Decision | Recommendation |
|---|---|---|
| D1 | Accept that a progress report such as "finished X" without `?` is filed as an unsure item (one tap or a `?` prefix sends it to the agent)? | **Yes.** The alternative is a store lookup or the gate (T4), and the cost of the tap is smaller than a lost item. T3 waits for D1. |
| D2 | Build the gate (T4)? | **Decided by the T2 result** against the pass criteria below, not by preference. |

---

## T1: Upgrade the system Ollama to >= 0.35 and pull Nimble (PC, owner present, no code)

- [ ] **Step 1 (OWNER): say the GPU is free.** `stash gpu status` prints `GPU free`; the gateway is stopped.
- [ ] **Step 2: Record the way back.** `ollama --version` (0.33.2 today), `systemctl cat ollama > ~/ollama-unit-before.txt`, `ollama list > ~/ollama-models-before.txt`. Rollback is `curl -fsSL https://ollama.com/install.sh | OLLAMA_VERSION=0.33.2 sh`.
- [ ] **Step 3 (OWNER, sudo): upgrade in place.** `curl -fsSL https://ollama.com/install.sh | sh`. Passed: `ollama --version` is >= 0.35.0; `ollama list` shows the same models as before; `ollama ps` after one request shows `CONTEXT 65536` (the override in `deploy/systemd/ollama.override.conf` survived; if it shows 4096 reapply it per `wsl-setup.md` section 3).
- [ ] **Step 4: Prove nothing regressed before anything else.** `stash eval --providers ollama --thinking off`. Passed: route about 79% (30/38 on the 38 text cases), type, stage and date 100%, no errors; the same numbers as the 2026-11-22 baseline. If they differ, stop, roll back, and record it in `docs/spike-m0.md` row #31.
- [ ] **Step 5: Pull Nimble and prove the endpoint.** `ollama pull nimble:9b-q4_K_M` (5.6 GB). `curl http://localhost:11434/v1/systemone` with the choice example from `https://docs.ollama.com/capabilities/decision.md`. Passed: a JSON answer with `probabilities` summing to about 1 and a `confidence`. Failed: record the error text in row #31 and stop.

## T2: The measurement spike (PC, throwaway script, ends with a decision)

**Files:**
- Create (not committed): `<scratchpad>/nimble_route_spike.py`
- Modify: `docs/spike-m0.md` (row #31), this plan (the decision line below)

**Interfaces:**
- Consumes: `evals/cases.jsonl` (`id`, `text`, `expect.route`), `POST http://localhost:11434/v1/systemone`.
- Produces: a table of per-case probabilities and the decision below. No product code.

- [ ] **Step 1: Write the script.** For every case with `arm == "text"`, send one `choice` question named `route` with options `capture`, `request`, `unsure` and a one-line description each (taken from the filing prompt's Routes block, without the example phrases). Run it twice: with the real option names and with neutral names `a`, `b`, `c` mapped back (label words bias answers). Print per case: expected route, the three probabilities, `confidence`, latency. Use `keep_alive` of `0` on the last request so the model unloads.
- [ ] **Step 2: Run it** on all 38+ text cases. Record the first-call (cold) and warm latency, and the VRAM from `nvidia-smi` while Nimble is loaded.
- [ ] **Step 3: Choose the threshold on the original cases only** (t01 to t19, r01 to r11), then evaluate once on the held-out r12 to r19. Report, for the chosen threshold `tau`: captures accepted as `request` (must be 0 on both sets), requests accepted as `request` (share), and the probability Nimble gives `t17`, `r10`, `r11`.
- [ ] **Step 4: Apply the pass criteria** (fixed here, before the run): the gate is worth building only if, at one `tau`, **(a)** no capture-expected case in either set is accepted as `request`, **(b)** at least 70% of request-expected cases without a question mark (r03, r06 to r09, r18, r19) are still accepted, and **(c)** warm latency is under 1 s and VRAM with Nimble loaded leaves room for `qwen3.5` to swap in under 10 s. The set is small (about 40 cases against the ~100 the papers use), so say so in the record. Write `PASS` or `FAIL` with the numbers on the line `**T2 result:**` below, plus a row #31 in `docs/spike-m0.md`.
- [ ] **Step 5: Clean up.** `ollama ps` shows no model (the last request used `keep_alive` 0); `nvidia-smi` shows the GPU free. Commit only the docs: `docs: spike #31, Nimble route probabilities (Plan 9 T2)`.

**T2 result:** _not run yet._

## T3: The question-shape floor (waits for D1; no live service)

**Files:**
- Create: `src/stash/filing/question_shape.py`
- Modify: `src/stash/filing/filer.py` (`Filer.file`, `Filer.file_image` use the floor), `evals/cases.jsonl`, `tests/unit/evaluation/test_shipped_cases.py`, `tests/acceptance/test_eval_comparison.py`
- Test: `tests/acceptance/test_filing.py`, `tests/unit/filing/test_question_shape.py`

**Interfaces:**
- Produces: `looks_like_question(text: str) -> bool` in `stash.filing.question_shape`: true when the stripped text contains `?`, or starts with `?`, or its first word (lower-cased, punctuation stripped) is one of `WH_WORDS = ("what", "which", "who", "whom", "when", "where", "why", "how", "should")`, or it starts with `show me`. Imperatives such as find, tell, list, read are not question shapes.
- Consumes: `Filing.without_request() -> Filing` (turns `Route.REQUEST` into `Route.UNSURE`).

- [ ] **Step 1: Write the failing tests** with the scripted model in `tests/filing_rig.py` returning route `request`: `test_a_request_with_a_question_mark_stays_a_request` ("what can I do Saturday afternoon?"), `test_a_request_starting_with_a_question_word_stays_a_request` ("What should I do this weekend"), `test_a_request_without_a_question_shape_becomes_unsure` ("finished Tidewater Notes last night, loved the ending"), `test_a_trigger_word_alone_does_not_make_a_request` ("Wi-Fi at the cabin: network PineView, ask the host for the password"), and unit tests for `looks_like_question` covering each rule and `show me`.
- [ ] **Step 2: Run them** (`uv run pytest tests/acceptance/test_filing.py tests/unit/filing -q`); expect failures.
- [ ] **Step 3: Implement `looks_like_question` and apply it in `Filer.file` and `Filer.file_image`** after `parse_filing`: `request` plus no question shape returns `filing.without_request()`. The prompt is not touched.
- [ ] **Step 4: Update the eval expectations** for r03, r06, r07, r08, r09, r18, r19 from `request` to `unsure` (they have no question shape; the commit message lists them), fix the case-count assertions, and add three held-out cases: a question with no `?` ("which restaurants have I saved"), a capture containing "tell" ("tell Sam about the ferry times"), a progress report without `?`.
- [ ] **Step 5: `make check`; then run `stash eval --providers ollama --thinking off` on the PC with the owner's OK** (GPU). Passed: zero capture-expected cases routed as `request`; r01, r02 still `request`. Record the route accuracy in `docs/adr/0004-local-model.md` (one line, same style as the 2026-11-21 lines).
- [ ] **Step 6: Commit** `fix: a request without a question shape is filed as unsure, never dropped (Plan 9 T3)`.

## T4: The route gate (conditional: only if T2 says PASS)

**Files:**
- Create: `src/stash/filing/route_scorer.py` (Protocol and value type), `src/stash/llm/systemone.py` (the adapter)
- Modify: `src/stash/filing/filer.py`, `src/stash/config/model.py` and its loader (`[llm.route_gate]`), `src/stash/app/build.py` (wiring), `deploy/stash.toml.example`, `docs/deploy/wsl-setup.md`, `src/stash/doctor_probes.py` (one probe line)
- Test: `tests/acceptance/test_filing.py`, `tests/unit/llm/test_systemone.py`, `tests/unit/config/test_loader_route_gate.py`, `tests/fakes/` (a scripted scorer)

**Interfaces:**
- Produces: `RouteProbabilities` (frozen dataclass: `capture: float`, `request: float`, `unsure: float`) and `RouteScorer` Protocol with `score(text: str) -> RouteProbabilities | None` (None means no usable score) in `stash.filing.route_scorer`; `SystemOneRouteScorer(base_url: str, model: str, client: httpx.Client)` in `stash.llm.systemone`; `RouteGateConfig(enabled: bool = False, base_url: str, model: str = "nimble", request_threshold: float)` with `request_threshold` taken from the T2 record, validated to (0, 1].
- Consumes: `looks_like_question` (T3), the GPU gate's `status(now)`.

- [ ] **Step 1: Failing tests.** The Filer with a scripted model saying `request`: `test_a_confident_request_without_a_question_shape_is_accepted` (scorer returns request 0.97 at threshold 0.9), `test_an_unconfident_request_without_a_question_shape_becomes_unsure` (0.6), `test_a_missing_score_falls_back_to_the_floor` (None), `test_a_busy_gpu_skips_the_scorer` (the scorer is not called). Adapter tests with `httpx.MockTransport`: a normal answer maps to `RouteProbabilities`; a 500, a timeout, probabilities `NaN`, negative or summing to 0, and a missing option all return `None`. Config test: the default is `enabled = False`, an unknown key and a threshold outside (0, 1] raise `ConfigError`.
- [ ] **Step 2: Run, expect failures; implement** the types, the adapter (one `choice` question `route`, the same option wording as T2's winning variant, `keep_alive` from config with a short default), the config table, the Filer step (floor first: question shape accepts; otherwise score; accept only at or above the threshold), the wiring in `stash.app` only, and the doctor line ("route gate: on, nimble reachable" or "off").
- [ ] **Step 3: `make check`; live check (OWNER, GPU free):** `stash eval` with the gate on and `base_url` at the system Ollama. Passed: the T2 numbers reproduce through the product path.
- [ ] **Step 4: Docs** (`wsl-setup.md`: the Ollama >= 0.35 upgrade is an owner step; the gate is off by default; the VRAM swap cost) and a Mac handoff entry. **Commit** `feat: an optional decision-model gate lets a confident request through (Plan 9 T4)`.

## Verification

- `make check` green after T3 and T4. Report `wc -l` for src and tests added (tests at most about 2x the source, rule R15).
- T3 live: zero capture-expected case routed as `request` in the eval; r01 and r02 still `request`.
- T2/T4 live: only with the owner present and the GPU free; both end with nothing loaded.

## Findings not planned

- Hosted Jev (no free tier, waitlist, US-hosted, undefined retention) and Laya (an encoder that needs fine-tuning and a new dependency) are not options for private notes.
- Moving item type and stage to a decision model, a duplicate check and tool-call gating are possible later uses; they wait for the route result.
