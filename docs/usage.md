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

## Configuration  [Task 4]

`load_config(path, env)` (in `stash.config.loader`) reads a TOML file (example:
`deploy/stash.toml.example`). Secrets come from the environment only.
`load_config` is the whole surface and has no edge to fake, so these
statements are pinned by unit tests (like "Storage guarantees"), not repeated
as acceptance tests.

- A minimal file (`[llm] provider = "ollama"` plus `[llm.ollama] model = "m"`)
  loads with Ollama at `http://localhost:11434/v1`, timezone
  `America/Los_Angeles`, `busy_fallback = "wait"` and the default GPU limits.
- `[llm.openrouter] model = "x"` with `OPENROUTER_API_KEY` in the environment
  gives OpenRouter settings at `https://openrouter.ai/api/v1` carrying that key.
- Choosing OpenRouter (as `provider`, as `busy_fallback`, or in `[llm.tasks]`)
  without `OPENROUTER_API_KEY` is a `ConfigError` that names the variable.
- An unknown provider name is a `ConfigError` naming the key path.
- `[llm.tasks] suggestions = "openrouter"` sends suggestions to OpenRouter while
  filing keeps using `provider`.
- An `api_key` inside the file is a `ConfigError` ("put secrets in env").
- An unknown key anywhere is a `ConfigError` naming its path (typos fail loudly).
- A `base_url` must be an http(s) URL with a host and no credentials; OpenRouter
  must use https.

## Switching the AI provider  [Tasks 4-5]

One config line plus an API key moves every stash LLM call between Ollama and
OpenRouter. Each statement below has one acceptance test in
`tests/acceptance/test_provider_switching.py`.

1. With `provider = "openrouter"`, a model request goes to
   `https://openrouter.ai/api/v1/chat/completions` with `Authorization: Bearer`
   and `X-OpenRouter-Title: stash`.
2. With `provider = "ollama"` it goes to the local server with no
   `Authorization` header.
3. A per-task override (`[llm.tasks] suggestions = "openrouter"`) routes only
   that task to the other provider.
4. The answer is requested as a JSON schema (`response_format`, named after the
   caller's schema).
5. Text that is not JSON is `LlmBadOutput`.
6. A provider that is down (timeout, connection refused, HTTP 402/408/429/5xx,
   or an `{"error": ...}` body inside an HTTP 200) raises `LlmUnavailable`.
7. A rejected request (HTTP 400) raises `LlmError` that is not `LlmUnavailable`.
8. The Ollama doctor probe reports a configured model that is not pulled.
9. The OpenRouter doctor probe reads "invalid key" for a rejected key.

## GPU sharing  [Tasks 5-6]

Each statement below has one acceptance test in
`tests/acceptance/test_gpu_sharing.py`.

1. Another application filling the GPU's VRAM (less free than
   `min_free_vram_mib`) makes the gate busy.
2. Foreign utilisation above `max_foreign_utilization_pct` while stash's model
   is unloaded makes the gate busy.
3. No `nvidia-smi` means "no GPU info" and the gate stays free.
4. With `busy_fallback = "wait"` a busy GPU defers Ollama work (`LlmDeferred`)
   without sending any request.
5. With `busy_fallback = "openrouter"` the same call goes to OpenRouter.
6. Work configured for OpenRouter is never deferred.
7. `gpu off` makes the gate busy for `manual_off_hours` (default 4); work flows
   again after the expiry.
8. `gpu on` ends the switch-off early.
9. The status reads `turned off until HH:MM` (in the caller's timezone).
10. The switch-off survives a restart (it is a stored setting).
11. Telling Ollama to unload (`keep_alive: 0`) frees VRAM immediately.
12. VRAM held by stash's own Ollama model is not counted against the GPU: the
    gate stays free when stash's model is the only thing filling it.

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
