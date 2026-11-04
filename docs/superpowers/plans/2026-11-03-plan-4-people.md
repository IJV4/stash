# stash Plan 4 — People and key dates (M4)

> **For agentic workers:** Python is written as `CLAUDE.md` § "Writing Python" says for the
> machine you are on (Mac: the `python-development` orchestrator; PC/WSL: subagent-driven
> development with TDD). The main loop commits.
> Requires Plans 2 and 3. Steps use checkbox (`- [ ]`) syntax.

**Goal:** A small list of people with yearly key dates. Items such as gifts
and plans link to people. Key dates produce lead-time reminders that pull in
linked gift ideas, and appear in the digest's upcoming section.

**Architecture:** `Person`/`KeyDate` value objects, migration `0004`, a
`PeopleStore` role Protocol, a `stash.people` feature (directory and name
resolution), a new `NudgeKind.PERSON_DATE` in `stash.nudges`, and agent tools
plus `/people` and `stash people`.

**Tech Stack:** unchanged.

**Spec:** design doc → People; Nudges (time-based reminders).

## Global Constraints

- Plan 1–3 Global Constraints apply.
- **Lead times (builder call, configurable as `[people] lead_days = [14, 2, 0]`):**
  reminders go out 14 days before, 2 days before and on the day, at
  `nudges.reminder_time`.
- **Feb 29:** in non-leap years the reminder falls on **Feb 28**.
- **Name matching:** names come from filing as `Item.people` strings. Matching
  is case-insensitive, exact on name or an alias, and **never fuzzy**. An
  unknown name stays a plain string, and the agent may offer to add the person.
- People data is private. It never appears in the HTML library (Plan 6).

## Review Focus

1. **Feb 29 birthdays** and dates near the year boundary: a Dec 30 birthday
   with a 14-day lead is first reminded on Dec 16.
2. **Two people with the same name or alias** → `ValueError` on save. An
   ambiguous name is never linked silently.
3. **Deleting a person** unlinks their items (the item keeps the name string)
   and removes their key dates and pending nudges.
4. **The same key date across many years:** the nudge ledger key includes the
   occurrence year, so each year fires once.
5. **Agent tool input:** invalid month/day pairs (Apr 31), blank names and
   2-KB notes → `{"error"}`, nothing stored.

---

### Task 1: Domain + migration 0004

**Files:** Create `src/stash/domain/person.py` and
`src/stash/store/migrations/0004_people.sql`. Modify the store
port/sqlite/_rows, `MemoryStore` and the builders. Tests:
`tests/unit/domain/test_person.py`, `tests/contract/test_store_people_contract.py`,
and a 0003→0004 migration integration test.

**Interfaces:**
- `Person(id, name ≤ 80, relation: str ≤ 40, aliases: tuple[str, ...] ≤ 5, notes ≤ 1000, created_at)`.
- `KeyDateKind(StrEnum)`: `BIRTHDAY`, `ANNIVERSARY`, `OTHER`.
- `KeyDate(id, person_id, kind, label ≤ 60, month, day, year: int | None)`.
  It is validated as a real calendar date, with Feb 29 allowed.
- `KeyDate.next_occurrence(today) -> date`.
- `KeyDate.years_on(occurrence) -> int | None`, the age or years married.
- SQL tables `people`, `key_dates` (FK cascade) and `item_people(item_id, person_id)`
  (FK cascade on both sides).
- `PeopleStore`: `save_person`, `get_person`, `delete_person`, `list_people`,
  `find_by_name(name) -> Person | None` (case-insensitive name or alias),
  `save_key_date`, `delete_key_date`, `key_dates_for(person_id)`,
  `key_dates_between(start, end) -> list[tuple[KeyDate, date]]` (occurrences),
  `link(item_id, person_id)`, `unlink`, `people_for(item_id)`,
  `items_for(person_id, item_type=None)`.
- [ ] **Step 1: Failing tests:** RF1 occurrences; the RF2 duplicate-alias
  refusal; RF3 cascades on both stores; `key_dates_between` across a year end.
