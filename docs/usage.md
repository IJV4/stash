# stash — how it is used

This is the outside-in specification. Every behaviour below is one statement;
each statement becomes exactly one acceptance test, named after its section.
All examples use fake data. Statements marked **[T1]** are covered by the
tests that exist today; the rest are specified here and get their acceptance
tests in the task named in brackets (see the plan in
`docs/superpowers/plans/2026-11-02-plan-1-core-and-filing.md`).

The owner talks to a Telegram bot. Every incoming message is saved raw before
any AI step, so nothing is lost when the AI is slow, busy or down.

## Calling it from code  [Tasks 7-9]

The Telegram adapter (Task 12) and the CLI (Task 11) call the same objects
the acceptance tests do. `stash.app` is the only module that builds the
adapters; everything else receives them.

    from stash.capture import (
        BurstCoalescer, CapturePipeline, FixHandler, IncomingMessage, reply_for,
    )
    from stash.enrich.links import FallbackInspector
    from stash.filing import Filer

    inspector = FallbackInspector(YtDlpInspector(default_ytdlp_extract), HtmlMetaInspector(client))
    filer = Filer(router, clock, config.timezone)
    pipeline = CapturePipeline(store, inspector, filer, new_id, clock)

    result = pipeline.handle(IncomingMessage(source, text, media_paths, received_at))
    # Filed | IsRequest | Deferred | Duplicate
    reply = reply_for(result)          # Filed | Deferred -> Reply (text and buttons)
    bursts = BurstCoalescer(config.burst_window_seconds)
    bursts.add(result, now)            # Filed and Deferred only
    reply = bursts.due(now)            # Reply | None
    answer = FixHandler(store, clock).apply("stash:t:<item id>")   # Reply | Reroute
    pipeline.retry_pending()           # list[ProcessResult]

## Link details  [Task 7]

When a message contains a link, the first link is inspected before filing.
The inspector never raises: a link it cannot describe is "unknown" and the
capture is filed from the owner's own words. Each statement below has one
acceptance test in `tests/acceptance/test_link_inspection.py`.

1. A link yt-dlp can describe yields its title, description, uploader, the
   duration in whole seconds, and whether captions (manual or automatic) exist.
2. When yt-dlp fails or finds no title, the page itself is read: Open Graph
   title and description first, then `<title>` and the meta description.
3. When neither can describe the link the result is unknown: only the platform
   (`instagram`, `youtube`, `tiktok`, `x`, `reddit` or `web`, from the host)
   is filled in.
4. A link that points at the owner's own machine or network (`localhost`, a
   private or link-local address) is never fetched, and neither is a page
   redirect that leads there. (yt-dlp follows redirects inside its own HTTP
   stack; only the first address is checked on that path. DNS names that
   resolve to private addresses are not detected on either path.)

Pinned by unit tests: hosts disguised with non-ASCII dots (`127。0。0。1`) or
IPv6 translation prefixes (NAT64, 6to4) are judged by the address they really
reach; hosts that are not plain host names (backslashes, percent escapes),
names without a dot, multicast addresses and home-network suffixes (`.lan`,
`.local`, `.internal`, `.localdomain`, `.svc`, ...) are never fetched; reading a page gives up after 20 seconds in total; only the first
512 KiB of a page is read; at most three redirects are followed; non-HTML, error statuses and timeouts are unknown;
trailing punctuation is not part of a link; the same link is reported once;
fields from the page are clipped to a safe length; `http` and `https` are the
only schemes accepted.

## Filing  [Task 8]

The filer asks the AI for a type, title, stage, details, tags, people and
date, and treats the answer as untrusted. Each statement below has one
acceptance test (1-4 in `tests/acceptance/test_filing.py`, 5 in
`tests/acceptance/test_filing_over_http.py`).

1. A clear capture is filed as the AI described it: type, title, stage
   (Want to), details and tags.
2. An answer with an unknown type, a forbidden stage such as `done`, or no
   title still produces a filing: Other, Inbox, title taken from the text.
3. An answer that is not JSON at all produces an Inbox filing titled from the
   text (the AI being unsure is never an error for the owner).
4. Words in a link's description reach the AI only inside the delimited
   `<link>` block, whatever they say.
