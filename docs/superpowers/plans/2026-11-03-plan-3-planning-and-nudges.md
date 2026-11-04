# stash Plan 3 — Planning and nudges (M3)

> **For agentic workers:** Python is written as `CLAUDE.md` § "Writing Python" says for the
> machine you are on (Mac: the `python-development` orchestrator; PC/WSL: subagent-driven
> development with TDD). The main loop commits.
> Build **after** the M0 spike — spike check #2 decides the tick mechanism (Task 6).
> Requires Plan 2. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Planned items get AI-proposed prep steps that the owner confirms.
Steps and dates produce reminders. There's a Sunday 10:00 digest, morning-after
follow-ups, and on-demand suggestions. Anything missed while the PC was off is
sent in one catch-up message when it starts. Backup health shows up in `doctor`.

**Architecture:**
- `Step` value objects and a `sent_nudges` ledger (migration `0003`).
- A pure `stash.nudges` feature: `Nudger.due(now)` returns the nudges that are
  due, and `mark_sent` records them, so nothing is sent twice.
- `stash.planning` for step proposals and `stash.suggestions` for picks and
  digest suggestions. Both are LLM features on `LlmTask.SUGGESTIONS` and follow
  the filer's schema/prompt/parse pattern.
- `stash tick`, triggered every minute by a Hermes cron job with no agent (spike #2), sends
  through the Telegram Bot API itself so nudges keep their buttons (amended 2026-11-04).

**Tech Stack:** unchanged (no new dependencies).

**Spec:** `docs/superpowers/specs/2026-11-02-stash-design.md` (Steps, Nudges,
Backups); `docs/spike-m0.md` #2.

## Global Constraints

- Plan 1/2 Global Constraints apply.
- **Default times (builder calls; configurable under a new `[nudges]` TOML section):**

  | Key | Default | Meaning |
  |---|---|---|
  | `digest_day` | `"sunday"` | Day the weekly digest goes out |
  | `digest_time` | `"10:00"` | Time of the weekly digest |
  | `reminder_time` | `"09:00"` | Day-of reminders, and the time a step with only a lead time is due |
  | `followup_time` | `"09:00"` | Morning-after follow-ups |
  | `forgotten_after_days` | `30` | Want-to items older than this count as forgotten |
  | `stuck_doing_days` | `21` | Doing items older than this count as stuck |
  | `tick_seconds` | `60` | How often the tick runs |

  All times are in `StashConfig.timezone`. Unknown keys are rejected, as in Plan 1.
- **Noise rules (spec):**
  - At most **one follow-up message per day** (items batched).
  - Never ask twice about the same item. Skip items that already have an outcome.
  - Catch-up is **one** batched message, not a flood.
- **Exactly-once-ish:** a nudge is marked sent only after the outbox send
  succeeds. The `(kind, subject_id, due_at)` key is unique, so a crash between
  send and mark at worst repeats one message.
- Unconfirmed proposed steps never produce reminders.
- LLM unavailable or deferred:
  - Step proposals are postponed (retried on the next tick).
  - The digest goes out **without** its suggestions section, rather than late.

## Review Focus

1. **PC off over a digest time and several reminders.** On start, exactly one
   catch-up message lists everything missed (the digest included). Nothing is
   sent twice on the next tick.
2. **DST transitions in America/Los_Angeles** (e.g. 2027-03-14, 2027-11-07):
   reminders at 09:00 local fire once, at the right instant.
3. **Item date edited or item dropped after reminders were scheduled.** Stale
   nudges are not sent, and steps re-derive their due times.
4. **Telegram send fails.** The nudge stays unsent and is retried on the next
   tick. Ticks never overlap.
5. **Hostile or oversized LLM step proposals** (50 steps, 2-KB step text, lead
   times like "-3 days" or "in 400 days") are clamped to ≤ 10 steps of ≤ 200
   chars, with lead times of 0–60 days.

---

### Task 1: Domain — Step, nudge kinds; migration 0003

**Files:** Create `src/stash/domain/step.py`, `src/stash/domain/nudge.py`,
`src/stash/store/migrations/0003_steps_nudges.sql`.
Modify `store/port.py`, `sqlite.py`, `_rows.py`, `tests/fakes/memory_store.py`,
`tests/builders.py`.
Tests: `tests/unit/domain/test_step.py`, `tests/unit/domain/test_nudge.py`,
`tests/contract/test_store_steps_contract.py`,
`tests/contract/test_store_nudge_ledger_contract.py`,
`tests/integration/test_sqlite_migration_0003.py`.

**Interfaces:**
- Produces:
  - `Step(id, item_id, text: str, lead_days: int | None, due_on: date | None,
    confirmed: bool, done: bool, position: int, created_at: datetime)`.
    - Validation: exactly one of `lead_days` (0–60) or `due_on`; text 1–200 chars.
    - Methods: `due_date(item_date: date | None) -> date | None`,
      `confirmed_now() -> Step`, `marked_done() -> Step`.
  - `Item.rescheduled(date: date | None, now) -> Item`: clearing the date of a
    PLANNED item moves it to WANT_TO. Used by "Didn't happen" and by agent date
    edits (Review Focus 3).
  - `NudgeKind(StrEnum)`: `STEP="step"`, `ITEM_DATE="item_date"`,
    `FOLLOWUP="followup"`, `DIGEST="digest"`, `STUCK="stuck"`
    (`PERSON_DATE` is added by Plan 4).
  - `Nudge(kind: NudgeKind, subject_id: str, due_at: datetime, title: str)`,
    with `key -> tuple[str, str, str]`.
- SQL:
  - `steps` table (FK `item_id` with ON DELETE CASCADE).
  - `sent_nudges(kind, subject_id, due_at, sent_at)` with a UNIQUE key on
    `(kind, subject_id, due_at)`.
- `StepStore`: `save_steps(item_id, steps: Sequence[Step])` (replaces the
  item's steps), `steps_for(item_id)`, `save_step(step)`, `get_step(step_id)`,
  `open_confirmed_steps() -> list[Step]`.
- `NudgeLedger`: `was_sent(key) -> bool`, `record_sent(nudge, sent_at)`
  (idempotent), `last_sent(kind) -> datetime | None`.
- Item queries needed by the nudger, added to `ItemStore`:
  - `items_dated_between(start, end)`
  - `planned_without_outcome_dated_between(start, end)`
  - `want_to_older_than(cutoff: datetime, limit)`
  - `doing_older_than(cutoff, limit)`
  - `created_between(start, end)`
- [ ] **Step 1: Failing tests:**
  - Step validation, plus `due_date` for a lead time vs an absolute date.
  - Contract tests on both stores for each method.
  - The ledger's uniqueness: recording the same key twice leaves one row.
  - A 0002 database migrates to 0003 intact.
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement. **Step 4:** `make check`.
- [ ] **Step 5: Commit** `feat(store): steps and sent-nudge ledger (migration 0003)`.

### Task 2: Config — `[nudges]`

**Files:** Modify `src/stash/config/model.py`, `config/loader.py`,
`deploy/stash.toml.example`, `tests/config_builders.py`.
Tests: `tests/unit/config/test_loader_nudges.py`.

**Interfaces:** `NudgeConfig(digest_day: Weekday, digest_time: time,
reminder_time: time, followup_time: time, forgotten_after_days: int,
stuck_doing_days: int, tick_seconds: int)`, using the defaults in Global
Constraints. `StashConfig.nudges: NudgeConfig`.
- [ ] **Step 1: Failing tests:**
  - Missing section → defaults.
  - `digest_time="25:00"` → `ConfigError` naming `nudges.digest_time`.
  - `digest_day="funday"` → `ConfigError`.
  - Unknown key → `ConfigError`.
  - The example file loads.
- [ ] **Step 2–4:** Implement; `make check`. **Step 5: Commit** `feat(config): nudge schedule settings`.

### Task 3: `stash.planning` — AI-proposed prep steps (confirm first)

**Files:** Create `src/stash/planning/{__init__,schema,prompt,parse,proposer,service}.py`.
Tests: `tests/unit/planning/*`, `tests/acceptance/test_planning.py`.

**Interfaces:**
- Consumes: `FilingModelSource`-style `model_for(LlmTask.SUGGESTIONS, now)`,
  `ChatModel.complete_json`, `StepStore`, `Item`.
- Produces:
  - `STEPS_SCHEMA`: `{"steps": [{"text", "lead_days"}]}`, strict.
  - `build_step_messages(item, today) -> list[ChatMessage]`. The item is wrapped
    in `<item>` data tags with the same escaping as the filer.
  - `parse_steps(raw) -> tuple[ProposedStep, ...]` never raises and clamps per
    Review Focus 5.
  - `StepProposer(models, clock).propose(item) -> tuple[ProposedStep, ...]`.
    It propagates `LlmUnavailable`/`LlmDeferred`; `LlmBadOutput` → `()`.
  - `Planning(store, proposer, new_id, clock)`:
    - `propose_for(item_id) -> Proposal(item, steps: tuple[Step, ...])` saves
      the steps **unconfirmed**.
    - `confirm_all(item_id) -> tuple[Step, ...]`, `discard(item_id) -> None`.
    - `add_step(item_id, text, lead_days | due_on) -> Step` (confirmed; used by
      the agent).
    - `edit_step(step_id, text?, lead_days?, due_on?)`, `complete_step(step_id) -> Step`.
  - `needs_proposal(item) -> bool`: true for a PLANNED item with a date and no
    steps.
  - Callback kinds, added to `stash.capture.callbacks.FixKind`:
    - `ACCEPT_STEPS="a"` (subject item id)
    - `SKIP_STEPS="n"` (subject item id)
    - `STEP_DONE="x"` (subject step id)
  - `proposal_reply(proposal, item_date) -> Reply`:
    - Text: `"🗓 Prep for {title} ({date:%a %b %-d}):"` followed by lines
      `"• {text} — {when}"`, where `when` is `"same day"`, `"N days before"` or
      an absolute date.
    - Buttons: `[["Looks good ✓", "No steps"]]`, with the footer
      `"Tell me changes any time."`.
- [ ] **Step 1: Failing acceptance tests** (usage doc section "Planning ahead"):
  - A date night planned for 2027-02-12 → the proposal lists ≤ 10 steps, all
    unconfirmed.
  - "Looks good ✓" confirms them.
  - "No steps" deletes them.
  - An LLM outage → no proposal, item unchanged; the next attempt succeeds.
- [ ] **Step 2:** Unit tests for clamping and prompt delimiting.
  **Step 3–4:** Implement; extend the architecture guard (`stash.planning` is a
  feature, like `stash.filing`). `make check`.
- [ ] **Step 5: Commit** `feat(planning): AI-proposed prep steps with owner confirmation`.

### Task 4: `stash.nudges` — what is due, catch-up batching, rendering

**Files:** Create `src/stash/nudges/{__init__,schedule,nudger,messages}.py`.
Tests: `tests/unit/nudges/*`, `tests/acceptance/test_nudges.py`.

**Interfaces:**
- Produces:
  - `Schedule(config: NudgeConfig, timezone: ZoneInfo)`:
    - `at_local(day: date, t: time) -> datetime` (aware UTC, DST-correct).
    - `digest_instants_between(start, end) -> list[datetime]`.
  - `Nudger(store: NudgeStore, schedule, clock)`:
    - `due(now) -> list[Nudge]`. It returns every nudge with
      `due_at ≤ now`, not sent, and still valid. The validity checks re-read
      the item and step (Review Focus 3).
      - STEP: confirmed, not done; `due_date` at `reminder_time`.
      - ITEM_DATE: PLANNED item, at `reminder_time` on its date.
      - FOLLOWUP: PLANNED item with no outcome, at `followup_time` the day after
        its date.
      - STUCK: Doing items older than `stuck_doing_days`. These go only into the
        digest (never a separate message).
      - DIGEST: the most recent digest instant ≤ now that has not been sent.
      - Lookback window: 14 days (anything older is dropped silently, builder call).
    - `mark_sent(nudges, sent_at) -> None`.
  - `NudgeBatch`: groups due nudges into messages for one tick. Rules, in order:
    1. The digest is its own message.
    2. Follow-ups are one message per day.
    3. Step and item-date reminders are one message.
    4. If more than one kind is due and the oldest `due_at` is > 30 min before
       `now`, it is a **catch-up**: one message headed
       `"While I was offline:"` (Review Focus 1).
  - `messages.render(batch_part, ...) -> Reply`:
    - Step reminder lines: `"⏰ {step text} — for {item title} ({date})"`, with a
      `"Done ✓"` button per step (`stash:x:<step_id>`; at most 8 buttons, then
      text-only).
    - Follow-up: `"How was {title}?"` with the Plan 2 rating and "Didn't happen"
      buttons. "Didn't happen" is a new `FixKind NOT_HAPPENED="h"`; it moves the
      item back to WANT_TO and clears its date.
- [ ] **Step 1: Failing tests:**
  - **Clock-driven acceptance:** a scripted week of instants. A step due
    Saturday 09:00 fires once. A follow-up fires Sunday 09:00 after a Saturday
    date night. The digest fires Sunday 10:00. Ticks every 60 s produce no
    duplicates.
  - **PC off Fri 18:00 → Sun 12:00:** one catch-up message containing the step,
    the follow-up and the digest (RF1).
  - **DST:** the 2027-03-14 and 2027-11-07 instants (RF2).
  - **Staleness:** dropping the item before 09:00 → no reminder (RF3).
- [ ] **Step 2–4:** Implement; `make check`.
- [ ] **Step 5: Commit** `feat(nudges): due-nudge computation, catch-up batching and messages`.

### Task 5: Digest and suggestions

**Files:** Create `src/stash/suggestions/{__init__,schema,prompt,parse,engine}.py`,
`src/stash/nudges/digest.py`.
Tests: `tests/unit/suggestions/*`, `tests/unit/nudges/test_digest.py`,
`tests/acceptance/test_digest.py`.

**Interfaces:**
- `SuggestionEngine(models, clock).pick(candidates: Sequence[Item], context: str,
  limit: int = 3) -> tuple[Suggestion, ...]`.
  - `Suggestion(item_id, reason ≤ 200 chars)`.
  - Only ids from `candidates` are accepted; others are dropped.
  - Propagates `LlmUnavailable`.
- `DigestBuilder(store, engine, schedule, clock).build(now) -> Digest`, with sections:
  - new this week
  - forgotten (≤ 3, oldest first, not in the last 4 digests; tracked via the
    ledger subject `digest-forgotten:<item_id>`)
  - upcoming 14 days (item dates and confirmed steps; people dates are added in Plan 4)
  - how did it go (stuck Doing)
  - suggestions (≤ 3; the section is omitted on an LLM failure)
- `render_digest(digest) -> Reply`: ≤ 4096 chars; each section is capped with
  "…and N more".
- On demand: the agent tool `stash_suggest {context}` and the command
  `/suggest [context]` both call `engine.pick(want_to items ≤ 40, context)` and
  return reasons.
- [ ] **Step 1: Failing tests:**
  - A digest with every section.
  - A suggestions failure → the digest without its suggestions section.
  - A forgotten item does not repeat within 4 weeks.
  - An unknown id returned by the LLM is dropped.
  - `/suggest "2h free Saturday, at home"` returns at most 3 lines.
- [ ] **Step 2–4:** Implement; `make check`.
- [ ] **Step 5: Commit** `feat(suggestions): weekly digest and on-demand picks`.

### Task 6: `stash tick` (Hermes cron, no agent) + direct Bot API delivery + proposals on plan

> **Amended 2026-11-04 (owner-approved, replaces the in-process Ticker).** Spike #2 proved Hermes
> cron `--no-agent --script` runs code without an LLM turn, but its stdout delivery has no buttons
> and adds a "Cronjob Response" header/footer. So cron only **triggers** `stash tick`; stash sends
> the messages itself through the Telegram Bot API, with buttons. Taps come back through Hermes's
> gateway to stash's existing `CallbackQueryHandler` (pattern `^stash:`), because Telegram delivers
> callback queries to whoever polls the bot token. **Unverified, PC must check (spike #22):** a tap
> on a message stash sent directly reaches that handler; the cron job runs with the Hermes env
> (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_ALLOWED_USERS`); a script that prints nothing sends nothing.

**Files:**
- Create `src/stash/tick/{__init__,runner,ports}.py` (feature) and
  `src/stash/telegram_api/{__init__,sender}.py` (adapter, httpx).
- Modify `src/stash/cli/*` (`tick` command), `src/stash/app/*` (wire Planning, Nudger,
  DigestBuilder, SuggestionEngine, BotApiSender, TickRunner), `src/stash/store/backup.py` and the
  doctor checks (`backup` line), architecture guard.
- Add `deploy/hermes-scripts/stash_tick.sh` (runs `stash tick` from the repo venv; copied into
  `~/.hermes/scripts/` by the deploy doc).
- Tests: `tests/unit/tick/test_runner.py`, `tests/contract/test_bot_api_sender.py`
  (MockTransport), `tests/acceptance/test_cli_tick.py`.

**Interfaces:**
- `NudgeSender(Protocol)` in `stash.tick.ports`: `send(chat_id: str, reply: Reply) -> None`
  (sync; raises `SendFailed` on any failure).
- `BotApiSender(token: str, client: httpx.Client)`: `POST https://api.telegram.org/bot<token>/sendMessage`
  with `chat_id`, `text` and, when the reply has buttons,
  `reply_markup = {"inline_keyboard": [[{"text", "callback_data"}, …], …]}` (the same layout
  `hermes_adapter.telegram_io.to_keyboard` builds). HTTP error, `{"ok": false}`, or a network
  error → `SendFailed`. **The token is part of the URL: it must never appear in a log line,
  exception text or `repr`** (redact like `llm.openai_compat._Failures`).
- `TickRunner(nudger, batcher, digest, renderer, planning, sender: NudgeSender, owner_chat: str, lock)`:
  `run_once(now) -> TickReport(sent: int, failed: int, proposals: int)`. One tick runs `due` →
  batch → send each message → `mark_sent` only for messages that were sent (RF4). Then
  `planning.propose_for` for ≤ 3 items where `needs_proposal` is true, each sent as a
  `proposal_reply`. A proposal that cannot be sent is discarded, so the next tick proposes again.
- Ticks never overlap: `lock` is an exclusive non-blocking file lock on `data_dir/tick.lock`
  (`fcntl.flock`). If the lock is held, `run_once` returns at once with nothing sent.
- The owner chat is the first id in `TELEGRAM_ALLOWED_USERS` (a Telegram DM chat id == user id).
  A missing `TELEGRAM_BOT_TOKEN` or owner → `stash tick` exits 2 with a message naming the variable.
- `stash tick [--dry-run]`: it prints nothing on success (so a cron job never posts output) and
  writes a one-line summary to stderr. `--dry-run` prints the rendered messages to stdout and sends
  and marks nothing.
- Hermes job (documented, not run here):
  `hermes cron create "every 1m" --no-agent --script stash_tick.sh`. Use **no `--deliver`**
  unless the PC shows it is required. If it is, deliver to `telegram:<owner id>` and rely on
  the empty output.
- `doctor` gains a `backup` line: OK if the last successful `stash backup` is
  < 48 h old. `Backups.write` records the setting `backup.last_success`.
- [ ] **Step 1: Failing tests:**
  - The runner sends the catch-up once and then nothing.
  - A send failure leaves the nudge unsent, and the next tick sends it.
  - A held lock → nothing sent.
  - `stash tick --dry-run` marks nothing.
  - The sender's request body is `inline_keyboard` with `stash:` callback data ≤ 64 bytes.
  - `{"ok": false}` → `SendFailed`, and the token is absent from the exception text and the
    captured logs.
  - doctor shows `! backup — last success 3 days ago`.
- [ ] **Step 2–4:** Implement; extend the architecture guard for the new packages
  (`tick`, planning, nudges and suggestions are features; `telegram_api` is an adapter that only
  `stash.app` imports); `make check`.
- [ ] **Step 5:** Update the docs:
  - `docs/usage.md`: "Planning ahead", "Reminders", "Weekly digest", "Suggestions".
  - `docs/deploy/wsl-setup.md`: the cron job, the script, and the env it needs.
  - `docs/spike-m0.md`: #22 covers the direct-sent buttons reaching the handler, the cron env,
    and the empty-output behaviour.
- [ ] **Step 6: Commit** `feat: reminders, digest and follow-ups sent by stash tick`.

### Task 7: Purchase cool-off (spec: optional, off by default)

**Files:** Modify `src/stash/domain/item.py` (`cool_off_until: date | None`), migration `0003` (column `cool_off_until TEXT`; this task lands in the same migration as Task 1 — do not add a separate file), `config` (`[nudges] purchase_cool_off_days = 0` — 0 disables), `src/stash/capture/pipeline.py` (set it for new PURCHASE items when enabled), `src/stash/nudges/*` (`NudgeKind.COOL_OFF`), `capture/callbacks.py` (`FixKind STILL_WANT="w"`); Tests unit + `tests/acceptance/test_cool_off.py`.

**Interfaces:** when enabled, a new PURCHASE item gets `cool_off_until = today + N days`; at `reminder_time` that day the ticker asks `"🛒 Still want {title}?"` with buttons `["Yes, keep it" (stash:w:<id>:1), "Drop it" (stash:w:<id>:0)]`; "Drop it" → `Lifecycle.drop(item_id, "cool-off")`; the digest's suggestions never pick an item still cooling off.
- [ ] **Step 1: Failing tests:** disabled by default (no field set, no nudge); enabled with 14 days → nudge on day 14 once; "Drop it" drops with reason "cool-off".
- [ ] **Step 2–4:** Implement; `make check`. **Step 5: Commit** `feat(nudges): optional cool-off for purchases`.