- [ ] **Step 2–4:** Implement; `make check`. **Step 5: Commit** `feat(store): people and key dates (migration 0004)`.

### Task 2: `stash.people` — directory and linking at filing time

**Files:** Create `src/stash/people/{__init__,directory}.py`. Modify
`src/stash/capture/pipeline.py` (after an item is saved, link the people whose
names resolve) and the capture ports. Tests: `tests/unit/people/*` and
`tests/acceptance/test_people_linking.py`.

**Interfaces:**
- `PeopleDirectory(store, new_id, clock)`.
  - `add(name, relation="", aliases=())`, `rename`, `add_alias`, `remove(person_id)`.
  - `add_key_date(person_id, kind, month, day, year=None, label="")`.
  - `resolve(names: Sequence[str]) -> Resolution(linked: tuple[Person, ...], unknown: tuple[str, ...])`.
- The pipeline calls `PeopleLinker.link(item)` after `save_item`. A failure is
  logged and never blocks filing.
- [ ] **Step 1: Failing acceptance:**
  - "gift idea for Ana: ceramic class" with Ana in the directory → the item is linked.
  - An unknown name "Bea" → not linked; the confirmation is unchanged.
- [ ] **Step 2–4:** Implement; `make check`. **Step 5: Commit** `feat(people): directory and automatic linking`.

### Task 3: Person-date nudges and digest section

**Files:** Modify `src/stash/domain/nudge.py` (`PERSON_DATE`),
`src/stash/nudges/{nudger,messages,digest}.py`, `config` (`[people] lead_days`)
and `deploy/stash.toml.example`. Tests: the unit nudger/digest tests and
`tests/acceptance/test_person_reminders.py`.

**Interfaces:**
- The nudge subject is `"<key_date_id>@<occurrence ISO>#<lead>"` (RF4). It is
  wire-safe because `:` is not used.
- Message text:
  - Before the day: `"🎂 Ana's birthday in 14 days (Sat Mar 6)."`, then the
    linked gift ideas (`"Gift ideas: • ceramic class • …"`), or
    `"No gift ideas saved yet."`.
  - On the day: `"🎂 Today: Ana's birthday (turns 34)."`.
  - The emoji depends on the kind: 🎂 birthday, 💍 anniversary, 📅 other.
- Digest "upcoming 14 days" includes person dates.
- [ ] **Step 1: Failing tests:**
  - A 14/2/0 sequence for a Mar 6 birthday.
  - Feb 29 in 2027 → Feb 28.
  - Gift ideas are listed, and only GIFT items not yet DONE.
  - Catch-up batching still produces one message.
- [ ] **Step 2–4:** Implement; `make check`. **Step 5: Commit** `feat(nudges): reminders for people's key dates`.

### Task 4: Agent tools, `/people`, `stash people`

**Files:** Modify `hermes_adapter/{tools,commands,wiring,plugin,ports}.py`, the CLI,
`rendering.py` and `app/*`. Tests: the tool and command unit tests,
`tests/acceptance/test_hermes_people.py` and `tests/acceptance/test_cli_people.py`.

**Interfaces:**
- Tools:
  - `stash_people {}`
  - `stash_add_person {name, relation?, aliases?}`
  - `stash_add_key_date {person_id, kind, month, day, year?, label?}`
  - `stash_link_person {item_id, person_id}`
  - `stash_remove_person {person_id}`
  - All return JSON and never raise (RF5).
- `/people`: one line per person with their next key date.
- `stash people [--upcoming DAYS]`.
- `StashApp.people: PeopleDirectory`.
- [ ] **Step 1: Failing acceptance:** tool calls add Ana with her birthday;
  `/people` shows `Ana (wife) — birthday Sat Mar 6`.
- [ ] **Step 2–4:** Implement; architecture guard (`stash.people` is a feature); `make check`.
- [ ] **Step 5:** Update `docs/usage.md` ("People and dates").
  **Step 6: Commit** `feat: people tools, /people and stash people`.
