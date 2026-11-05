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
(all on fakes: a fake Hermes context that refuses injection into a chat with no
admitted human message (a command or a non-owner message does not admit it),
and a fake outbox; the assistant is the real `GatewayAssistant` over that fake
context, except in the two button tests that record what was asked).

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
3. The registered hook answers `{"action": "allow"}` for a question and Hermes
   is asked to inject nothing (`test_a_question_dispatched_through_hermes_is_allowed_and_nothing_is_injected`).
4. The `That was a question →` button on a confirmation that Telegram delivered
   goes through the registered Telegram handler to the same hand-over. In a
   chat with no `allow`ed message the owner is told `I couldn't pass that on to
   the assistant. Send it again starting with ? and I'll hand it over.` and
   nothing is injected.
   (`test_that_was_a_question_pressed_through_telegram_apologises_with_no_allowed_question`)
5. After an `allow`ed question in the same chat the same press, through the
   registered handler, is injected into Hermes and no apology is sent.
   (`test_that_was_a_question_pressed_through_telegram_injects_the_text_after_a_question`)

Re-registration is safe. A plugin hot-reload (any `hermes plugins enable/disable`
on a running gateway) makes Hermes call `register(ctx)` again in the same process,
but Hermes keeps the Telegram handler factory it already has and does not call the
new one: factories are deduplicated by plugin and function qualname (observed on
the PC, ADR 0001). stash keeps the Telegram connection, the button handler and the
open app in one process-wide `AdapterState`, so the second `register` reuses them.
The configuration file is read once per process (a changed `stash.toml` still
needs a gateway restart); the owner list (`TELEGRAM_ALLOWED_USERS`) is read again
on every `register`.

Assumed until `docs/spike-m0.md` #24 is run, and modelled that way by the offline
fake (`FakeHermesContext.reloaded()`): `AdapterState` outlives the reload; the
second `register` gets a new context; the Telegram handler factories and chat
admission carry over from before the reload; the hook, commands and tools are
replaced, not duplicated.

6. After a second `register`, the owner's message is still confirmed through
   Telegram.
   (`test_after_a_second_register_the_owners_message_is_still_confirmed_through_telegram`)
7. After a second `register`, pressing a button on that confirmation edits the
   message. (`test_after_a_second_register_a_button_press_edits_its_confirmation`)
8. After a second `register`, the commands answer in the reloaded context.
   (`test_after_a_second_register_the_commands_answer_in_the_reloaded_context`)
9. A second `register` opens no second app: one app (one database connection)
   stays open, and the one exit hook closes it.
   (`test_after_a_second_register_one_app_stays_open`)
10. After a second `register`, when Telegram reconnects with a new application,
    pressing a button on the confirmation that application delivered edits it
    through the same application.
    (`test_after_a_second_register_a_new_telegram_application_confirms_and_edits_through_it`)
11. A second `register` before Telegram first connects still leaves the owner's
    message confirmed once Telegram connects.
    (`test_a_second_register_before_telegram_first_connects_still_confirms_the_owners_message`)

Pinned by unit tests: the Telegram handler is safe to call again (Hermes also
calls it on every reconnect). `TelegramAttachment` adds no second button handler
when called again with the same Telegram application, and attaches to a new one,
with replies going to the new bot. A button press after a re-registration is
answered by the newest registration. A second `register` with a new
`TELEGRAM_ALLOWED_USERS` answers the new owner, and does not read the
configuration file again.

### Messages (the hook)

The hook runs before Hermes authorises the sender, so stash checks the owner
itself. It saves every owner message raw first, then classifies it **inside the
hook** (the hook waits for the AI), then answers. Each statement names its
acceptance test, in `tests/acceptance/test_hermes_capture.py` except statements
10, 11, 15 and 16 (the `?` rule), which are in
`tests/acceptance/test_hermes_forced_questions.py`.

1. A plain message from the owner is saved raw, classified, and the hook answers
   `{"action": "skip"}`, so the agent never sees it. After the burst window the
   owner gets one reply with the confirmation and its buttons.
   (`test_a_plain_message_from_the_owner_is_skipped_and_confirmed_after_the_burst_window`)
2. A message whose text starts with `/` answers `{"action": "allow"}` and stores
   nothing: Hermes runs the command.
   (`test_a_message_starting_with_a_slash_is_allowed_through_and_stores_nothing`)
3. A message from anybody else answers `{"action": "allow"}`; nothing is stored
   and nothing is sent, so Hermes' own authorisation decides what they get.
   (`test_a_message_from_anybody_else_is_allowed_through_stores_nothing_and_sends_nothing`)
