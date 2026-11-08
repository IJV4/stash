# stash clean-up — design

Date: 2026-11-07. Branch: `cleanup` (from `main` d5e8931). Approach **A**, chosen by the owner.

## Intent

stash works, but it is too heavy to change. The source is ~14.5k lines. The tests are ~70.8k
lines (unit tests alone are 48.8k lines in 359 files), with 89 fake files and a 1,811-line
`docs/usage.md`. Every agent session reads and edits far more than the change needs, and the
2026-11-07 cost analysis (R15) traced most of the spend there. This clean-up makes future changes
cheaper, mostly for agent sessions, **without changing behaviour**.

The whole-branch review of 2026-11-07 named the hotspots this addresses:

- two store implementations;
- the single-fault fakes;
- layered concurrency for one owner and one process;
- `usage.md` written as an API narration;
- a Protocol for every consumer (81 `class …(Protocol)` in `src`).

## Goals

1. **One store in tests.** Every test that needs a store uses the real `SqliteStore` on an
   in-memory (or temporary-file) SQLite database. The in-memory store family (`tests/fakes/memory_*`)
   and the "run against both stores" parametrisation are deleted.
2. **Redundant unit tests deleted (owner decision).** A unit test is redundant when its behaviour
   is already pinned by an acceptance, contract or integration test. Deleting it must not lower
   branch coverage of `src`. Keep a unit test when it is the only cover for a branch, or when it
   pins tricky logic: date and DST arithmetic, Feb 29, escaping and URL schemes, parsing and
   clamping hostile LLM or link output, wire formats (`callback_data` ≤ 64 bytes), and config
   validation tables (one parametrised table per loader, not one test per value).
3. **One fault-injecting store wrapper.** It replaces the single-fault stores (failing, busy,
   racing, changing, vanishing, lingering, …): `FaultyStore(real, fail_on={method: exception})`
   or an equivalent shape. Fakes remain only at real external seams: the LLM, Telegram/PTB, the
   Hermes context, link inspection/yt-dlp, the GPU probe, OCR, the clock and ids.
4. **One process-wide write lock.** It serialises owner actions (button presses, agent tools,
   intake writes) and ticker delivery inside the gateway process. Then delete what it makes
   unnecessary:
   - the conditional `replacing=` writes, `StaleItemError`/`ItemChanged`, and the "changed
     meanwhile" replies;
   - the per-service locks (FixHandler, Planning, and any other in-process lock it subsumes);
   - the race fakes and race tests.
5. **Protocols only at real seams.** Keep them at the store port, the LLM port, the Telegram/Hermes
   adapter ports, enrichment, and the clock/ids. Inside the core, a feature's consumer-side
   Protocol becomes the concrete class or the store port. Duplicates go (`PeopleRoster` ×2,
   `NudgeDeliveries` vs `TickDelivery`).
6. **Owner docs.** `docs/usage.md` becomes a one-page owner guide: what to send, the buttons, the
   commands, the config keys, and pointers to deploy and spike-m0. `docs/store-writes.md` is
   deleted or folded in. The spec plus behaviour-named tests become the contract writers work
   from. `CLAUDE.md` is updated to match (see Constraints).

## Non-goals

- No behaviour change visible to the owner. The one exception is that the "That changed
  meanwhile — try again" reply disappears with goal 4.
- No Plan 5, no Plan 3 Task 7, no new features.
- No change to the migrations, the database schema, the Hermes pin, runtime dependencies, or
  the spike-m0 rows.

## Anti-goals (a failure even if the gate is green)

- Lower branch coverage of the `src` code that still exists after the change.
- A behaviour from the spec, or an owner-facing fix from Plans 2–6, that ends up with no test at
  all. That includes the review-fix tests: stale "Didn't happen", proposals for past dates,
  withdrawing a proposal after a failed send, people backlinks, presses on batched nudges, and
  confirmed steps kept on reroute.
- Losing fidelity in the fakes that guard live-service facts. The Hermes ctx fake must still
  refuse injection, dedupe factories and refuse `spawn_task` outside a running loop. The PTB fake
  must still accept only real kwargs.
- A slower gate: today `make check` takes ~20 s wall-clock, and the target is ≤ 30 s.
- Weaker layering: the architecture tests stay and still pass.

## Constraints

- `make check` stays the only gate, green after every step, with one task per commit. On the
  Mac, the 4 real-socket tests skip because the sandbox forbids binding, and the tesseract test
  skips.
- **Owner ruling R15** applies throughout:
  - one review round of at most 3 reviewers per task;
  - sonnet by default;
  - the orchestrator delegates its reading;
  - Minor findings go to the branch notes;
  - fix rounds go to a fresh writer.
- Python is written through the `python-development` orchestrator or writers (owner's global
  rule). This clean-up conflicts with that plugin's defaults ("in-memory fakes", "usage
  document"), and **CLAUDE.md wins**. `CLAUDE.md` § Tests is updated in step 6 to say:
  - tests use the real SQLite store in memory, plus `FaultyStore` for faults;
  - fakes exist only at external seams;
  - the spec is the usage document;
  - the R15 test budget applies.
- New dev dependency: `pytest-cov` (from PyPI, dev group only), used to measure coverage for
  goal 2. Whether `make check` itself measures coverage is the builder's call. The default is
  no: a separate `make coverage` target.
- Fake data only. Offline only.

## Approaches considered

- **A. Step by step, with coverage-guided test deletion (chosen).** Six steps, each green:
  1. one store;
  2. delete redundant unit tests, checked against branch coverage;
  3. one write lock;
  4. one fault wrapper;
  5. trim the Protocols;
  6. docs and CLAUDE.md.

  Deletion comes early, so the later refactors touch fewer tests. Evidence backs every deletion.
  Cost: one dev tool and six review rounds.
