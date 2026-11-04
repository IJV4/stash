# stash — how it is used

This is the outside-in specification. Every behaviour below is one statement;
each statement becomes exactly one acceptance test, named after its section.
All examples use fake data. Statements marked **[T1]** are covered by the
tests that exist today; the rest are specified here and get their acceptance
tests in the task named in brackets (see the plan in
`docs/superpowers/plans/2026-11-02-plan-1-core-and-filing.md`).

The owner talks to a Telegram bot. Every incoming message is saved raw before
any AI step, so nothing is lost when the AI is slow, busy or down.

## Calling it from code  [Tasks 7-9, 11]

The Hermes adapter (Task 12, see *Telegram through Hermes*) and the CLI
(Task 11) call the same objects the acceptance tests do. `stash.app` is the only module that builds the
adapters; everything else receives them.

    from stash.app import build_app
    from stash.capture import IncomingMessage, reply_for
    from stash.config.loader import load_config

    config = load_config(path, os.environ)
    app = build_app(config)            # the only place adapters are built

    result = app.pipeline.handle(IncomingMessage(source, text, media_paths, received_at))
    # Filed | IsRequest | Deferred | Duplicate
    reply = reply_for(result)          # Filed | Deferred -> Reply (text and buttons)
    bursts = app.burst_factory()       # BurstCoalescer(config.burst_window_seconds)
    bursts.add(result, now)            # Filed and Deferred only
    reply = bursts.due(now)            # Reply | None
    answer = app.fixes.apply("stash:t:<item id>")   # Reply | Reroute
    app.pipeline.retry_pending()       # list[ProcessResult]
    app.gpu_switch.turn_off(app.local_now())   # GpuSwitchResult(until, warnings); also turn_on(), status(app.local_now())
    app.close()                        # closes the database

