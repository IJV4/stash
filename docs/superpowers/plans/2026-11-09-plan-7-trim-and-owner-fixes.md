# Plan 7: trim and owner fixes

## Context
About 100 deferred or parked items had built up: the SDD ledgers, the whole-branch review, the
clean-up and the PC spike list. The owner asked, for each one, whether it is really needed and
whether it is a chance to simplify the code, the architecture or performance, and then for a plan
of the most important ones.

**How the plan was built:**
- Three read-only explorers triaged every item against `main` (405e4e9), and a plan agent checked
  the task design against the architecture tests.
- A second review used the mattpocock skills (codebase-design, tdd, grilling, domain-modeling,
  writing-for-agents). It narrowed T4 and T6, dropped the digest cache, and set the test seams.

**Result.**
- Most items close without code (see *Reference*, used only by T10).
- Four owner-facing faults get fixed, item edits get one write path, and the unused LAN server goes.
- Baseline: src 14.2k lines, tests 47.0k. Expected: about −490 src and −1,300 test lines.

## Decisions (owner, 2026-11-09)
1. **Deferral replies.** They say what is true, with no automatic retry. They name `/stash_retry`,
   the name the PC saw, because Hermes refuses `/retry`.
2. **Delete `stash serve`.** Amend the spec and record ADR 0006.
3. **Scope.** Fixes plus core simplification. The digest model-call cache is dropped (closed
   together with R17). T6 is the length measure only. T4 keeps `IntakeSteps` and `FixApplier`. T8
   also covers answers whose steps all fail validation.
4. **Three orchestrator groups**, still one commit per task.
5. **Test seams** as written in each task.

Builder-level calls already made:
- Mirrored networking stays on the PC; it has been set since `wsl-setup.md` §1.
- The double-tap window stays in `CompletionButtons`.
- `BusyFallback` stays a Literal (R15: nothing beyond the brief).
- The PC teardown is a conditional note in `wsl-setup.md`. The PC very likely never ran serve:
  serve landed 2026-11-07, the last pc-m0 commit is 2026-11-04, and `[library]` is commented out
  in the example.

## Process
- **Start.** Create branch `plan-7` from `main`. Its first commit is this plan, as
  `docs/superpowers/plans/2026-11-09-plan-7-trim-and-owner-fixes.md`.
- **Before each group.** Run `git log --oneline main..pc-m0`; merge per CLAUDE.md if it moved.
- **Groups.**
  - G1 = T1, T2.
  - G2 = T3, T4, T5.
  - G3 = T6, T7, T8, T9.
  - Each group runs under one sonnet `python-development:python-coding-orchestrator`.
  - Each orchestrator receives only its group's tasks, this Process section, and pointers to
    CLAUDE.md and the spec.
- **Inside a group, per task:**
  - Red → green in vertical slices, tests only at the task's agreed seam.
  - One critique round with ≤3 reviewers, then one sonnet task review.
  - The main loop commits the task with `make check` green.
- **Refactor tasks** (T2–T5) add only pin tests, written first and green on `main`. Old tests are
  deleted only when they test deleted code, with `make coverage` as the evidence.
- **Finish.** After G3: one opus plan-level review and one fix wave, then T10. Merging to `main`
  is the owner's call.
- **Minors** go to the plan ledger, never into a later task.

## G1

### T1 — FaultyStore refuses unknown method names
- **Change.** In `tests/fakes/faulty_store.py::FaultyStore`, every key of `fail_on` and
  `fail_once`, and every name given to `fail_next`, must be a public member of
  `stash.store.port.Store`. Otherwise raise `ValueError` naming the key.
- **Seam.** The `FaultyStore` constructor and `fail_next`: one sentence-named test, added to the
  existing `tests/unit/test_faulty_store.py`.
- **Done when.** A misspelled name raises, every existing use still passes, and `make check` is
  green.

### T2 — Delete `stash serve`; ADR 0006
- **Delete modules:** `stash.library_server`, `stash.library_access`, `stash.library_server_probe`
  and `stash.config.library`.
- **Remove their wiring:**
  - `stash.app`: `library_servers`, `serve_only_library_page` and `library_server`.
    `app/library.py` keeps `library_copy_path` and its constants.
  - `app/build.py` and the library-server check in `app/doctor_checks.py`.
  - The `[library]` table in `stash.config`: model, loader and exports.
  - The CLI `serve` command: parser, dispatch, and the command with `TOKEN_PLACEHOLDER`.