- **B. Step by step, with judgment-based deletion.** The same order, but reviewers decide what is
  redundant. No new tool, but the deletions rest on opinion. Rejected.
- **C. Rebuild the test suite from the spec, then refactor.** Smallest result, but behaviour is
  guarded only by untrusted new tests for a while. Rejected as too risky for a working app.

## How (decided)

**Order.** The six steps above, one plan task per step, each its own commit. If a step is too big
for one orchestrator run, the builder may split it into sub-tasks (as with Plan 3 6a/6b).

**Step 1 (one store).**
- A shared test builder opens `SqliteStore` on `:memory:` (or a temp file where WAL behaviour
  matters).
- Contract tests drop the store parametrisation and run once, on SQLite.
- Tests that relied on in-memory store internals (snapshots, seeded ids) use the public store API
  or a small builder instead.

**Step 2 (coverage-guided deletion).**
1. Measure the baseline: line and branch coverage of `src` over the default and `-m integration`
   runs.
2. Work package by package. For each unit test file, decide whether to delete it, trim it, or
   merge it into a parametrised table. Delete only when coverage stays at the baseline and the
   behaviour is pinned at a higher tier. Keep the goal-2 categories.
3. Record per-package counts (files and lines before and after) in the task report.

**Step 3 (one write lock).**
- The lock is one instance, built in `stash.app`.
- It is held around each owner action's read-modify-write and around each ticker delivery.
- It is **never held across an LLM or network call**: filing can take ~100 s, and button presses
  must not wait for it.
- SQLite `BEGIN IMMEDIATE`, the busy timeout and `StoreBusyError` stay, because `stash tick` and
  `stash serve` are other processes.
- These stay because they are not concurrency machinery:
  - the double-tap window (UX);
  - atomic `group_item`;
  - `record_all_sent` (crash safety);
  - the ticker's no-overlap guarantee (the write lock may provide it).

**Step 4 (one fault wrapper).** One wrapper around the real store, configurable per method. Each
single-fault store fake is replaced, or deleted with its tests.

**Step 5 (Protocols).** Feature-internal ports become concrete types. The ports at the seams listed
in goal 5 stay, and the architecture tests keep enforcing the layers.

**Step 6 (docs).**
- `docs/usage.md` becomes the one-page owner guide (~150 lines).
- `docs/store-writes.md` goes.
- Update `CLAUDE.md` § Tests and "Writing Python".
- Grep `docs/` and the plans for pointers into the deleted sections.

**Success numbers** (checked at the end):
- tests at or under ~25k lines;
- fake files at or under ~25;
- Protocols at or under ~30;
- branch coverage of the remaining `src` at or above the baseline;
- `make check` at or under 30 s;
- `docs/usage.md` at or under ~200 lines.

## Left to the builder

- The exact `FaultyStore` shape and name.
- Where the write lock lives and how features receive it.
- File-by-file deletion choices within the goal-2 rules.
- Whether to split steps into sub-tasks.
- Whether coverage runs inside `make check`; the default is a separate target.
- Which feature Protocols are "real seams" at the margins. Rule: two implementations in `src`
  (or an external system behind it) make a real seam; one implementation plus a test fake does
  not, unless the fake guards a live-service fact.

## Settled after the builder check (controller's calls unless marked)

1. **Domain checks stay, race checks go.** The race-only machinery is removed: `replacing=`,
   `StaleItemError`, and the "changed meanwhile" reply for a concurrent write. Checks that compare
   a press with the item's *current state* are domain rules and stay, with their reply. The main
   one is "Didn't happen" whose encoded date no longer matches the item. A domain check may keep a
   renamed exception (for example `StaleButton`), and its tests are rewritten, not deleted.
2. **Cross-process lost updates are accepted (the owner agreed: "SQLite locking stays for the CLI
   and serve").** The other processes are:
   - `stash serve`: read-only;
   - `stash tick`: the cron fallback, off by default; it writes only idempotent ledger inserts;
   - the CLI.

   None of them does an item read-modify-write while the gateway runs in normal use, so nothing
   replaces `replacing=` across processes. If the builder finds a CLI command that does an item
   read-modify-write, it notes this in the task report and does not add machinery.
3. **Coverage and behaviour win over the numbers.** The success numbers are targets. Never delete
   below the coverage baseline, or below the anti-goal list, to reach them. Report the numbers
   actually reached.
4. **`SerializedPipeline` (`capture/serial.py`) stays.** It serialises intake by design and may be
   held across the LLM call. The new write lock is taken only around store read-modify-write
   sections: owner actions, tools, the post-LLM save, and ticker delivery. It is never held across
   an LLM or network call, so intake stays serialised and a button press waits only for a short
   store section.
5. **The coverage baseline is per step.** Coverage of the `src` that remains must be no lower than
   coverage of that same code just before the step. For a unit test to count as "pinned at a
   higher tier", the branch must be covered with the unit tests excluded (acceptance + contract +
   integration only). The task reviewer also checks that the behaviour is *asserted* at that tier,
   not merely executed.
6. **Protocols are counted in `src` only**, as `class …(Protocol)` definitions, today 81. The ~30
   target is a target (point 3).
7. **The gate budget:** aim for ≤ 30 s. Real SQLite in memory is expected to be fast. A temporary
   file is used only where WAL or multi-connection behaviour is the point of the test. If the
   budget is exceeded, report it rather than reintroduce fakes.
