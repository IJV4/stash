# Thinking control and per-case eval output — implementation plan

> **For agentic workers:** Python is written as `CLAUDE.md` § "Writing Python" says for the
> machine you are on (Mac: the `python-development` orchestrator; PC/WSL: subagent-driven
> development with TDD). The main loop commits. Run with superpowers:subagent-driven-development.
> Steps use checkbox (`- [ ]`) syntax. Not a `plan-N` milestone plan: a follow-up from the
> 2026-11-04 Mac handoff (`docs/superpowers/notes/2026-11-04-mac-handoff.md` §3) and ADR 0004.

**Goal:** Let the owner switch model "thinking" off per LLM task from config, without
changing what any model receives by default. Let `stash eval` compare thinking on and off
and show each case's result next to the expected values, so the date failures (`t10`, `i02`)
can be debugged.

**Architecture:** `[llm.thinking]` sets a provider-neutral `Thinking` value per `LlmTask`
(`default` | `off`). Each provider adapter maps `off` to its own request field in
`OpenAICompatibleChat`. `default` sends no field. `ModelRouter.model_for(task, now)` returns a
model that carries that task's setting, including after a busy fallback to OpenRouter. The eval
gains `--thinking default,off`, which runs each target once per value and labels the runs
`<provider>:<model> thinking=<value>`. The report gains a per-case section.

**Tech Stack:** unchanged (no new dependencies).

**Spec:** `docs/superpowers/specs/2026-11-02-stash-design.md` (LLM providers: per-task override;
Local-model eval); `docs/adr/0004-local-model.md` (latency finding, eval baseline).

## Global Constraints

- **`default` sends nothing.** With no `[llm.thinking]` table, every request body is byte-for-byte
  what it is today. What a model *without* thinking does with the off field is unverified,
  so nothing is sent unless the owner asks.
- **Provider mapping for `off`.** The owner must not have to know the field names.
  - Ollama: `"reasoning_effort": "none"`. Verified only on Ollama 0.33.2 with `qwen3.5`
    (ADR 0004: 4.7 s → 0.2 s).
  - OpenRouter: `"reasoning": {"effort": "none"}`. This is taken from OpenRouter's request
    schema, read from the generated `openrouter` Python SDK 1.3.121
    (`ChatRequest.reasoning.effort`, Literal includes `"none"`). openrouter.ai is blocked on
    the Mac. Behaviour per model is unverified.
  - Each mapping gets a one-line comment in the code that says what was verified and on what
    version, and what the PC must check.
- **Results belong to one model.** A thinking on/off comparison holds only for the model it
  was measured on. Every eval run label names provider, model and thinking value. ADR 0004 says
  the comparison must be re-run when the chosen model changes.
- Config keys are the `LlmTask` values (`filing`, `suggestions`, `vision`). Values are `default`
  or `off`. Anything else is a `ConfigError` naming `llm.thinking.<task>`. An unknown key is a
  `ConfigError`, as in the rest of the loader.
- The setting applies to **stash's own LLM calls only**. Hermes's agent turns use Hermes's
  provider config. Say so in `deploy/stash.toml.example` and ADR 0004.
- Offline tests only (`httpx.MockTransport`); fake data only.

## Review Focus

1. **The busy fallback reroutes to OpenRouter.** With `filing = "off"` and Ollama busy, the
   OpenRouter request carries OpenRouter's field, not Ollama's.
2. **The vision model.** `vision_model` targets (`OpenAICompatibleChat(..., model=...)`) honour
   `[llm.thinking] vision`. They never pick up the filing setting by accident.
3. **No table, or `filing = "default"`.** The request JSON has no `reasoning_effort` and no
   `reasoning` key. Pin this with an exact-keys assertion, not "contains".
4. **`--thinking off` while the config says `default`.** The eval uses what the flag says. A
   run label never claims a value it did not send.
5. **Very long model output in the per-case report.** A got/expected cell is clipped (≤ 80
   chars, `collapse_and_clip`), and the error text stays within the existing `ERROR_LIMIT`.
   The report stays line-oriented (no embedded newlines from model output).

---

### Task 1: `Thinking` setting, per-provider mapping, routing

**Files:**
- Modify: `src/stash/config/model.py`, `src/stash/config/loader.py`,
  `src/stash/config/__init__.py`, `deploy/stash.toml.example`.
- Modify: `src/stash/llm/openai_compat.py`, `src/stash/llm/router.py`,
  `src/stash/app/providers.py`, `src/stash/app/build.py`.
- Test: `tests/unit/config/test_loader_thinking.py`,
  `tests/contract/test_openai_compat_thinking.py`, `tests/unit/llm/test_router_thinking.py`,
  `tests/acceptance/test_provider_switching.py` (additions).

**Interfaces:**
- Produces:
  - `Thinking(StrEnum)`: `DEFAULT = "default"`, `OFF = "off"`, in `stash.config`.
  - `LlmConfig` gains `thinking: Mapping[LlmTask, Thinking]` (frozen through
    `MappingProxyType`, default empty) and `thinking_for(task) -> Thinking`.
  - `OpenAICompatibleChat(settings, client, model=None, thinking: Thinking = Thinking.DEFAULT)`.
  - `ModelRouter.model_for(task, now)` returns a model for `(provider_for(task) or the
    fallback, thinking_for(task))`. How the router gets those models is the implementer's
    choice, but it must be built once in the composition root and not per call.
  - `eval_targets(...)` keeps its signature for now. Task 2 changes it.