- **Store.** Remove `Store.read_snapshot`, `ReadSnapshotStore`, and from `store/_transaction.py`
  `read_snapshot`, `_is_busy_or_locked`, `_BUSY_OR_LOCKED` and `_LOCKED_MESSAGE`. Nothing else uses
  them; `_BUSY` stays.
- **`hermes_adapter/library_file.py`.** The too-big text points at the copy kept on the PC, which
  is written before the size check, instead of the home network.
- **Tests.** Delete the tests and rigs of the deleted code; find them with
  `grep -rln "library_server\|library_access\|read_snapshot\|LIBRARY_TOKEN\|socket_permission\|serve" tests`.
  Adjust `tests/architecture_guard.py`, the library rows in `tests/unit/test_architecture.py`,
  `cli_rig.py`, `app_builders.py` and `test_cli_doctor.py`. The existing `/library html` and
  `--html` acceptance tests pin what remains.
- **Docs:**
  - Spec: drop the LAN server from the diagram and the mirrored note. "Served on the home LAN"
    becomes "sent on `/library` and kept on the PC". M6 becomes "Telegram file". Drop "LAN server
    port" from the open choices. The NAS "home LAN" line stays.
  - `docs/adr/0006-no-lan-library-server.md`: one paragraph on why the Telegram file replaces
    the server, plus the rejected option. Add its row in `docs/adr/README.md`.
  - `docs/deploy/wsl-setup.md`: delete the serve section and renumber. Add a three-line
    conditional note: "If you set up `stash serve` from an earlier version: disable
    `stash-serve.service`, delete `serve.env`, remove both firewall rules and any `[library]`
    table (stash refuses unknown config tables)." Reword §1's reason for mirrored mode, keeping the
    setting. Update the comment in `deploy/windows/wslconfig.example`.
  - Delete `deploy/systemd/stash-serve.service` and the `[library]` block in
    `deploy/stash.toml.example`. Remove the serve lines in `docs/usage.md`.
  - `docs/spike-m0.md`: delete row #28; row #27 expects the new too-big text.
- **Done when.**
  - The serve names grep is empty outside `docs/superpowers` and the ADR:
    `grep -rn "library_server\|library_access\|read_snapshot\|LIBRARY_TOKEN\|stash serve\|stash-serve" src tests docs deploy`.
  - `stash --help` lists no `serve`.
  - `make coverage` shows no surviving src line or branch lost coverage.
  - `make check` is green.

## G2

### T3 — Dead code
- **Reopen.** Delete `Lifecycle.reopen` and `Item.reopened`: there is no caller, and
  `set_stage(want_to)` on a done item gives the same item. Reword the comment in `Item.kept_as`.
  Delete the reopen tests. Contract tests that build a reopened item use
  `done.relocated_to(Stage.WANT_TO, t)`.
- **People store.** Delete `Store.unlink` and `Store.delete_key_date`: port, `SqliteStore`,
  `store/_people.py`, the `store/_sql.py` constants, and their contract tests.
- **`stash.people.Resolution`.** `PeopleDirectory.resolve()` returns `tuple[Person, ...]`; delete
  `people/results.py`.
- **Small duplicates.**
  - `_nothing()` in `hermes_adapter/plugin.py` and `telegram_link.py`: pass `lambda: None` inline.
  - `config/loader.py::_PerTask`: reuse `config/_section.py::_Choice`.
- **Done when.** These names are absent from src, `make coverage` shows no loss, and `make check`
  is green.

### T4 — Protocols only at real seams
- **Remove** the single-adapter Protocols:
  - `planning.ports.ProposalDeclines`: callers take `Declines`.
  - `suggestions.ports.PickDesk`: `QuietPicks` takes `SuggestionDesk`.
  - The store sub-Protocols `CaptureStore`, `OutcomeStore`, `StepStore`, `PeopleStore` and
    `NudgeLedger`: inline their methods into `Store` and drop the exports.
- **Keep:**
  - `IntakeSteps` (4 adapters) and `FixApplier` (2 adapters): real seams.
  - `capture.ports`: the layering forbids the concrete imports.
  - `library_html`'s `LibrarySource`.
  - `ItemStore` and `SettingsStore`: they have narrow consumers.
- **Helpers.** Move the `require_*` and `find_named` helpers from `store/port.py` into a new
  store-private `store/_checks.py`, with its architecture row like the other private store
  modules. Repoint their tests, and delete the ones the contract tests already cover (coverage
  evidence).
- **Duplicate store argument.** `DigestBuilder(store, picks, schedule)` and
  `_Upcoming(store, schedule)` drop the duplicate `people: Store` parameter; update app build and
  the digest test builders and rigs.
