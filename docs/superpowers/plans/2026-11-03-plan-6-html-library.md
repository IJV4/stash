# stash Plan 6 — HTML library (M6)

> **For agentic workers:** Python only through
> `python-development:python-coding-orchestrator`; the main loop commits.
> Requires Plan 2 (library and outcomes); uses Plan 5 summaries if present.
> Steps use checkbox (`- [ ]`) syntax.

**Goal:** A read-only HTML view of your library and history. `/library html`
sends it as one self-contained file in Telegram, and it is also served,
always current, on the home network.

**Architecture:**
- A pure renderer `stash.library_html`: stdlib string building plus
  `html.escape`, with no template-engine dependency.
- Telegram document sending: `TelegramBot.send_document`, plus
  `Outbox.send_file`.
- A separate `stash serve` process (stdlib `ThreadingHTTPServer`, a systemd
  user service), so a web bug can never take down the gateway.

**Tech Stack:** unchanged (stdlib only).

**Spec:** design doc → Browsing; Constraints (home network, nothing published).

## Global Constraints

- Plan 1–2 constraints apply.
- **Self-contained and inert:**
  - one HTML file with inline CSS and no JavaScript;
  - no external resources (fonts, images, scripts);
  - `<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'">`;
  - `<meta name="robots" content="noindex">`.
- Every piece of stored text is escaped with `html.escape(quote=True)`. That
  includes titles, notes, takeaways, summaries and URLs. Links render only for
  `http(s)` URLs, with `rel="noopener noreferrer"`.
- **Private by default (builder call):**
  - The LAN server requires an access token, as `?k=<token>` or a cookie set
    after the first visit.
  - The token is the env `STASH_LIBRARY_TOKEN` (≥ 24 chars). Without it,
    `stash serve` refuses to start.
  - It binds `[library] bind = "0.0.0.0"`, `port = 8765`.
  - A wrong or missing token → 404 (no hint).
  - Only `GET /` and `GET /healthz` exist.
- **People data never appears** (Plan 4 constraint). Dropped items appear only
  in a collapsed "Dropped" section with their reason.
- Telegram documents are limited to 50 MB. A library over 45 MB is refused with
  the message `"Library too big to send — open it on the home network."`

## Review Focus

1. **Stored XSS:** a title such as `<script>…`, a takeaway with
   `"><img onerror=…>`, or a `javascript:` URL renders as inert text. Tests
   assert there are no `<script`, no `on…=` attributes and no `javascript:` in
   the output.
2. **Token handling:**
   - The token is compared in constant time (`hmac.compare_digest`).
   - The cookie is `HttpOnly; SameSite=Strict`.
   - The token is never logged, and query strings are stripped from the access
     log.
3. **A database being written while serving** (WAL): pages render from a
   consistent snapshot, and a locked database → 503, not a crash.
4. **An empty library and a 5 000-item library** both render. The large one
   stays under 45 MB, with paging inside sections (show the latest 200 per
   section).
5. **Path traversal or odd requests** (`/../`, `HEAD`, `POST`, a 10 MB request
   line) → 404/405/414, with nothing read from disk.

---

### Task 1: Renderer

**Files:** Create `src/stash/library_html/{__init__,model,render,styles}.py`.
Tests: `tests/unit/library_html/test_render.py` and `test_escaping.py` (RF1),
plus `tests/acceptance/test_library_html.py`.

**Interfaces:**
- `LibrarySnapshot(generated_at, kept: Mapping[ItemType, list[LibraryEntry]],
  done_by_year: Mapping[int, list[LibraryEntry]], want_to: Mapping[ItemType, list[Item]],
  dropped: list[Item])`.
- `LibraryEntry(item, outcomes, media_notes | None)`.
- `build_snapshot(store, today, per_section=200) -> LibrarySnapshot`. It uses
  only the store ports: `library`, `done_between`, `list_items`, `outcomes_for`
  and `get_media_notes` (when Plan 5 exists; otherwise None).
- `render_library(snapshot, *, title="My stash") -> str`.
  - Sections, in order:
    1. **Kept**, grouped by type: recipes, books (with takeaways), places,
       media (summary and takeaways), others.
    2. **Done** by year, newest first, with ⭐ ratings and dates.
    3. **Want to**, grouped by type.
    4. **Dropped**, collapsed in `<details>`.
  - A header shows counts and "Generated {local datetime}".
  - Mobile-friendly CSS with `prefers-color-scheme` light/dark.