- [ ] **Step 1: Failing tests:**
  - Loader:
    - No table → every task is `DEFAULT`.
    - `filing = "off"` → `OFF`.
    - `filing = "maybe"` → `ConfigError` naming `llm.thinking.filing`.
    - `[llm.thinking] chat = "off"` → `ConfigError`.
    - The example file still loads.
  - Contract (MockTransport, both providers):
    - `DEFAULT` → the payload keys are exactly `{"model", "messages", "temperature",
      "response_format"}` (RF3).
    - `OFF` + Ollama → `payload["reasoning_effort"] == "none"`.
    - `OFF` + OpenRouter → `payload["reasoning"] == {"effort": "none"}`, with no
      `reasoning_effort`.
  - Router:
    - `model_for(FILING)` honours `thinking_for(FILING)`.
    - Busy + `busy_fallback = "openrouter"` → the OpenRouter field (RF1).
    - `VISION` with `filing = "off"` and no vision setting → no field (RF2).
  - Acceptance (`test_provider_switching.py`): an app built with `[llm.thinking] filing = "off"`
    files a message, and the captured Ollama request carries `reasoning_effort: "none"`.
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement. Put the provider → field mapping in one
  `UPPER_SNAKE` constant in `openai_compat.py`, with the verification comments from Global
  Constraints. **Step 4:** `make check`.
- [ ] **Step 5:** `deploy/stash.toml.example`: add a commented `[llm.thinking]` block
  (`# filing = "off"   # stash's own calls only; Hermes agent turns are configured in Hermes`).
- [ ] **Step 6: Commit** `feat(llm): per-task thinking control mapped per provider`.

### Task 2: Eval — thinking comparison and per-case output

**Files:**
- Modify: `src/stash/evaluation/{results,runner,report,expectation,target}.py`,
  `src/stash/cli/{parser,eval_command,dispatch}.py`, `src/stash/app/{providers,app,build}.py`.
- Modify docs: `docs/adr/0004-local-model.md`, `docs/spike-m0.md`, `docs/usage.md`
  (the "stash eval" section).
- Test: `tests/unit/evaluation/test_report_cases.py`,
  `tests/unit/evaluation/test_expectation_mismatches.py`,
  `tests/acceptance/test_cli_eval.py` (additions).

**Interfaces:**
- Consumes: `Thinking`, `OpenAICompatibleChat(..., thinking=...)` (Task 1).
- Produces:
  - `FieldMismatch(field: EvalField, expected: str, got: str)`.
  - `Expectation.mismatches(filing) -> tuple[FieldMismatch, ...]`, in `FIELD_ROWS` order. A
    missing value renders as `"none"`. For details, the expected and got values are the
    `key=value` pairs for the expected keys.
  - `CaseResult` gains `mismatches: tuple[FieldMismatch, ...] = ()`.
  - `EvalTarget` gains `thinking: Thinking`, and its label becomes
    `f"{provider}:{model} thinking={thinking}"`.
  - `app.eval_targets: Mapping[tuple[ProviderName, Thinking], EvalTarget]` covers both values
    for every configured provider. The CLI picks from it.
  - `stash eval --thinking default,off` (comma list of `Thinking` values; default: the
    configured `thinking_for(LlmTask.FILING)` only). Each chosen provider × thinking value is one
    run, in that order (RF4).
  - The report appends, per run, `### cases — <label>`, then one line per case in file order:
    - Pass: `"<case id> <arm> ok (<latency> s)"`.
    - Fail: `"<case id> <arm> FAIL <field>: want <expected> got <got>; … (<latency> s)"`.
    - Error: `"<case id> <arm> ERROR <error text> (<latency> s)"`.
    - Cells are clipped to 80 chars with `collapse_and_clip` (RF5).
- [ ] **Step 1: Failing tests:**
  - `mismatches` for a `t10`-shaped case (stage planned/want_to, date 2027-03-14/none).
  - Report lines for pass, fail and error.
  - A 2-KB model title is clipped, and newlines are collapsed.
  - Acceptance: `stash eval --providers ollama --thinking default,off` against a MockTransport.
    The report has two columns labelled `ollama:<model> thinking=default` and
    `… thinking=off`. The second run's requests carry `reasoning_effort: "none"` and the first
    run's do not. A `### cases` section lists `t10` with `want 2027-03-14`.
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement. **Step 4:** `make check`.
- [ ] **Step 5: Docs.**
  - ADR 0004: add a "Thinking control" section covering the mapping table and what is
    verified (Ollama 0.33.2 + qwen3.5 only), and that OpenRouter is schema-only. State that
    `default` sends nothing because a non-thinking model's reaction to the field is unknown, that
    results are per model (re-run on any model change), and that Hermes agent turns are not
    covered.
  - `docs/spike-m0.md`: add rows.
    - #19: `stash eval --providers ollama --thinking default,off`. Expected: compare scores and
      latency, look at `t10`/`i02` in the cases section, and record the result in ADR 0004.
    - #20: the OpenRouter `off` field accepted (no HTTP 400) and reasoning tokens drop, per
      candidate model.
    - #21: a non-thinking model (e.g. `gemma4:12b`) with `filing = "off"`: accepted or ignored,
      with no error.
  - `docs/usage.md`: describe `--thinking` and the cases section.
- [ ] **Step 6: Commit** `feat(eval): compare thinking on/off and print per-case results`.