- **Done when.** The removed names are absent from src and tests, `mypy --strict` and
  `make check` are green, and no tests were added.

### T5 — Button edits go through Lifecycle
- **Lifecycle.** Add `Lifecycle.retype(item_id, item_type)` (`_changed` with `Item.retyped`).
  Add `set_stage` and `retype` to `capture.ports.LifecycleActions`.
- **`FixHandler._move`.** Keep the pre-read and the `stage_menu` answer for an unknown or refused
  stage. Then call
  `lifecycle.set_stage(item.id, stage, item.drop_reason if stage is Stage.DROPPED else None)`.
- **`FixHandler._retype`.** Call `lifecycle.retype`.
- **Errors.** Both answer through the error mapping of `CompletionButtons._answering`, lifted to a
  module function in `capture/completion_buttons.py`. That is the capture module the
  architecture test lets import lifecycle errors.
- **Delete** `FixHandler._replaced` and the `_clock` field. The `clock` parameter still feeds
  `CompletionButtons`.
- **Seam.** A button press through the Hermes button rig / `FixHandler.apply`.
  - **Pin first** (green on `main`): re-pressing Dropped keeps the drop reason; Type and Stage
    edits answer the same replies. Only add the ones not already pinned.
  - Then refactor. `test_capture_requests_and_fixes`, `test_hermes_buttons` and `test_fixes_*`
    stay green unchanged.
- **Done when.** `capture/fixes.py` has no `update_item` call, the pin tests are green before and
  after, and `make check` is green.

## G3

### T6 — Telegram length in UTF-16 units
- **Measure.** Add `telegram_length(text)` beside `TELEGRAM_TEXT_LIMIT` in `capture/replies.py`
  as `len(text.encode("utf-16-le")) // 2`, and export it from `stash.capture`.
- **Callers.** Use it in all five length checks: `Reply.__post_init__`, `replies._within_limit`,
  `nudge_replies._fitting`, `digest_replies._fitted` and `hermes_adapter.commands._bounded`. Each
  keeps its own fitting policy. Callback data (bytes) and the `capture/agent.py` input limit stay
  as they are.
- **Seams.**
  - `telegram_length` as a wire-format unit.
  - `summary()`, `nudge_reply()` and the `/list` command.
  - Inputs and expected values are literals: `telegram_length("😀") == 2`, and a catch-up batch
    of emoji-titled reminders that is under 4096 code points but over 4096 units is trimmed to a
    literal N reminders.
- **Done when.** No `len(` is compared with `TELEGRAM_TEXT_LIMIT` (grep), and `make check` is
  green.

### T7 — Honest deferral reply
- **Enum.** `capture/results.py::DeferralReason` becomes a StrEnum with `GPU_BUSY`,
  `AI_UNAVAILABLE` and `UNEXPECTED`. `UNEXPECTED` replaces `UNEXPECTED_FAILURE_REASON` in
  `capture/agent.py`, `hermes_adapter/intake.py` and `capture/__init__`.
- **One reply.** `DEFERRED_TEXT = "📥 Saved, not filed yet. Send /stash_retry to file it."`
  replaces the per-reason map. The CLI's `deferred (<reason>)` line is unchanged.
- **Docs.**
  - `docs/usage.md`: the deferral paragraph and the command tables say `/stash_retry`.
  - Spec: "filing is retried later" becomes "captures stay saved; `/stash_retry` files them".
  - `docs/spike-m0.md`: row #6's expectation.
- **Seam.** Capture through the Hermes capture rig. GPU busy, AI down and a store fault each get
  the one reply, and `/stash_retry` then files the capture (add only what is not already pinned).
  Adjust the tests that assert the old texts.
- **Done when.** No "I'll file it" remains in src or docs, and `make check` is green.

### T8 — No "Nothing to prep" on a model fault
- **Definition.** An answer is unusable when it can't be parsed (`LlmBadOutput`), or when it
  listed steps and none survived validation (`parse_steps` then raises `LlmBadOutput`). A
  genuinely empty list still means "Nothing to prep" (R22).
- **Change.**
  - `planning/proposer.py` lets `LlmBadOutput` propagate.
  - `Planning.propose_for` catches it, logs a warning, records the decline under
    `store.writing()` (R7: no re-ask on every tick), and raises `ProposalUnusable(PlanningRefused)`.
  - `delivery/proposals.py` already sends nothing on `PlanningRefused`.
- **Seam.** `ProposalDelivery.deliver` with the fake LLM:
  - Unparseable output, and output whose steps all fail validation, send nothing.
  - The next tick sends nothing and makes no new model request; calls are counted at the fake
    LLM only.
  - Rewrite the proposer tests that pin "returns ()".