- [ ] **Step 1: Failing tests:**
  - RF1 payloads.
  - Section order and counts.
  - An empty library shows "Nothing here yet."
  - The 5 000-item fake library stays under 45 MB and each section is capped at
    200 with "…and N more" (RF4).
- [ ] **Step 2–4:** Implement; architecture guard (`library_html` is a
  presentation package, like `rendering`); `make check`.
- [ ] **Step 5: Commit** `feat(library): self-contained HTML library renderer`.

### Task 2: Send as a Telegram file + local copy

**Files:** Modify `hermes_adapter/{telegram_io,outbox,commands,wiring}.py`,
`src/stash/cli/*` (`stash library --html PATH`) and `app/*`. Tests: the
telegram_io unit tests (a `send_document` contract against PTB 22.8 kwargs),
the command tests, `tests/acceptance/test_hermes_library_file.py` and
`tests/acceptance/test_cli_library_html.py`.

**Interfaces:**
- `TelegramBot` gains `async send_document(*, chat_id: str, document: InputFile | bytes, filename: str, caption: str | None = None)`.
- `Outbox.send_file(chat_id, filename, data: bytes, caption) -> None`.
- `/library html` renders the snapshot in a thread, writes
  `data_dir/library/latest.html` atomically, and sends
  `stash-library-YYYY-MM-DD.html` with the caption `"📚 Your stash library"`.
  Over the size limit → the refusal text.
- `/library` without arguments keeps the Plan 2 text listing.
- `stash library --html PATH` writes the file atomically and refuses to
  overwrite non-`.html` paths.
- [ ] **Step 1: Failing tests:**
  - The document is sent with the right filename and caption.
  - The local copy is written.
  - An outbox failure is logged and the command still replies with an error
    line.
- [ ] **Step 2–4:** Implement; `make check`. **Step 5: Commit** `feat(library): send the HTML library in Telegram`.

### Task 3: `stash serve` on the home network

**Files:** Create `src/stash/library_html/server.py` (an adapter) and the CLI
`serve` command; add `deploy/systemd/stash-serve.service` and update
`docs/deploy/wsl-setup.md` (mirrored networking, the Windows Firewall inbound
rule for TCP 8765 on Private networks only, bookmarking the tokenized URL).
Modify `config` (`[library] bind`, `port`) and `deploy/stash.toml.example`.
Tests: `tests/integration/test_library_server.py` (a real server on
127.0.0.1:0, offline) and `tests/unit/library_html/test_auth.py`.

**Interfaces:**
- `LibraryServer(snapshot_source: Callable[[], str], token: str, bind, port, clock)`,
  with `serve_forever()` and `shutdown()`.
- Request handling:
  - `GET /?k=<token>` → 200 HTML plus `Set-Cookie: stash_k=…; HttpOnly; SameSite=Strict; Path=/`.
  - `GET /` with the cookie → 200.
  - `GET /healthz` → `ok`, without auth.
  - Everything else → 404/405/414 (RF5).
  - A database lock → 503 (RF3).
- `Cache-Control: no-store`, `X-Content-Type-Options: nosniff`,
  `Referrer-Policy: no-referrer`, `X-Frame-Options: DENY`.
- `stash serve`: starts after loading the config and finding
  `STASH_LIBRARY_TOKEN`; otherwise exits 2 with a message saying how to set it.
- `doctor` gains an optional `library server` line (GET `/healthz` on the
  configured port).
- [ ] **Step 1: Failing tests:** RF2 (the compare path, the cookie flags, no
  token in the log), RF3 and RF5 against the real local server.
- [ ] **Step 2–4:** Implement; `make check`.
- [ ] **Step 5:** Update `docs/usage.md` ("The HTML library") and
  `docs/spike-m0.md` (reach `http://<pc-ip>:8765/?k=…` from the phone on Wi-Fi;
  confirm it is not reachable on the guest network, if there is one).
- [ ] **Step 6: Commit** `feat(library): token-protected LAN library server`.
