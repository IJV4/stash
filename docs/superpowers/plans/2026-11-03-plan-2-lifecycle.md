# stash Plan 2 — Lifecycle: outcomes, library, repeats, groups (M2)

> **For agentic workers:** Python is written as `CLAUDE.md` § "Writing Python" says for the
> machine you are on (Mac: the `python-development` orchestrator; PC/WSL: subagent-driven
> development with TDD). The main loop commits.
> Build **after** the M0 spike (`docs/spike-m0.md`) unless the owner says otherwise.
> Steps use checkbox (`- [ ]`) syntax.

**Goal:** Items move through the full lifecycle: Done with an outcome
(date, rating, notes, takeaways, keep), repeats, Dropped with a reason, and
groups. A browsable library of kept items, reachable by buttons, agent tools,
`/library` and `stash library`.

**Architecture:** New domain value objects (`Outcome`), new item fields
(`kept`, `parent_id`, `drop_reason`), migration `0002`, a role Protocol
`OutcomeStore`, a feature package `stash.lifecycle` (pure, store-port only),
new callback kinds for quick Done/rating/keep, new agent tools for rich notes,
and thin CLI/Hermes entry points. Builds on Plan 1's interfaces as mapped on
2026-11-03 (see the interface notes in each task).

**Tech Stack:** unchanged from Plan 1 (no new dependencies).

**Spec:** `docs/superpowers/specs/2026-11-02-stash-design.md` (Data model:
Stages, Outcome, Groups; Browsing).

## Global Constraints

- All Plan 1 Global Constraints apply (offline suite, fake data, untrusted LLM
  output, ≤64-byte callback data, ≤4096-char messages, America/Los_Angeles).
- Every new store method: Protocol in `stash.store.port`, `MemoryStore`,
  `SqliteStore`, and an `@all_stores` contract test.
- Schema changes only via `src/stash/store/migrations/0002_lifecycle.sql`
  (never edit `0001`). Existing rows must load after migration.
- Rich text (notes, takeaways) arrives via the **agent** (tools), not via
  multi-step button dialogs. Buttons cover only the one-tap paths.