- **Done when.** These tests and R22's genuine-empty test are green, and `make check` is green.

### T9 — Untrusted model text through the printable rule
- **Filing.** `filing/parse.py` title and detail values use `printable_and_clip`
  (`domain/_validation.py`). `domain/item.py::derive_title` applies the printable replacement per
  line.
- **Rendering.** `rendering._preview` becomes `printable_and_clip(text, TEXT_PREVIEW_CHARS)`,
  with identical output. `rendering._clean` stays for rows stored before this change.
- **Eval.** In `evaluation/cases.py`, case ids pass `printable_and_clip` (new `CASE_ID_LIMIT`)
  before the duplicate check.
- **Seams.** Capture through the Hermes capture rig, plus `stash show`: control characters in a
  model title or details reach neither the reply nor `stash show`. The eval case loader: a case id
  with control characters loads clean.
- **Done when.** These tests are green, and `make check` is green.

## Main loop

### T10 — Close the ledger (docs only, after the opus review)
- Write `.superpowers/sdd/2026-11-09-plan-7-trim-and-owner-fixes/progress.md` (gitignored) with a
  "Closed deferred items" table: item | source ledger | fixed in Tn, or closed: reason. Build it
  from *Reference* below.
- Strike through the carries in `.superpowers/sdd/mac-dev-branch.md`, and update the memory note.
- **Done when.** Every item in *Reference* has a row.

## Verification
- `make check` is green after every task: format, ruff, `mypy --strict src tests/fakes`, default
  tests, then `-m integration`.
- `make coverage` runs before and after G1 and G2. No surviving src line or branch loses coverage.
- Each task's "Done when" greps come back clean, and `stash --help` and `stash doctor` show no
  serve.
- Report `wc -l` for src and tests before and after in the final summary.
- **Live (PC).**
  - Spike row #6: the new wording, and `/stash_retry` files a pending capture.
  - Row #27: the too-big text.
  - Row #15: the command names.
  - The conditional teardown note, applied only if the PC ever set up serve.

## Reference: closed without building (T10 only)
- **Fixed or unreachable:**
  - Reroute double-tap (fixes lock); `completed_on` future dates; `set_stage` lists done.
  - Naive-clock ungroup (aware clock); TITLE_LIMIT (titles only from `derive_title`); `with_facts`
    room (at most 3 facts).
  - Window > 1 yr (366-day cap); `NON_FORCING_TEXTS` and `record_sent` (gone); link facts already
    printable.
  - Reopen double tap (reopen goes in T3); names NFC (9b569e8); `test_atomic_write` (covered by
    acceptance).
- **By design and pinned:**
  - PC off all day loses that day's key-date reminder.
  - `record_all_sent` duplicate key → False.
  - The `latest.html` failure blocks the send.
  - The adapter reaches `Planning` via delivery.
- **Accepted like R17:**
  - First-run seeding builds the digest's picks: one model call per install.
  - An unsent digest rebuilds its picks every tick during a Telegram outage.
- **Latent or cosmetic at one-owner scale:**
  - Store: ROLLBACK masking; raw OperationalError across processes after 5 s.
  - Ticker and nudges: TickerLauncher flag (spike #26); last-4-digests slots; follow-up day
    boundary and "offline" heading; repeat items get no follow-up; lead > 14-day lookback; subject
    cap; > 30 s resend; GPU-busy log noise.
  - Doctor and config: BackupProbe on a malformed timestamp; `owner_chat_id` bool; `BusyFallback`
    Literal.
  - Planning and capture: proposal scan limit 200; `/suggest` catch; unshielded raw save; bursts
    log; stash_get cap; `rate()` re-read; `_last_finished` order; annotate error order;
    O(n²) `_fitting` (small batches).
  - People: `years_on` sign; `/people` cap; person notes.
  - Library: 45 MB per group; `%Z`; href tests; symlink and 0600; generic error line; `--html`
    flags.
  - Tests: `NUDGES_BLOCK_LINE_COUNT`; the withdraw log.
- **Closed by T2:** every `stash serve` item (slow-drip, query and cookie parsing, token load
  failure, probe client, HEAD body, `read_snapshot` lock).
- **Not cleanups (product features):** undo a repeat outcome; link facts in the confirmation.
  Plan 3 Task 7 and Plan 5 are unchanged.
- **PC-owned:** spike rows #19–#27, the PC `make check`, eval items, the handoff 25-45 s line, and
  the PTB write timeout (#27).