5. The request to a real model carries the filing schema as plain JSON in
   `response_format` (checked through the real client on a fake transport), so
   a live Ollama or OpenRouter accepts it.

Pinned by unit tests: a Planned answer without a valid date becomes Want to;
at most 10 tags and 5 people; non-text details are dropped; titles are clipped
to 120 characters; "today" is the owner's local date; a message with no text
and no link is filed as an Other Inbox capture without asking the AI; an AI
that is down or deferred propagates so the capture stays pending.

## Sharing a link  [Task 9]

Send `https://example.com/ramen-tokyo` with the optional note `try this in March`.

1. The bot replies with one line, `✅ Places · Tokyo · Want to`, carrying two
   buttons, `Type` and `Stage`. The item exists with stage Want to, the link as
   its source URL and the whole message kept as the note.
2. Sending the same Telegram message twice (a gateway retry) creates one
   capture and one item; the second delivery is a duplicate.

## Typing a thought  [Task 9]

Send `idea: sell handmade candles at the weekend market`.

1. The bot replies `✅ Ideas · Want to` (no detail segment when nothing fits).
2. A message of 10 000 characters is saved whole, gets a title of at most 120
   characters, and the reply stays within 4096 characters.

## Sending an image  [Task 9]

Send a picture with no caption.

1. The image path is saved with the capture and the item is filed from the note
   alone; with no text the title is `Untitled` and the AI is not asked. The bot
   still replies with a confirmation.

## Asking a question  [Task 9]

Send `what can I do Saturday afternoon?`.

1. The AI routes it as a request: no item is created, the capture is marked as
   a request and the question is handed to the assistant.
2. When the AI is unsure, the item is filed and the reply carries a
   `That was a question →` button; pressing it deletes the item, marks the
   capture as a request and hands the original text to the assistant. Pressing
   it a second time answers `That item no longer exists.`

## Pressing a fix button  [Task 9]

1. `Type` opens a menu of item types; choosing `Recipes` retypes the item and
   shows the updated confirmation.
2. A stale or forged button (unknown item, malformed data) answers
   `That item no longer exists.` and never fails.

Pinned by unit tests: `Stage` opens a menu of stages; items without a date are
offered Inbox, Want to, Doing and Dropped; items with a date are also offered
Planned; a stage the menu did not offer is answered with the menu again;
every button's data is at most 64 bytes.

## GPU busy  [Task 9]

Another application is using the GPU (or the owner ran `stash gpu off`).

1. The bot replies `📥 Saved — I'll file it when the GPU is free.` The capture
   stays pending; `stash retry` (or the next retry) files it once the GPU is
   free, without creating a second item.

## AI down  [Task 9]

Ollama is unreachable, times out, returns an error, or the provider rejects
the key.

1. The bot replies `📥 Saved — I'll file it once the AI is reachable.` The
   capture stays pending and is filed by a later retry.
2. A misconfigured provider (rejected key, unknown model) is treated the same
   way: the capture is never lost and nothing crashes.

## Several messages at once  [Task 9]

1. Forwarding a backlog produces one combined reply once the burst window has
   passed: `✅ Saved 3 items:` followed by one bullet per item, instead of
   three replies. Nothing is sent before the window has passed.

Pinned by unit tests: a single message in a window gets its normal reply and
buttons; the combined reply never exceeds 4096 characters; a batch whose reply
cannot be built is kept for the next attempt. The coalescer is not
thread-safe: call it from one thread (the adapter's event loop).

## Recovering from half-finished work  [Task 9]

Pinned by unit tests: a capture whose processing fails unexpectedly is logged
and skipped, stays pending, and does not stop the rest of `retry_pending`; a
capture whose item was saved before the status write failed is completed on
retry without asking the AI and without overwriting a fix the owner made in
between; a retry that finds the item already saved returns it as a plain confirmation
(the `That was a question →` button is not repeated); capture and item ids must
be 1-40 ASCII characters without whitespace or `:` so every button fits in 64
bytes; media paths containing `..`, a NUL or a
URL are refused when the message is built (absolute gateway cache paths are
accepted; keeping reads under the media directory is the media loader's job).

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