- Ratings are integers 1–5. Takeaways: ≤ 20 items, each ≤ 500 chars; notes ≤ 4000 chars.
- Groups are **one level deep** (a group's parent has no parent) — builder call.

## Review Focus

1. **Migration on a populated Plan-1 database** must keep every item and capture
   and give defaults (`kept=False`, `parent_id=NULL`, `drop_reason=NULL`).
2. **Completing an item twice** (double tap, repeat) creates two outcomes, never
   overwrites the first; the second tap of the *same* button message is a no-op.
3. **Grouping cycles / deep nesting / self-parent** are rejected with a clear
   message, not stored.
4. **Deleting or rerouting an item that has outcomes or children** (Plan 1's
   "That was a question →") must not leave orphans: outcomes cascade; children
   become ungrouped.
5. **Agent tool arguments** with wrong types, unknown ids, out-of-range ratings or
   oversized text return `{"error": …}` and change nothing.

---

### Task 1: Domain — Outcome, lifecycle fields, transitions

**Files:** Create `src/stash/domain/outcome.py`; Modify `src/stash/domain/item.py`,
`src/stash/domain/__init__.py`; Tests `tests/unit/domain/test_outcome.py`,
`tests/unit/domain/test_item_lifecycle.py`; Modify `tests/builders.py`
(`an_outcome`, item builder defaults).

**Interfaces:**
- Produces:
  - `Outcome(id: str, item_id: str, completed_on: date, rating: int | None,
    notes: str, takeaways: tuple[str, ...], recorded_at: datetime)` (frozen;
    wire-safe ids; rating 1–5 or None; limits above).
    `with_notes(notes, takeaways, now) -> Outcome` (append-only edit of the text).
  - `Item` gains `kept: bool = False`, `parent_id: str | None = None`,
    `drop_reason: str | None = None` (≤ 300 chars).
  - `Item.completed(now) -> Item` (stage DONE; allowed from any stage except DONE);
    `Item.reopened(now) -> Item` (DONE → WANT_TO, keeps `kept`);
    `Item.dropped(reason: str | None, now) -> Item`;
    `Item.kept_as(kept: bool, now) -> Item` (only DONE items may be kept → `ValueError` otherwise);
    `Item.grouped_under(parent: Item, now) -> Item` (rejects self, a parent that has a parent, or a parent that is itself a child of this item → `ValueError("groups are one level deep")`);
    `Item.ungrouped(now) -> Item`.
  - `MOVEABLE_STAGES` unchanged (DONE still reached only through `completed`).
- [ ] **Step 1: Failing tests:** each transition's happy path and each `ValueError`
  above; `Outcome(rating=0)` / `6` raise; 21 takeaways raise; `with_notes` keeps
  `id`, `completed_on`, `rating`; `reopened` on a non-DONE item raises.
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement. **Step 4:** `make check` green.
- [ ] **Step 5: Commit** `feat(domain): outcomes and lifecycle transitions`.

### Task 2: Store — migration 0002, OutcomeStore, library and group queries

**Files:** Create `src/stash/store/migrations/0002_lifecycle.sql`; Modify
`store/port.py`, `store/sqlite.py`, `store/_rows.py`, `tests/fakes/memory_store.py`;
Tests `tests/contract/test_store_outcomes_contract.py`,
`tests/contract/test_store_library_contract.py`,
`tests/integration/test_sqlite_migration_0002.py`.

**Interfaces:**
- Consumes: `Store`, `item_values/item_from_row`, `_UPSERT_ITEM` (store/sqlite.py), migrations runner (`_migrate.py`, contiguous numbering).
- Produces:
  - SQL: `ALTER TABLE items ADD COLUMN kept INTEGER NOT NULL DEFAULT 0`,
    `parent_id TEXT REFERENCES items(id) ON DELETE SET NULL`, `drop_reason TEXT`;
    `CREATE TABLE outcomes (id TEXT PRIMARY KEY, item_id TEXT NOT NULL REFERENCES items(id) ON DELETE CASCADE, completed_on TEXT NOT NULL, rating INTEGER, notes TEXT NOT NULL, takeaways TEXT NOT NULL, recorded_at TEXT NOT NULL)`; index on `outcomes(item_id)`.
  - `OutcomeStore(Protocol)`: `add_outcome(outcome: Outcome) -> None` (raises `UnknownItemError` for a missing item), `save_outcome(outcome) -> None` (upsert), `outcomes_for(item_id: str) -> list[Outcome]` (oldest first), `get_outcome(outcome_id) -> Outcome | None`.
  - `ItemStore` additions: `library(item_type: ItemType | None = None, limit: int = DEFAULT_PAGE_SIZE, offset: int = 0) -> list[Item]` (kept items, most recent completion first); `children_of(parent_id: str) -> list[Item]`; `done_between(start: date, end: date) -> list[Item]` (items with an outcome in range).
  - `Store` union gains `OutcomeStore`.
- [ ] **Step 1: Failing contract tests** (both stores): outcome round-trip incl. takeaways; two outcomes for one item kept in order; `delete_item` removes its outcomes and ungroups its children; `library(ItemType.RECIPE)` returns only kept recipes; `children_of`; `done_between` bounds inclusive.
- [ ] **Step 2: Failing integration test:** a database created with only `0001` and filled via Plan 1's store migrates to version 2 with all rows intact and defaults set (Review Focus 1).
- [ ] **Step 3:** Run → FAIL. **Step 4:** Implement (SQLite FK `ON DELETE` needs `foreign_keys=ON`, already set). **Step 5:** `make check`.
- [ ] **Step 6: Commit** `feat(store): outcomes, library and group queries (migration 0002)`.

### Task 3: Feature — `stash.lifecycle`

**Files:** Create `src/stash/lifecycle/__init__.py`, `service.py`, `ports.py`;
Tests `tests/unit/lifecycle/test_service.py`, `tests/acceptance/test_lifecycle.py`.

**Interfaces:**
- Consumes: Task 1–2 types; `new_id: Callable[[], str]`, `clock`.
- Produces: `LifecycleStore(Protocol)` (narrow: get_item, save_item, add_outcome, save_outcome, outcomes_for, get_outcome, children_of);
  `Lifecycle(store: LifecycleStore, new_id, clock, timezone: ZoneInfo)` with
  `complete(item_id, *, rating: int | None = None, notes: str = "", takeaways: Sequence[str] = (), keep: bool | None = None, on: date | None = None) -> Completion` (creates an Outcome, `completed_on` defaults to local today; repeat on a DONE item adds another outcome),
  `annotate(outcome_id, notes, takeaways) -> Outcome`, `rate(outcome_id, rating) -> Outcome`,
  `keep(item_id, kept: bool) -> Item`, `reopen(item_id) -> Item`, `drop(item_id, reason) -> Item`,
  `group(child_id, parent_id) -> Item`, `ungroup(child_id) -> Item`,
  `history(item_id) -> ItemHistory(item, outcomes, children)`.
  Errors: `UnknownItem(item_id)`, `LifecycleRefused(message)` (wraps domain `ValueError`).
  `Completion(item: Item, outcome: Outcome, repeat: bool)`.
- [ ] **Step 1: Failing acceptance tests** (named after new `docs/usage.md` section "Finishing things"): finish a book with rating 4 and two takeaways → DONE, one outcome; make a kept recipe again → second outcome, `repeat=True`, still kept; drop with reason "too expensive" → DROPPED, searchable; group "Tokyo ramen" under "Japan trip" → `children_of` lists it; grouping the trip under the ramen → `LifecycleRefused` (Review Focus 3).
- [ ] **Step 2:** Unit tests for each method's error paths. **Step 3:** Run → FAIL. **Step 4:** Implement. **Step 5:** `make check`.
- [ ] **Step 6: Commit** `feat(lifecycle): complete, repeat, keep, drop and group items`.

### Task 4: Quick buttons — Done, rating, keep

**Files:** Modify `src/stash/capture/callbacks.py` (FixKind), `fixes.py`,
`menus.py`, `replies.py`; Tests `tests/unit/capture/test_callbacks_lifecycle.py`,
`tests/unit/capture/test_fixes_lifecycle.py`, acceptance additions in
`tests/acceptance/test_capture_requests_and_fixes.py`.

**Interfaces:**
- Consumes: `Lifecycle` (Task 3) — `FixHandler` gains a constructor dependency `lifecycle: LifecycleActions` (Protocol in `capture/ports.py`: `complete`, `rate`, `keep`).
- Produces: new `FixKind` members `DONE="d"` (arg-less, subject item id), `RATE="r"` (subject = outcome id, arg `1`–`5`), `KEEP="k"` (subject = item id, arg `1`/`0`).
  Replies: confirmation and stage menu gain a `"Done ✓"` button (`stash:d:<id>`) for non-DONE items;
  `done_reply(completion) -> Reply` text `"🎉 Done: {title}"` (+ `" (again)"` on repeat), buttons row `⭐1 … ⭐5` (`stash:r:<outcome_id>:<n>`), row `["Keep 📚" (stash:k:<id>:1), "Not keeping" (stash:k:<id>:0)]`, footer line `"Tell me notes or takeaways any time."`;
  rating tap → edits to `"🎉 Done: {title} · ⭐{n}"` keeping the keep row; keep tap → `"📚 Kept: {title}"` / `"Okay, not keeping {title}."`.
- [ ] **Step 1: Failing tests:** encode/parse round-trip of the three kinds within 64 bytes for max-length ids; tapping Done on a DONE item edits to the repeat flow; tapping the same rating twice yields the same outcome rating (idempotent, Review Focus 2); a rating for an unknown outcome → `gone()`.
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement (new `match` arms; `assert_never` stays exhaustive). **Step 4:** `make check`.
- [ ] **Step 5: Commit** `feat(capture): one-tap done, rating and keep buttons`.

### Task 5: Routing update for status messages + eval cases

**Files:** Modify `src/stash/filing/prompt.py`; Modify `evals/cases.jsonl` (+6 fake cases);
Tests `tests/unit/filing/test_prompt_lifecycle.py`, `tests/unit/evaluation/test_shipped_cases.py` (counts).

- [ ] **Step 1:** System prompt gains: messages *about an existing item's progress* ("I finished…", "we went to… it was great", "takeaways from…") are `request`, not `capture`. Failing unit test asserts the instruction text is present and still delimits user data.
- [ ] **Step 2:** Add 6 routing cases (4 progress updates → request; 2 new-thing captures that mention finishing something else → capture). Update the shipped-case count test (31 cases: 17/11/3).
- [ ] **Step 3:** `make check`. **Step 4: Commit** `feat(filing): route progress updates to the assistant`.

### Task 6: Agent tools, `/library`, `stash library` / `stash show`

**Files:** Modify `src/stash/hermes_adapter/tools.py`, `plugin.py`
(`_register_tools` tuple), `commands.py`, `wiring.py`, `ports.py`;
`src/stash/cli/{parser,dispatch,commands}.py`; `src/stash/rendering.py`;
`src/stash/app/{app,build}.py` (wire `Lifecycle`); `tests/app_builders.py`; Tests
`tests/unit/hermes_adapter/test_tools_lifecycle.py`, `tests/acceptance/test_hermes_tools.py` additions,
`tests/acceptance/test_cli_library.py`, `tests/unit/test_rendering.py` additions.

**Interfaces:**
- Produces:
  - `StashApp.lifecycle: Lifecycle`.
  - Tools (toolset `stash`, JSON in/out, never raise): `stash_get {item_id}` → item + outcomes + children;
    `stash_complete {item_id, rating?, notes?, takeaways?, keep?, completed_on?}`;
    `stash_annotate {outcome_id, notes, takeaways?}`; `stash_set_stage {item_id, stage, reason?}` (`done` → use complete; `dropped` takes reason);
    `stash_keep {item_id, kept}`; `stash_group {child_id, parent_id | null}`; `stash_library {item_type?, limit?}`.
    Tool descriptions tell the agent to call `stash_search` first to find ids. Argument validation per Review Focus 5.
  - `/library [type]` → text list `"📚 {Type}: {title} · ⭐{last rating}"`, bounded like `/list`.
  - CLI: `stash library [--type T] [--limit N]`, `stash show ID` (item, outcomes with takeaways, children).
  - `rendering.library_line(item, last_outcome) -> str`, `history_lines(history) -> list[str]`.
- [ ] **Step 1: Failing acceptance tests:** agent-style tool calls complete a book with takeaways then `stash_library {"item_type":"book"}` lists it; `/library recipe`; `stash show <id>` prints takeaways; bad args → `{"error"}` and unchanged store.
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement; extend architecture guard allow-lists for `stash.lifecycle` (feature: may import domain + store.port only; importable by app, cli, hermes_adapter, rendering). **Step 4:** `make check`.
- [ ] **Step 5:** Update `docs/usage.md` ("Finishing things", "Your library") and `docs/spike-m0.md` (verify the agent actually uses `stash_complete` for "I finished X").
- [ ] **Step 6: Commit** `feat: lifecycle tools, /library and stash library/show`.