Switch the GPU off only through `app.gpu_switch.turn_off(app.local_now())`,
which also unloads the model; `app.gpu` (the raw gate) and `app.router` are
exposed for read-only use (status, model routing) and for tests. The time
given to `app.gpu_switch.status` and `turn_off` must be `app.local_now()`
(the clock in the owner's zone), because the status text is formatted in the
zone of that time. `app.today()` is the owner's calendar day, which names the
day's backup. `GpuSwitchResult.warnings` is empty unless the model could not be
unloaded, in which case it carries one line saying so.

`app.pipeline` never runs `handle`, `process` and `retry_pending` at the same
time inside one process (they take turns); a second process such as
`stash retry` is safe because filing is idempotent (item id == capture id).
Tests build the same app with `build_app(config, client=<MockTransport client>,
run=<fake nvidia-smi runner>, which=<fake PATH lookup>)`.

## Telegram through Hermes  [Task 12]

`stash.hermes_adapter` is the only package that knows Hermes. Hermes loads
`deploy/hermes-plugin/stash/` (a symlink at `~/.hermes/plugins/stash`), whose
`__init__.py` puts the repository's `src` on `sys.path` and calls
`stash.hermes_adapter.plugin.register(ctx)`:

    from stash.hermes_adapter.plugin import register

    register(ctx)    # ctx is Hermes' plugin context; builds the app from the plugin's
                     # `config_path` setting (default ~/.config/stash/stash.toml)

Secrets and the owner list come from Hermes' secret store, then the process
environment: `OPENROUTER_API_KEY` for the AI provider and `TELEGRAM_ALLOWED_USERS`
(comma-separated Telegram user ids) for who the owner is. Hermes and
`telegram` are imported lazily, inside functions, only by this package.

Each statement below has one acceptance test, in
`tests/acceptance/test_hermes_registration.py`, `test_hermes_capture.py`,
`test_hermes_buttons.py`, `test_hermes_commands.py` and `test_hermes_tools.py`
(all on fakes: a fake Hermes context, a fake outbox and a fake assistant).

### Registration

1. `register(ctx)` registers the `pre_gateway_dispatch` hook, a handler for the
   `telegram` platform, the commands `/list`, `/gpu` and `/retry`, and the tools
   `stash_search` and `stash_list` in the toolset `stash`. A command name that
   Hermes refuses because a built-in owns it (`/retry` is one) is registered with a
   hyphenated prefix, `stash-retry`, and the log says so. In Telegram you type
   `/stash_retry`: the gateway turns underscores into hyphens before looking a plugin
   command up, so an underscore in the registered name would never be found.
2. An unreadable or invalid configuration makes `register` raise the
   `ConfigError`, so the failure shows in Hermes' log instead of messages being
   silently left to the agent.

### Messages (the hook)

The hook runs before Hermes authorises the sender, so stash checks the owner
itself.

1. A plain message from the owner is saved raw and the hook answers
   `{"action": "skip"}`, so the agent never sees it. After the burst window the
   owner gets one reply with the confirmation and its buttons.
2. A message whose text starts with `/` answers `{"action": "allow"}` and stores
   nothing: Hermes runs the command.
3. A message from anybody else answers `{"action": "allow"}`; nothing is stored
   and nothing is sent, so Hermes' own authorisation decides what they get.
4. The same Telegram message delivered twice is one capture, one item, one
   reply; the second delivery answers `skip` and sends nothing.
5. Several messages inside the burst window get one combined
   `✅ Saved 3 items:` reply. An item that is processed twice in one window
   (a `/retry` overlapping the background filing) is listed once; that rule
   lives in `BurstCoalescer.add` (unit-tested there).
6. When the AI is down the owner gets `📥 Saved — I'll file it once the AI is
   reachable.`; the capture stays pending.
7. A message the AI routes as a question creates no item and is handed to the
   assistant (`ctx.inject_message`); stash sends no reply of its own. If Hermes
   refuses the hand-over the owner is told so.
8. If the raw save itself fails the owner is told `⚠️ I could not save that
   message — please send it again.` and the hook answers `skip`.
9. If filing raises unexpectedly it is logged, nothing is sent and the capture
   stays pending for `/retry`.

Pinned by unit tests: a message with an unusable media path (for example
containing `..`) is still saved, without the media; a message without a user
id, without text and media, or with a missing message id is handled as above
(passed through, or given a generated id).

### Buttons

Every callback is scoped to data starting `stash:`, so Hermes' own buttons keep
working; stash always acknowledges a press.

1. Pressing `Type`, then `Recipes`, edits the same message to the updated
   confirmation.
2. Pressing `That was a question →` hands the original text to the assistant.
3. A press from anybody but the owner is acknowledged and otherwise ignored.
4. A stale or forged press edits the message to `That item no longer exists.`

Pinned by unit tests: Telegram refusing an edit (message unchanged) is logged
and never raises; a press whose question cannot be handed to the assistant
tells the owner.

### Commands

Replies are plain text, at most 4096 characters.

1. `/list` prints the newest items as `<Type> · <title> · <Stage>`; `/list
   want_to` filters by stage; with nothing to show it says `No items.`; an
   unknown stage lists the valid ones.
2. `/gpu status`, `/gpu off` and `/gpu on` answer as `stash gpu` does (see
   *stash gpu*); `/gpu` alone is `status`; anything else prints the usage.
3. `/retry` files the pending captures and prints one line each, or
   `Nothing pending.`

### Agent tools

Both tools return a JSON string and never raise. Titles come from the owner's
own captures and are data, not instructions.

1. `stash_search {query}` returns `{"items": [{"id", "type", "title", "stage",
   "date"}]}` for a case-insensitive match (the same search as the store).
2. `stash_list {stage?, item_type?, limit?}` returns the same shape, newest
   first, `limit` between 1 and 50 (default 20).
3. A blank query, an unknown stage or type, a non-integer limit, or a store
   that fails answers `{"error": "..."}`.

### Telegram I/O

Pinned by unit tests (real `python-telegram-bot` objects, no network): a reply
becomes an `InlineKeyboardMarkup` whose `callback_data` equals each button's
data; sending uses `send_message`, editing `edit_message_text`; the callback
handler matches `stash:` data only; a callback query is answered before
anything else.

### The plugin shim

1. The shim finds the repository's `src` through a symlink (integration test
   with a real temporary symlink; Hermes is not imported).

