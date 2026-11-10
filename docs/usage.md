# stash — owner guide

You send things to a Telegram bot; stash files them, reminds you, and keeps a library of what
you finished. Every message is saved before any AI step, so nothing is lost when the AI is slow,
busy or down. Behaviour is specified in `docs/superpowers/specs/2026-11-02-stash-design.md`; the
tests are named after the behaviour they pin.

## What to send

- **A link.** It is filed with its page title, uploader and duration when the page has them.
- **A thought** ("try that ramen place in Shibuya"). It is filed as a type (place, recipe, book,
  media, gift, …) and a stage (inbox, want to, planned, doing, done, dropped).
- **An image.** It is read by the vision model, and filed like a thought.
- **A question.** It goes to the assistant instead of being filed. Start a message with `?` to
  make sure it is treated as a question.
- **Several messages at once.** They get one combined confirmation.

When the GPU is busy or the AI is down, the reply says the message is saved and will be filed
when the GPU is free or the AI is reachable. `/retry` (or `stash retry`) files
what is pending.

## Buttons

| Button | What it does |
|---|---|
| `Type`, `Stage` | Correct how an item was filed. |
| `That was a question →` | Hand the message to the assistant instead (it is not filed). |
| `Done ✓` | Finish an item. Then `⭐1`–`⭐5` rate it, and `Keep 📚` / `Not keeping` decide whether it goes into your library. |
| `Done ✓ · <name>` | On a reminder with several items: finish that one. The reminder stays, and the answer comes as a new message. |
| `Didn't happen` | On a morning-after follow-up: the plan did not happen, and the item goes back to Want to. |
| `Looks good ✓`, `No steps` | Accept or decline prep steps the AI proposed for a planned, dated item. |

An old or stale button answers "That item no longer exists." or "That changed meanwhile — try
again."; nothing is changed.

## Reminders and the digest

- **Reminders.** A step reminder goes out before a planned item. A day-of reminder goes out at
  `reminder_time`, and a follow-up ("How was it?") the morning after, at `followup_time`. You get
  at most one follow-up message a day.
- **Forgotten and stuck items.** Want-to items older than `forgotten_after_days` and doing items
  older than `stuck_doing_days` appear in the weekly digest.
- **The weekly digest.** It goes out on `digest_day` at `digest_time`. It lists what was added,
  what is coming in the next 14 days (people's dates included) and up to 3 suggestions.
- **The PC was off.** Everything missed arrives as one catch-up message, and nothing is sent
  twice.
- **First run.** A first run over an existing database sends nothing old.
- **Prep steps.** For a planned item with a date today or later, the AI may propose prep steps.
  None are kept until you press `Looks good ✓`.

## People and key dates

- **Adding people.** Ask the agent to add a person (name, relation, aliases) and their
  birthdays, anniversaries or other dates.
- **Linking.** Items that name a person, now or earlier, are linked to them. Matching is exact on
  the name or an alias, case-insensitive, and never fuzzy; an unknown name stays plain text.
- **Reminders.** Key-date reminders go out at `[people] lead_days` before the date (default 14, 2
  and 0 days), listing that person's open gift ideas. Only the closest one that is due is sent,
  worded with the real number of days left. On the day itself only the on-the-day reminder goes
  out, at `reminder_time`. A key date whose whole day the PC was off is skipped; the earlier
  reminders have normally gone out already. Feb 29 is reminded on Feb 28 in other years.
- **Correcting a date.** Adding a key date again with the same kind and label replaces the old
  date.

## Commands (Telegram)

| Command | Answer |
|---|---|
| `/list [stage]` | Newest items, one per line. |
| `/library [type]` | Kept items. |
| `/library html` | The whole library as one HTML file (also saved as `data_dir/library/latest.html`). Over 45 MB it is refused. |
| `/people` | One line per person with their next key date (the first 20, then "…and N more"). |
| `/suggest [context]` | Up to 3 Want-to items that fit the moment. |
| `/gpu status\|on\|off` | Show or switch the GPU gate (when off, stash uses OpenRouter or defers). |
| `/retry` | File every pending capture. A capture that turns out to be a question says to send it again starting with `?`. |

**Agent tools**, used by the assistant:
- `stash_search`, `stash_list`, `stash_get`, `stash_library` read items;
- `stash_capture` saves something new;
- `stash_complete`, `stash_annotate`, `stash_keep`, `stash_set_stage`, `stash_set_date`,
  `stash_group` change an item;
- `stash_add_step`, `stash_edit_step`, `stash_complete_step` work on steps;
- `stash_suggest` picks suggestions;
- `stash_people`, `stash_add_person`, `stash_add_key_date`, `stash_link_person`,
  `stash_remove_person` work on people.

All of them answer JSON. Bad input answers `{"error": "..."}` and stores nothing.

## Command line

`stash <command> [--config PATH]`. The config defaults to `$STASH_CONFIG`.

| Command | Does |
|---|---|
| `doctor` | Checks the config, the database, the AI providers, the GPU reading, the optional tools (yt-dlp, tesseract, deno) and the last backup (< 48 h). |
| `list [--stage S] [--type T] [--limit N]` | Saved items. |
| `show ITEM_ID` | An item's history. |
| `library [--type T] [--limit N] [--html PATH]` | Kept items, or the whole library written as an HTML page. |
| `people [--upcoming DAYS]` | People and their next key dates. |
| `retry` | Files every pending capture. |
| `gpu status\|on\|off` | Shows or switches the GPU gate. |
| `backup --to DIR` | Writes `stash-YYYYMMDD.db` (the systemd timer runs it daily). |
| `tick [--dry-run]` | The cron fallback for reminders. It prints nothing when nothing is due, and `--dry-run` marks nothing sent. |
| `eval [--providers …] [--thinking default,off] [--arms …] [--cases PATH] [--out PATH]` | Compares local and OpenRouter models on the fake cases in `evals/cases.jsonl`, with a per-case section. |

## Configuration (`stash.toml`)

See `deploy/stash.toml.example`; every key has its default there. Unknown keys are refused.

| Table | Keys |
|---|---|
| `[llm]`, `[llm.ollama]`, `[llm.openrouter]`, `[llm.tasks]` | The provider, models and timeouts; `busy_fallback = "wait"` (defer filing while the GPU is busy) or `"openrouter"`; a provider per task (`filing`, `suggestions`, `vision`). |
| `[llm.thinking]` | `default` or `off` per task, for stash's own calls only. Off maps to each provider's field. |
| `[gpu]` | `min_free_vram_mib`, `max_foreign_utilization_pct`, `manual_off_hours`: when the GPU counts as busy, and how long `gpu off` lasts. |
| `[nudges]` | `digest_day`, `digest_time`, `reminder_time`, `followup_time`, `forgotten_after_days`, `stuck_doing_days`, `tick_seconds`. Changing a time can repeat that day's sends once. |
| `[people]` | `lead_days`. |

## Deploying and live checks

- Install and run it on the PC (WSL2, Hermes profile, systemd units, NAS backup):
  `docs/deploy/wsl-setup.md`.
- What still has to be verified against the live services: `docs/spike-m0.md`.
- Decisions behind the setup: `docs/adr/`.