4. The same Telegram message delivered twice is one capture, one item, one
   reply; the second delivery answers `skip` and sends nothing.
   (`test_the_same_telegram_message_delivered_twice_is_one_item_and_one_reply`)
5. Several messages inside the burst window get one combined
   `✅ Saved 3 items:` reply. An item that is processed twice in one window
   (a `/retry` overlapping the filing) is listed once; that rule lives in
   `BurstCoalescer.add` (unit-tested there).
   (`test_several_messages_inside_the_burst_window_get_one_combined_reply`)
6. When the AI is down the owner gets `📥 Saved — I'll file it once the AI is
   reachable.`; the capture stays pending.
   (`test_when_the_ai_is_down_the_owner_is_told_it_is_saved_and_the_capture_stays_pending`)
7. When the AI goes down between the raw save and the classification the hook
   answers `skip`, the capture stays pending, and nothing reaches the agent.
   (`test_when_the_ai_goes_down_after_the_raw_save_the_hook_skips_and_the_agent_gets_nothing`)
8. A message the AI routes as a question creates no item and the hook answers
   `{"action": "allow"}`: Hermes runs a normal agent turn on the owner's own
   message, unchanged. stash injects nothing and sends no reply of its own.
   (`test_a_question_is_allowed_through_to_the_agent_and_creates_no_item_and_no_reply`)
9. In a burst of five messages with one question among them, the question's
   message answers `allow` and the other four answer `skip`; the owner gets one
   combined `✅ Saved 4 items:` reply for the four captures.
   (`test_a_burst_with_one_question_allows_it_and_confirms_the_four_captures_together`)
10. A message that starts with `?` (after leading whitespace) is routed as a
    request by the core pipeline (see "Asking a question"): it is saved raw,
    marked as a request with no AI call, and the hook answers `allow`. Hermes
    receives the message unchanged, `?` included (`?` alone and
    `  ? what can I do` both qualify).
    (`test_a_message_starting_with_a_question_mark_is_a_request_without_asking_the_ai`)
11. A message that merely contains `?` (a link such as
    `https://x.test/a?b=1`) is classified like any other: the AI is asked, the
    hook answers `skip` and the item is filed.
    (`test_a_link_containing_a_question_mark_is_classified_and_filed_not_forced`)
12. If Hermes redelivers a question (same message id) the first delivery
    answers `allow` and the second answers `skip`, so the agent answers once.
    (`test_a_redelivered_question_reaches_the_agent_only_once`)
13. If the raw save itself fails the owner is told `⚠️ I could not save that
    message — please send it again.` and the hook answers `skip`.
    (`test_when_the_raw_save_fails_the_owner_is_told_to_send_it_again_and_the_hook_skips`)
14. If processing a capture raises unexpectedly (the log names the capture id,
    never its text) the hook answers `skip`, nothing is sent, and the capture
    stays pending for `/retry`.
    (`test_when_filing_raises_nothing_is_sent_and_the_capture_stays_pending`)
15. If processing a forced question raises, the hook answers `allow` (the
    raw copy is saved and Hermes still gets the owner's message), the failure
    is logged by capture id only, nothing is sent and the capture stays pending;
    a later retry marks it as a request and files nothing.
    (`test_a_forced_question_whose_processing_raises_is_allowed_and_retried_as_a_request`)
16. If a retry processes a pending `?` capture between the hook's raw save and
    the hook's own processing, the retry marks it as a request and files
    nothing, the hook still answers `allow` once, and nothing is injected or
    sent by the retry path.
    (`test_a_retry_racing_the_hook_on_a_forced_question_files_nothing_and_hook_allows_once`)

Pinned by unit tests: the verdict for each processing result and for a raised
exception (`tests/unit/hermes_adapter/test_intake_routing.py`), where a failure
answers `allow` for a forced question and `skip` for any other message; the
hook always classifies through `process`, on a worker thread, and has finished
when it returns; the pipeline routes a `?` capture as a request, first time or
on retry, without a model call, a link inspection or an item (resumed items
first); the `SerializedPipeline` does not make a `?` capture wait for another
message's classification; a message with an unusable media path (for example containing
`..`) is still saved, without the media; a message without a user id, without
text and media, or with a missing message id is handled as above (passed
through, or given a generated id).