Deferred: nothing retries pending captures on a timer yet (Plan 3's scheduler);
`/retry` does it by hand. The raw copy of a question is marked `request` rather
than deleted. Everything Hermes-specific that the code assumes and the suite
cannot check is listed in `docs/spike-m0.md` (items 13-21).

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

5. yt-dlp is only asked about links from a known platform (`instagram`,
   `youtube`, `tiktok`, `x`, `reddit`) and its generic extractor is switched
   off; any other link (`web`) is read only by the page reader. Acceptance
   tests in `tests/acceptance/test_link_inspection_app.py` (a message sent
   through `build_app`'s pipeline: a web link, then a youtube link).
6. When inspecting a link takes longer than 25 seconds in total (a hung
   extractor or page), the result is unknown and the capture is filed from the
   owner's own words. Acceptance test in the same file (an app built with a
   hung extractor and a 5 ms deadline).

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

## Command line  [Task 11]

Every subcommand takes `--config PATH`; without it `$STASH_CONFIG`, then
`~/.config/stash/stash.toml` is used. Output goes to the injected stream, so the
acceptance tests in `tests/acceptance/test_cli.py` read it directly (they call
`main([...], factory=...)` with an app built on a fake HTTP transport).

1. An invalid or unreadable configuration exits 2 and prints the
   `ConfigError` message on standard error, for every subcommand.
2. A database that cannot be opened is reported the same way (exit 2).

## stash doctor  [Task 11]

Prints one line per check, `✔ name — detail` when it passes, `✖` when a
required check fails and `!` when an optional one does. Exit 1 when a required
check fails, otherwise 0. Checks: `config`, `database`, one line per configured
provider (`ollama`, `openrouter`; required when any task or the busy fallback
uses it; the `ollama` line also checks the model is pulled), `openrouter model`, then the optional
`nvidia-smi`, `yt-dlp`, `deno` and `tesseract`. Acceptance tests in
`tests/acceptance/test_cli_doctor.py`:

1. With a reachable Ollama that has the model, every required line is `✔` and
   the exit code is 0, even when optional tools are missing (shown as `!`).
2. A rejected OpenRouter key prints `✖ openrouter — invalid key` and exits 1.
3. A configured Ollama model that is not pulled prints
   `✖ ollama — model <m> is not pulled (ollama pull <m>)` and exits 1.
4. An OpenRouter model id that OpenRouter does not list prints
   `✖ openrouter model — model <id> is not offered by OpenRouter` and exits 1.
5. A provider that is configured but unused is checked too, but its failure is
   an optional `!` line and does not change the exit code.

Assumption not yet verified (the sandbox blocks openrouter.ai): the model list is
`GET <base_url>/models` returning `{"data": [{"id": "..."}]}`; confirm in the
M0 spike (`docs/spike-m0.md`).

Pinned by unit tests: a check that raises is reported as a failed line, never
crashes the run; line rendering; `Doctor.run` keeps the order given.

## stash list  [Task 11]

`stash list --stage want_to --type place --limit 20` prints matching items,
newest first, one line each: `<Type> · <title> · <Stage>` with the date appended
when there is one. Acceptance tests:

1. Filters narrow the list and the limit caps it.
2. With nothing to show it prints `No items.` and exits 0.

## stash retry  [Task 11]

Files every pending capture and prints one line for each (`filed`, `request`,
`deferred (gpu_busy)` or `deferred (ai_unavailable)` followed by the title or the
start of the text). Acceptance tests:

1. Pending captures are filed once the GPU is free; running it again prints
   `Nothing pending.`
2. While the GPU is busy the lines say `deferred (gpu_busy)`, the captures stay
   pending and the exit code is 0.

## stash gpu  [Task 11]

`stash gpu status | off | on`, times shown in the configured timezone.
Acceptance tests:

1. `off` prints `GPU switched off until HH:MM` and tells Ollama to unload its
   model (`keep_alive: 0`); `status` then reads `GPU busy — turned off until HH:MM`.
2. `on` prints `GPU switched on` and `status` reads `GPU free — GPU is free`
   (or the real reason when other apps use it).
3. `off` still switches the gate off when Ollama cannot be reached; it adds a
   `! could not unload the model: ...` line and exits 0.

## Local-model eval  [Task 10]

`evals/cases.jsonl` holds 25 fake cases (17 text filings, 5 routing questions
of which 2 are ambiguous, 3 images whose PNGs are generated by
`evals/make_images.py`). One JSON object per line:

    {"id": "t01", "arm": "text", "text": "...", "link": null,
     "expect": {"route": "capture", "item_type": "place", "stage": "want_to",
                "date": null, "details": {"city": "Tokyo"}}}

`"link"` is `null` or `{"url", "title", "description"}` (optional `uploader`,
`duration_s`, `has_captions`); image cases carry `"arm": "image"`, the note in
`"text"` and `"image": "images/<name>.png"` relative to the cases file.
Omitted `item_type`, `stage`, `date` and empty `details` are not scored.
Each statement has one unit test (`tests/unit/evaluation/`):

1. `load_cases` reads that format; a bad line raises `ValueError` naming the
   line (`line 2 ...`); the shipped `evals/cases.jsonl` loads and has 25 cases
   in the stated mix, every image file present.
2. A case passes a field when the filing agrees: route, type, stage and date
   by equality, details when each expected value is a case-insensitive
   substring of the filed value.
3. The text arm runs text cases through the filer; the vision arm sends the
   image to the vision model; the OCR arm reads the image to text first and
   files that text. Vision and OCR run image cases only.
4. A model that is unavailable (or OCR that fails) marks the case as an error
   and fails every field it would have scored.
5. `render_report` prints one Markdown table per arm with a column per model
   label and rows for route, type, stage, date and details accuracy (a
   percentage), p50 latency and error count.

Acceptance test in `tests/acceptance/test_cli_eval.py`: `stash eval
--providers ollama,openrouter --arms text,ocr --cases <file> --out <path>`
prints and saves the table with a column for each provider, never touching the
network (fake transport); an unknown provider exits 2.
The eval talks to the models directly, bypassing the GPU gate: do not run it
while gaming (acceptance test in `tests/acceptance/test_cli_eval.py`: with the
GPU busy the eval still gets answers from the models). The OCR arm needs `tesseract`; without it that arm reports
errors for every image case.

## stash eval  [Task 11]

`stash eval --providers ollama,openrouter --arms text,vision,ocr --cases evals/cases.jsonl --out PATH`
(all configured providers and all arms by default) runs the case set against
each provider, with OpenRouter as the reference, and prints the Markdown
comparison table (see *Local-model eval*).

## stash backup  [Task 11]

`stash backup --to DIR` writes `stash-YYYYMMDD.db` (today's date in the
configured timezone) and keeps the newest 30 `stash-*.db` files; other files in
DIR are left alone. The copy is written to a temporary file in DIR and renamed
into place, so an interrupted backup never replaces a good file with a partial
one. Acceptance tests in `tests/acceptance/test_cli.py` (through the command);
the same two statements are pinned on the files themselves in
`tests/unit/store/test_backups_usage.py`:

1. The backup file is a readable copy that holds the items.
2. With 31 older backups present, writing today's leaves 32 files and the two
   oldest are removed, so 30 remain.

Pinned by unit tests: a failed copy leaves no temporary file and keeps the
previous backup; running twice on one day replaces that day's file; names that
only look like backups are not touched.

## Storage guarantees  [Tasks 2-3]

These have no caller-visible surface yet; they are pinned by unit and contract
tests and surface through the sections above.

- A capture is stored raw before filing; a second capture from the same chat
  message is refused and nothing is written.
- Items round-trip with details, tags, people and date intact, and list newest
  first.
- Search is a case-insensitive substring match over title, note and tags.
- Reopening the database keeps the data and does not re-run migrations.
