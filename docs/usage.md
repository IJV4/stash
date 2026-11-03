# stash — how it is used

This is the outside-in specification. Every behaviour below is one statement;
each statement becomes exactly one acceptance test, named after its section.
All examples use fake data. Statements marked **[T1]** are covered by the
tests that exist today; the rest are specified here and get their acceptance
tests in the task named in brackets (see the plan in
`docs/superpowers/plans/2026-11-02-plan-1-core-and-filing.md`).

The owner talks to a Telegram bot. Every incoming message is saved raw before
any AI step, so nothing is lost when the AI is slow, busy or down.

## Sharing a link  [Task 9]

Send `https://example.com/ramen-tokyo` with the optional note `try this in March`.

- The bot replies with one line: `✅ Places · Tokyo · Want to`.
- The reply carries two buttons, `Type` and `Stage`.
- The item exists in the store with stage Want to, the link as its source URL
  and the note kept.
- Sending the same Telegram message twice (a gateway retry) creates one item.

## Typing a thought  [Task 9]

Send `idea: sell handmade candles at the weekend market`.

- The bot replies `✅ Ideas · Want to` (no detail segment when nothing fits).
- A message of 10 000 characters is saved whole, gets a title of at most 120
  characters, and the reply stays within 4096 characters.

## Sending an image  [Task 9]

Send a picture with no caption.

- The image path is saved with the capture and the item is filed from the note
  alone; with no text the title is `Untitled`.
- The bot still replies with a confirmation.

## Asking a question  [Task 9]

Send `what can I do Saturday afternoon?`.

- The AI routes it as a request: no item is created and the question is handed
  to the assistant.
- When the AI is unsure, the item is filed and the reply carries a
  `That was a question →` button; pressing it deletes the item and hands the
  original text to the assistant.

## Pressing a fix button  [Task 9]

- `Type` opens a menu of item types; choosing `Recipes` retypes the item and
  shows the updated confirmation.
- `Stage` opens a menu of stages; items without a date are offered Inbox, Want
  to, Doing and Dropped; items with a date also Planned.
- A stale or forged button (unknown item, malformed data) answers
  `That item no longer exists.` and never fails.

## GPU busy  [Task 9]

Another application is using the GPU (or the owner ran `stash gpu off`).

- The bot replies `📥 Saved — I'll file it when the GPU is free.`
- The capture stays pending; `stash retry` (or the next retry) files it once
  the GPU is free.

## AI down  [Task 9]

Ollama is unreachable, times out, or OpenRouter returns an error.

- The bot replies `📥 Saved — I'll file it once the AI is reachable.`
- The capture stays pending and is filed by a later retry.

## Several messages at once  [Task 9]

Forwarding a backlog produces one combined reply: `✅ Saved 3 items:` followed
by one bullet per item, instead of three replies.

## stash --version  [T1]

    $ stash --version
    stash 0.1.0

- `main(["--version"])` returns 0 and prints `stash 0.1.0` on standard output
  (acceptance test `test_version_flag_prints_version`).
- The version it prints is the installed package's version (unit test
  `test_package_version_matches_installed_distribution_metadata`).

## stash doctor  [Task 11]

Prints one line per check, `✔`, `✖` or `!` followed by the name and a detail,
and exits 1 when a required check fails (for example an OpenRouter key that is
rejected). Invalid configuration exits 2 with the error message.

## stash list  [Task 11]

`stash list --stage want_to --type place --limit 20` prints matching items,
newest first.

## stash retry  [Task 11]

Files every pending capture and prints one line for each.

## stash gpu  [Task 11]

`stash gpu status | off | on`. `off` prints when the switch expires (4 hours
by default) and tells Ollama to unload its model.

## stash eval  [Task 11]

`stash eval --providers ollama,openrouter --arms text,vision,ocr` runs the fake
case set against each provider and prints a Markdown comparison table.

## stash backup  [Task 11]

`stash backup --to DIR` writes `stash-YYYYMMDD.db` and keeps the newest 30.

## Storage guarantees  [Tasks 2-3]

These have no caller-visible surface yet; they are pinned by unit and contract
tests and surface through the sections above.

- A capture is stored raw before filing; a second capture from the same chat
  message is refused and nothing is written.
- Items round-trip with details, tags, people and date intact, and list newest
  first.
- Search is a case-insensitive substring match over title, note and tags.
- Reopening the database keeps the data and does not re-run migrations.