Unverified until the PC checks it (`docs/spike-m0.md` #23): whether Hermes
times out a hook that waits 25-45 s for classification, and whether a slow hook
delays other messages.

### Buttons

Every callback is scoped to data starting `stash:`, so Hermes' own buttons keep
working; stash always acknowledges a press. All in
`tests/acceptance/test_hermes_buttons.py`.

1. Pressing `Type`, then `Recipes`, edits the same message to the updated
   confirmation.
2. Pressing `That was a question →` hands the original text to the assistant.
3. A press from anybody but the owner is acknowledged and otherwise ignored.
4. A stale or forged press edits the message to `That item no longer exists.`
5. The hand-over uses `ctx.inject_message`, which Hermes accepts only in a chat
   that has already had a human message admitted. In a chat with none the
   owner is told `I couldn't pass that on to the assistant. Send it again
   starting with ? and I'll hand it over.` and nothing is injected.
   (`test_pressing_that_was_a_question_with_no_admitted_message_in_the_chat_apologises`)
6. After an `allow`ed question in the same chat the same press is injected.
   (`test_pressing_that_was_a_question_after_an_allowed_question_injects_the_text`)

Pinned by unit tests: Telegram refusing an edit (message unchanged) is logged
and never raises; a press whose question cannot be handed to the assistant
tells the owner; the apology text is exactly the one above, for a refused and
for a raising injection.

### Commands

Replies are plain text, at most 4096 characters.

1. `/list` prints the newest items as `<Type> · <title> · <Stage>`; `/list
   want_to` filters by stage; with nothing to show it says `No items.`; an
   unknown stage lists the valid ones.
2. `/gpu status`, `/gpu off` and `/gpu on` answer as `stash gpu` does (see
   *stash gpu*); `/gpu` alone is `status`; anything else prints the usage.
3. `/retry` files the pending captures and prints one line each, or
   `Nothing pending.` A pending capture starting with `?` prints a `request`
   line, files nothing and asks the AI nothing
   (`test_retry_command_answers_a_pending_question_as_a_request_and_asks_the_ai_nothing`).

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
cannot check is listed in `docs/spike-m0.md` (items 13-24).

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
7. When a link was described, the saved item's `details` gain `link_title`,
   `uploader` and `duration` (`H:MM:SS`, or `M:SS` under an hour; a 0-second
   video is `0:00`), each only when known. They are facts from the source and
   override a model-written detail with the same key; the model's own `title`
   is unchanged. Each value has non-printable characters replaced by spaces,
   whitespace collapsed and is clipped to the details value limit. The facts
   count toward the 20-detail cap: when the model filled it, its last details
   make room. A message without a link, or a link that is unknown, keeps
   exactly the details the model wrote. Acceptance test in `tests/acceptance/test_link_inspection_app.py`
   (a youtube link whose model answer wrote its own `uploader`).

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
3. A message that starts with `?` (after leading whitespace) is a request
   without asking the AI: no link is inspected, no model is called, no item is
   created and the capture is marked as a request. `?` alone qualifies;
   `https://x.test/a?b=1` and `what time is it?` do not start with it and are
   classified as usual. Every path that processes a capture follows the rule:
   `handle`, `retry_pending`, `stash retry` and `/stash_retry`.
   (`test_a_message_starting_with_a_question_mark_is_handled_as_a_request_without_the_ai`
   in `tests/acceptance/test_capture_requests_and_fixes.py`; for `stash retry`,
   `test_retry_of_a_pending_question_mark_capture_prints_a_request_line_and_asks_the_ai_nothing`
   in `tests/acceptance/test_cli.py`; for `/stash_retry`,
   `test_retry_command_answers_a_pending_question_as_a_request_and_asks_the_ai_nothing`
   in `tests/acceptance/test_hermes_commands.py`)

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
- `[llm.thinking]` sets model thinking per task. Keys are the tasks (`filing`,
  `suggestions`, `vision`); values are `default` or `off`. With no table, or for
  an unlisted task, `LlmConfig.thinking_for(task)` is `Thinking.DEFAULT`.
- `[llm.thinking] filing = "off"` gives `thinking_for(LlmTask.FILING) == Thinking.OFF`.
- Any other value (`filing = "maybe"`) is a `ConfigError` naming
  `llm.thinking.filing`; an unknown key (`chat = "off"`) is a `ConfigError`
  like any unknown key.
- The setting covers stash's own LLM calls only; Hermes agent turns use Hermes's
  provider config.

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
10. With `[llm.thinking] filing = "off"`, the model the app routes filing to
    sends Ollama a request carrying `"reasoning_effort": "none"`.

How `off` reaches each provider is pinned by contract tests
(`tests/contract/test_openai_compat_thinking.py`), not acceptance tests:
`OpenAICompatibleChat(settings, client, model=None, thinking=Thinking.OFF)` adds
`"reasoning_effort": "none"` for Ollama and `"reasoning": {"effort": "none"}`
for OpenRouter. `Thinking.DEFAULT` (the default) adds nothing: the request keys
are exactly `model`, `messages`, `temperature`, `response_format`. The router
(unit-tested) hands each task a model carrying that task's setting, including
after a busy fallback to OpenRouter, and `vision` never inherits `filing`.

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
3. A pending capture that starts with `?` prints a `request` line, files
   nothing and sends no AI request; running it again prints `Nothing pending.`
   (`test_retry_of_a_pending_question_mark_capture_prints_a_request_line_and_asks_the_ai_nothing`
   in `tests/acceptance/test_cli.py`)

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

### Thinking on/off  [thinking-control Task 2]

`stash eval --providers ollama --thinking default,off` runs every chosen
provider once per thinking value, providers first, then values in the order
given (`ollama default`, `ollama off`, …). Without `--thinking` the eval runs
only the configured `[llm.thinking] filing` value (`default` when unset). The
flag wins over the config: `--thinking off` with no `[llm.thinking]` table
sends the off field. One run uses one thinking value for its text model, its
`vision_model` and the image arm's fallback to the text model.
Today only filing has a production LLM call, so the `vision` and `suggestions`
settings have no effect yet outside the eval; the eval's runs follow
`--thinking` (default: the filing setting).

Each column is labelled `<provider>:<model> thinking=<value>`, for example
`ollama:qwen3.5:latest thinking=off`. When the provider has a `vision_model`, the
label names it too, because the vision arm runs it:
`<provider>:<model> vision=<vision model> thinking=<value>`, for example
`ollama:qwen3.5:latest vision=qwen2.5vl:7b thinking=off`. A comparison holds only for those
models: re-run it when a model changes (ADR 0004).

After the arm tables, the report has one section per run, its case lines in a
fenced code block so Markdown viewers show them line by line:

    ### cases — ollama:qwen3.5:latest thinking=off
    ```
    t01 text ok (0.4 s)
    t10 text FAIL stage: want planned got want_to; date: want 2027-03-14 got none (0.3 s)
    i02 vision ERROR LlmUnavailable: ollama unreachable: ConnectError (0.0 s)
    ```

Cases are listed by arm, in the `--arms` order (text, vision, ocr by
default), and in file order within each arm. Each case is one line that names
only the scored fields that failed. A missing value shows as `none`. Details
show as `key=value` pairs for the expected keys only. Each want/got value is
collapsed onto one line with every non-printable character (such as the escape
and bell characters that start terminal control sequences, or a bidi override)
replaced by a space, then clipped to 80 characters. Error text gets the same
treatment and is clipped to 200. When the model returns unusable JSON, the
filer falls back to route `unsure` and stage `inbox`. A FAIL line showing
`got unsure` together with `got inbox` most likely means bad model output, not
a wrong answer.

Statements, each with one test:

1. `--thinking default,off` gives two columns, `… thinking=default` and
   `… thinking=off`. The off run's requests carry the provider's off field
   and the default run's requests carry none (acceptance:
   `tests/acceptance/test_cli_eval.py`).
2. The cases section lists a failing case with its want and got values
   (acceptance: `t10` shows `want 2027-03-14`).
3. With no flag, the run uses the configured filing value, and the flag
   overrides the config (acceptance: `tests/acceptance/test_cli_eval.py`;
   unit: `tests/unit/cli/`, `tests/unit/evaluation/test_eval_targets.py`).
4. Pass, fail and error lines have the formats shown above, inside a fenced
   code block, and long or multi-line model output is clipped and collapsed
   (unit: `tests/unit/evaluation/test_report_cases.py`,
   `tests/unit/evaluation/test_expectation_mismatches.py`).
5. When no vision model is configured, the vision arm uses the text model and
   the chosen thinking value still applies (acceptance:
   `tests/acceptance/test_cli_eval.py`).
6. The label names the vision model when the provider has one, and has no
   `vision=` part when it does not (unit: `tests/unit/evaluation/test_target.py`,
   `tests/unit/app/test_eval_provider_targets.py`; acceptance:
   `tests/acceptance/test_cli_eval.py`).
7. Want/got values and error text carry no non-printable characters: the
   escape, bell and bidi-override characters a model or provider sends become
   spaces, so what remains is inert text (unit: `tests/unit/domain/test_printable_and_clip.py`,
   `tests/unit/evaluation/test_expectation_mismatches.py`,
   `tests/unit/evaluation/test_case_result.py`).

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
