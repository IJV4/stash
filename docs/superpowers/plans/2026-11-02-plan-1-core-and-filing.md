# stash Plan 1 — Core, providers, AI filing, Hermes adapter (M0 + M1)

> **For agentic workers:** Plan 1 was written on the Mac through
> `python-development:python-coding-orchestrator` (owner's global rule): one orchestrator per
> task group, then the main loop commits. For any later work follow `CLAUDE.md` § "Writing
> Python" (the PC has no orchestrator). Non-Python files (docs, TOML/YAML examples, SQL,
> CLAUDE.md) may be written by the main loop. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A Hermes-free `stash` core that saves every message raw, files it
with an LLM (Ollama or OpenRouter, switchable by config), replies with fix
buttons, defers work while the GPU is busy, plus an eval harness, a `stash`
CLI with `doctor`, a thin Hermes plugin adapter and a PC deploy/spike kit.

**Architecture:** Layered package `stash` (Foundation → Component → Feature →
Application). Domain value objects and ports have no I/O; adapters (SQLite,
httpx LLM client, yt-dlp, nvidia-smi, Tesseract) implement the ports; a single
composition root (`stash.app.build_app`) wires them; the CLI and the Hermes
adapter are the only entry points. Tests use in-memory fakes and
`httpx.MockTransport`; nothing in the suite touches the network.

**Tech Stack:** Python ≥3.11 (dev on 3.12.10), uv 0.13.6 (`uv_build`),
httpx 0.28.1, yt-dlp[default] 2026.10.26, pytesseract + Pillow (eval OCR arm),
stdlib sqlite3/tomllib/zoneinfo/argparse; dev: pytest 9.2.0, ruff 0.17.3,
mypy 2.4.1, python-telegram-bot 22.8 (adapter tests only — Hermes provides it
at runtime). Target runtime: Hermes Agent v0.22.6 (pinned, GitHub release; the
PyPI `hermes-agent` 0.19.0 is stale and is **not** a dependency).

**Spec:** `docs/superpowers/specs/2026-11-02-stash-design.md`

## Global Constraints

- `requires-python = ">=3.11"`; ruff `target-version = "py311"`, line length 100.
- Timezone for display/scheduling: `America/Los_Angeles`; persist datetimes as
  timezone-aware UTC ISO-8601 strings.
- Bot copy is English. Confirmation format: `✅ <Type> · <detail> · <Stage>`.
- Every incoming message is saved raw **before** any AI step.
- Only fake data in this repo (tests, evals, examples). No real personal items.
- No network in the test suite; `make check` must pass offline.
- LLM output and link metadata are untrusted input: validate, clamp, never
  execute; link text is passed to the model as delimited data.
- Ollama `/v1` has **no `tool_choice`** and cannot set context length → stash's
  own LLM calls use `response_format` JSON schema, not tools. Context length is
  an Ollama server env (`OLLAMA_CONTEXT_LENGTH=65536`).
- OpenRouter may return `{"error": …}` with HTTP 200 → treat as failure.
- httpx default timeout (5 s) is too short: LLM client uses
  `httpx.Timeout(120.0, connect=10.0)`.
- Telegram `callback_data` ≤ 64 bytes; message text ≤ 4096 chars.
- Config file: TOML (`stash.toml`); secret `OPENROUTER_API_KEY` only from env.
- Tooling commands: `make check` = `ruff format --check`, `ruff check`,
  `mypy --strict src`, `pytest -q`. Unit tests < 50 ms each; whole suite < 10 s.

## Review Focus

1. **Duplicate delivery** of the same Telegram message (gateway retry) must not
   create two captures or two items → dedupe on `(chat_id, message_id)`
   (Task 3 + Task 9 tests).
2. **Malformed or hostile LLM output** (non-JSON, unknown enum, missing title,
   `stage: "done"`, instructions injected via a link description) must still
   yield a saved item with safe defaults (Task 8 tests).
3. **Slow/cold or unreachable model** (ReadTimeout, connection refused, HTTP
   503, error-in-200) leaves the capture pending and replies "saved, will
   file it later"; a later retry files it (Task 5 + Task 9 tests).
4. **Stale or forged button presses** (unknown item, malformed callback data,
   deleted item) reply "That item no longer exists." and never raise
   (Task 9 tests).
5. **Image-only or oversized messages** (no text; 10 000-char text) are saved,
   get a derived title ≤ 120 chars, and replies stay ≤ 4096 chars
   (Task 9 tests).

---

### Task 1: Project foundation and usage document

**Files:**
- Create: `pyproject.toml`, `Makefile`, `.gitignore`, `README.md`,
  `docs/usage.md`, `CLAUDE.md`, `src/stash/__init__.py`, `src/stash/cli.py`
- Test: `tests/acceptance/test_cli_skeleton.py`

**Interfaces:**
- Produces: console script `stash = "stash.cli:main"`; `main(argv: Sequence[str] | None = None) -> int`;
  `stash.__version__ = "0.1.0"`.

- [ ] **Step 1:** Write `docs/usage.md` — the outside-in usage document: what
  the owner sends in Telegram and sees back for: a shared link, a typed
  thought, an image, a question, a fix-button press, GPU busy, AI down; plus
  `stash doctor`, `stash eval`, `stash list`, `stash retry`, `stash gpu`.
  Acceptance tests in later tasks are named after its sections.
- [ ] **Step 2: Failing test** `test_version_flag_prints_version`: `main(["--version"])`
  returns 0 and stdout is `stash 0.1.0\n`.
- [ ] **Step 3:** Run `.venv/bin/uv run pytest tests/acceptance -q` → FAIL (no module).
- [ ] **Step 4:** Create `pyproject.toml` (`build-backend = "uv_build"`,
  `requires = ["uv_build>=0.13.6,<0.14"]`; deps `httpx>=0.28.1,<0.29`,
  `yt-dlp[default]>=2026.10.26`, `pytesseract>=0.3.13`, `pillow>=11`;
  dependency-group `dev`: pytest 9.2, ruff 0.17.3, mypy 2.4.1,
  python-telegram-bot 22.8); `[tool.pytest]` (native table, `testpaths=["tests"]`);
  ruff/mypy config; `Makefile` targets `install`, `fmt`, `check`, `test`;
  `.gitignore` (`.venv/`, `*.db`, `evals/results/`, `.mypy_cache/`, `.ruff_cache/`);
  argparse `main` with `--version`.
- [ ] **Step 5:** `make check` → all green.
- [ ] **Step 6:** Main loop writes `CLAUDE.md` (via mattpocock-skills:writing-for-agents):
  layout, commands, the Global Constraints above, "Python only via
  python-development orchestrator", "fake data only".
- [ ] **Step 7: Commit** `chore: project foundation, usage doc, CLI skeleton`.

### Task 2: Domain value objects

**Files:**
- Create: `src/stash/domain/__init__.py`, `src/stash/domain/item.py`, `src/stash/domain/capture.py`
- Test: `tests/unit/domain/test_item.py`, `tests/unit/domain/test_capture.py`

**Interfaces:**
- Produces (all `@dataclass(frozen=True, slots=True)` / `StrEnum`):
  - `ItemType(StrEnum)`: `PLACE="place"`, `RECIPE="recipe"`, `PURCHASE="purchase"`,
    `LEARN="learn"`, `BOOK="book"`, `MEDIA="media"`, `IDEA="idea"`, `PLAN="plan"`,
    `ACTIVITY="activity"`, `GIFT="gift"`, `OTHER="other"`; property `label -> str`
    (`"Places"`, `"Recipes"`, `"Purchases"`, `"Learning"`, `"Books"`, `"Media"`,
    `"Ideas"`, `"Plans"`, `"Activities"`, `"Gifts"`, `"Other"`).
  - `Stage(StrEnum)`: `INBOX="inbox"`, `WANT_TO="want_to"`, `PLANNED="planned"`,
    `DOING="doing"`, `DONE="done"`, `DROPPED="dropped"`; `label` (`"Inbox"`,
    `"Want to"`, `"Planned"`, `"Doing"`, `"Done"`, `"Dropped"`).
  - `Route(StrEnum)`: `CAPTURE`, `REQUEST`, `UNSURE`.
  - `CaptureStatus(StrEnum)`: `PENDING`, `FILED`, `REQUEST`.
  - `SourceRef(chat_id: str, message_id: str)`.
  - `RawCapture(id: str, source: SourceRef, received_at: datetime, text: str,
    media_paths: tuple[str, ...], status: CaptureStatus)`; `with_status(s) -> RawCapture`.
  - `Filing(route: Route, item_type: ItemType, title: str, stage: Stage,
    details: Mapping[str, str], tags: tuple[str, ...], people: tuple[str, ...],
    date: date | None)`.
  - `Item(id: str, capture_id: str, item_type: ItemType, title: str, stage: Stage,
    source_url: str | None, note: str, details: Mapping[str, str], tags: tuple[str, ...],
    people: tuple[str, ...], date: date | None, created_at: datetime, updated_at: datetime)`;
    `retyped(t, now) -> Item`, `moved_to(stage, now) -> Item`;
    classmethod `from_filing(item_id, capture, filing, source_url, now) -> Item`.
  - `derive_title(text: str) -> str` (first non-empty line, whitespace-collapsed,
    truncated to 120 chars with `…`; `"Untitled"` when empty).

- [ ] **Step 1: Failing tests:** naive datetime in `RawCapture` raises `ValueError`;
  empty `Item.title` raises `ValueError`; `Item.moved_to(Stage.PLANNED, now)` with
  `date=None` raises `ValueError` ("planned items need a date");
  `derive_title("  \n Ramen   in Shibuya \n more")=="Ramen in Shibuya"`;
  `derive_title("x"*200)` has length 120 and ends with `"…"`; `derive_title("")=="Untitled"`;
  `ItemType.PLACE.label=="Places"`, `Stage.WANT_TO.label=="Want to"`.
- [ ] **Step 2:** `uv run pytest tests/unit/domain -q` → FAIL.
- [ ] **Step 3:** Implement the types above (validation in `__post_init__`).
- [ ] **Step 4:** Tests pass; `make check` green.
- [ ] **Step 5: Commit** `feat(domain): item, capture and filing value objects`.

### Task 3: Store port, in-memory fake, SQLite adapter

**Files:**
- Create: `src/stash/store/__init__.py`, `src/stash/store/port.py`,
  `src/stash/store/sqlite.py`, `src/stash/store/migrations/0001_init.sql`,
  `tests/fakes/memory_store.py`
- Test: `tests/contract/test_store_contract.py` (same tests, parametrized over
  both implementations), `tests/integration/test_sqlite_store.py`

**Interfaces:**
- Consumes: Task 2 types.
- Produces: `class Store(Protocol)`:
  - `add_capture(c: RawCapture) -> bool` — `False` if a capture with the same
    `SourceRef` exists (dedupe), nothing written.
  - `set_capture_status(capture_id: str, status: CaptureStatus) -> None`
  - `get_capture(capture_id: str) -> RawCapture | None`
  - `pending_captures() -> list[RawCapture]` (oldest first)
  - `save_item(item: Item) -> None` (upsert), `get_item(item_id) -> Item | None`,
    `delete_item(item_id) -> None`
  - `list_items(stage: Stage | None = None, item_type: ItemType | None = None,
    limit: int = 20, offset: int = 0) -> list[Item]` (newest first)
  - `search_items(query: str, limit: int = 20) -> list[Item]` (case-insensitive
    substring over title, note, tags)
  - `get_setting(key: str) -> str | None`, `put_setting(key: str, value: str) -> None`
  - `SqliteStore(path: Path)`; `MemoryStore()` in `tests/fakes`.
  - `SqliteStore.backup_to(target: Path) -> None` (uses `Connection.backup`).

- [ ] **Step 1: Failing contract tests:** add/get capture round-trip;
  `add_capture` of a second capture with the same `SourceRef` returns `False` and
  `pending_captures()` has one entry; status change removes it from pending;
  item upsert/get/delete; `list_items(stage=Stage.WANT_TO)` filters; ordering;
  `search_items("ramen")` matches title "Ramen in Shibuya"; settings round-trip;
  details/tags/people/date survive a round-trip.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Write `0001_init.sql` (tables `captures` with
  `UNIQUE(chat_id, message_id)`, `items` (JSON columns for details/tags/people),
  `settings`); `SqliteStore` applies migrations by `PRAGMA user_version`;
  sets `journal_mode=WAL` **before** any transaction, `foreign_keys=ON` per connection.
- [ ] **Step 4:** Implement `MemoryStore`.
- [ ] **Step 5:** Integration test: reopening a `SqliteStore` on the same file keeps
  data and does not re-run migrations; `backup_to` produces a readable copy.
- [ ] **Step 6:** Tests pass; `make check` green.
- [ ] **Step 7: Commit** `feat(store): store port, sqlite adapter, memory fake`.

### Task 4: Configuration

**Files:**
- Create: `src/stash/config.py`, `deploy/stash.toml.example`
- Test: `tests/unit/test_config.py`

**Interfaces:**
- Produces:
  - `ProviderName(StrEnum)`: `OLLAMA="ollama"`, `OPENROUTER="openrouter"`.
  - `LlmTask(StrEnum)`: `FILING="filing"`, `SUGGESTIONS="suggestions"`, `VISION="vision"`.
  - `ProviderSettings(name: ProviderName, base_url: str, model: str,
    api_key: str | None, vision_model: str | None)`.
  - `LlmConfig(provider: ProviderName, busy_fallback: Literal["wait", "openrouter"],
    providers: Mapping[ProviderName, ProviderSettings], tasks: Mapping[LlmTask, ProviderName])`;
    `provider_for(task) -> ProviderName`.
  - `GpuConfig(min_free_vram_mib: int = 9000, max_foreign_utilization_pct: int = 30,
    manual_off_hours: float = 4.0)`.
  - `StashConfig(data_dir: Path, timezone: ZoneInfo, llm: LlmConfig, gpu: GpuConfig,
    burst_window_seconds: float = 8.0)`; `db_path` property = `data_dir / "stash.db"`.
  - `load_config(path: Path, env: Mapping[str, str]) -> StashConfig`; `ConfigError(ValueError)`.

- [ ] **Step 1: Failing tests** with TOML strings written to `tmp_path`:
  minimal file (`[llm] provider="ollama"`, `[llm.ollama] model="m"`) → defaults
  `base_url="http://localhost:11434/v1"`, timezone `America/Los_Angeles`,
  `busy_fallback="wait"`; `[llm.openrouter] model="x"` + env
  `OPENROUTER_API_KEY="k"` → settings with `base_url="https://openrouter.ai/api/v1"`,
  `api_key="k"`; `provider="openrouter"` (or `busy_fallback="openrouter"`, or any
  `[llm.tasks]` entry naming openrouter) without the env key → `ConfigError`
  mentioning `OPENROUTER_API_KEY`; unknown provider name → `ConfigError` naming
  the key path; `[llm.tasks] suggestions="openrouter"` →
  `provider_for(LlmTask.SUGGESTIONS) == OPENROUTER` while FILING falls back to
  `provider`; `api_key` present in the TOML file → `ConfigError` ("put secrets in env").
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement with `tomllib`; all validation in `load_config`.
- [ ] **Step 4:** Main loop writes `deploy/stash.toml.example` matching the spec's
  `[llm]` block plus `[gpu]`, `data_dir`, `timezone`.
- [ ] **Step 5:** Tests pass; `make check` green.
- [ ] **Step 6: Commit** `feat(config): TOML config with provider switch and per-task override`.

### Task 5: LLM client, model router, provider probes

**Files:**
- Create: `src/stash/llm/__init__.py`, `src/stash/llm/messages.py`,
  `src/stash/llm/errors.py`, `src/stash/llm/openai_compat.py`,
  `src/stash/llm/router.py`, `src/stash/llm/probes.py`, `tests/fakes/chat_model.py`
- Test: `tests/contract/test_openai_compat_contract.py` (parametrized: ollama
  flavour, openrouter flavour), `tests/unit/llm/test_router.py`, `tests/unit/llm/test_probes.py`

**Interfaces:**
- Consumes: `ProviderSettings`, `LlmConfig`, `LlmTask` (Task 4); `GpuGate.is_busy(now)` (Task 6 — router takes a `BusyCheck` Protocol `is_busy(now: datetime) -> bool` so Task 5 does not import Task 6).
- Produces:
  - `TextPart(text: str)`, `ImagePart(data_url: str)`, `ChatMessage(role: Literal["system","user","assistant"], parts: tuple[TextPart | ImagePart, ...])`; `ChatMessage.text(role, s)` constructor.
  - `class ChatModel(Protocol)`: `complete_json(messages: Sequence[ChatMessage], schema: Mapping[str, object], schema_name: str) -> dict[str, object]`.
  - Errors: `LlmError(Exception)`; `LlmUnavailable(LlmError)`; `LlmDeferred(LlmUnavailable)`; `LlmBadOutput(LlmError)`.
  - `OpenAICompatibleChat(settings: ProviderSettings, client: httpx.Client, model: str | None = None)` — POST `chat/completions` with `response_format={"type":"json_schema","json_schema":{"name":schema_name,"strict":True,"schema":schema}}`, `temperature=0`; headers `Authorization: Bearer <key>` when key set, plus for OpenRouter `X-OpenRouter-Title: stash`.
  - `ModelRouter(config: LlmConfig, models: Mapping[ProviderName, ChatModel], busy: BusyCheck)`; `model_for(task: LlmTask, now: datetime) -> ChatModel` — returns the configured model; if that is Ollama and `busy.is_busy(now)`: returns OpenRouter when `busy_fallback=="openrouter"`, else a `DeferringModel` whose `complete_json` raises `LlmDeferred`.
  - `ProviderProbe(Protocol)`: `check() -> ProbeResult(ok: bool, detail: str)`; `OllamaProbe(settings, client)` (GET `<root>/api/tags`, model must be listed; root = base_url without `/v1`), `OpenRouterProbe(settings, client)` (GET `key` → ok with `limit_remaining` in detail; 401 → not ok "invalid key").
  - `OllamaControl(settings, client)`: `unload() -> None` (POST `<root>/api/generate` `{"model": m, "keep_alive": 0}`).
  - `make_http_client() -> httpx.Client` with `httpx.Timeout(120.0, connect=10.0)`.

- [ ] **Step 1: Failing contract tests** using `httpx.MockTransport` handlers (assert on the captured `httpx.Request`):
  request body has `model`, `response_format.json_schema.name == schema_name`, image parts encoded as `{"type":"image_url","image_url":{"url": data_url}}`;
  OpenRouter flavour sends `Authorization: Bearer k` and `X-OpenRouter-Title: stash`, Ollama flavour sends no Authorization;
  JSON content `'{"a":1}'` → `{"a": 1}`; content `"not json"` → `LlmBadOutput`;
  HTTP 503 / 429 / 402 → `LlmUnavailable`; HTTP 200 with body `{"error":{"code":502,"message":"down"}}` → `LlmUnavailable`;
  handler raising `httpx.ReadTimeout` or `httpx.ConnectError` → `LlmUnavailable`; HTTP 400 → `LlmError` (not Unavailable).
- [ ] **Step 2: Failing router tests** with `FakeChatModel` and a `FakeBusy(flag)`:
  per-task override picks OpenRouter for SUGGESTIONS; busy + `wait` → `LlmDeferred`; busy + `openrouter` → OpenRouter model; busy never affects an OpenRouter-configured task.
- [ ] **Step 3: Failing probe tests:** tags list without the model → not ok, detail names the missing model; key endpoint 200 → ok; 401 → "invalid key"; `OllamaControl.unload` posts `keep_alive: 0`.
- [ ] **Step 4:** Run → FAIL. **Step 5:** Implement. **Step 6:** Pass; `make check` green.
- [ ] **Step 7: Commit** `feat(llm): OpenAI-compatible client for Ollama/OpenRouter, router, probes`.

### Task 6: GPU gate

**Files:**
- Create: `src/stash/gpu/__init__.py`, `src/stash/gpu/probe.py`, `src/stash/gpu/gate.py`
- Test: `tests/unit/gpu/test_probe.py`, `tests/unit/gpu/test_gate.py`

**Interfaces:**
- Consumes: `Store.get_setting/put_setting` (Task 3), `GpuConfig` (Task 4).
- Produces:
  - `GpuSample(total_mib: int, used_mib: int, utilization_pct: int)`.
  - `GpuProbe(Protocol)`: `sample() -> GpuSample | None` (None = no NVIDIA GPU / nvidia-smi missing).
  - `NvidiaSmiProbe(run: CommandRunner)` with `CommandRunner = Callable[[Sequence[str]], str]`, running `nvidia-smi --query-gpu=memory.total,memory.used,utilization.gpu --format=csv,noheader,nounits`; `parse_nvidia_smi(output: str) -> GpuSample` (first GPU line).
  - `OwnVramUsage(Protocol)`: `own_mib() -> int`; `OllamaVramUsage(settings, client)` sums `size_vram` from `<root>/api/ps` (bytes → MiB); returns 0 on error.
  - `GpuGate(probe, own, store, config: GpuConfig)`: `is_busy(now) -> bool`, `turn_off(now) -> datetime` (returns expiry, persisted under setting `gpu.manual_off_until`), `turn_on() -> None`, `status(now) -> GpuStatus(busy: bool, reason: str)`.
  - Busy rule: manual-off and `now < expiry` → busy ("turned off until HH:MM"); sample None → not busy ("no GPU info"); `total - (used - own) < min_free_vram_mib` → busy ("other apps use N MiB"); `own == 0 and utilization_pct > max_foreign_utilization_pct` → busy ("GPU N% busy"); else free.

- [ ] **Step 1: Failing tests:** `parse_nvidia_smi("12288, 1024, 3\n")` → `GpuSample(12288,1024,3)`; garbage → `ValueError`; gate cases for each rule with a fake probe/own/`MemoryStore`, including expiry in the past → not busy; `turn_off` expiry = now + 4 h.
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement. **Step 4:** Pass; `make check`.
- [ ] **Step 5: Commit** `feat(gpu): busy detection with manual off switch`.

### Task 7: Link inspection

**Files:**
- Create: `src/stash/enrich/__init__.py`, `src/stash/enrich/links.py`,
  `src/stash/enrich/ytdlp.py`, `src/stash/enrich/html_meta.py`, `tests/fakes/link_inspector.py`
- Test: `tests/unit/enrich/test_links.py`, `tests/unit/enrich/test_html_meta.py`,
  `tests/unit/enrich/test_ytdlp_mapping.py`

**Interfaces:**
- Produces:
  - `LinkInfo(url: str, platform: str, title: str | None, description: str | None,
    uploader: str | None, duration_s: int | None, has_captions: bool)`; `LinkInfo.unknown(url)`.
  - `extract_urls(text: str) -> tuple[str, ...]` (http/https, trailing punctuation stripped, order kept, deduped).
  - `platform_of(url: str) -> str` → one of `instagram`, `youtube`, `tiktok`, `x`, `reddit`, `web` (`youtu.be`, `m.youtube.com`, `twitter.com` handled).
  - `LinkInspector(Protocol)`: `inspect(url: str) -> LinkInfo` — never raises.
  - `YtDlpInspector(extract: Callable[[str], Mapping[str, object]])` + `default_ytdlp_extract(url)` using `YoutubeDL({"quiet":True,"no_warnings":True,"skip_download":True,"noplaylist":True,"socket_timeout":15})`, `extract_info(url, download=False)`, `sanitize_info`; `info_to_link(url, info) -> LinkInfo` (`has_captions` = non-empty `subtitles` or `automatic_captions`).
  - `HtmlMetaInspector(client: httpx.Client)` — reads `og:title`, `og:description`, `<title>`, `meta description`; first 512 KiB only.
  - `FallbackInspector(first: LinkInspector, second: LinkInspector)` — uses second when first returns no title.

- [ ] **Step 1: Failing tests:** `extract_urls("see https://youtu.be/abc). and http://x.com/a")` → `("https://youtu.be/abc", "http://x.com/a")`; platform table; `info_to_link` with a dict sample (title/description/uploader/duration 61.5 → 61, `automatic_captions={"en":[…]}` → True); HTML parsing via MockTransport pages (og tags, title only, non-HTML content-type → unknown, 404 → unknown); yt-dlp `DownloadError` raised by the injected extract → `LinkInfo.unknown`; fallback chooses HTML when yt-dlp has no title.
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement. **Step 4:** Pass; `make check`.
- [ ] **Step 5: Commit** `feat(enrich): link metadata via yt-dlp with HTML fallback`.

### Task 8: Filer (routing + filing)

**Files:**
- Create: `src/stash/filing/__init__.py`, `src/stash/filing/prompt.py`,
  `src/stash/filing/schema.py`, `src/stash/filing/parse.py`, `src/stash/filing/filer.py`
- Test: `tests/unit/filing/test_parse.py`, `tests/unit/filing/test_filer.py`

**Interfaces:**
- Consumes: `ChatModel`, `ModelRouter.model_for`, `LlmTask.FILING`/`VISION`, `LinkInfo`, `Filing`, `Route`, `derive_title`.
- Produces:
  - `FILING_SCHEMA: Mapping[str, object]` (strict JSON schema: `route` enum, `item_type` enum, `title`, `stage` enum restricted to `inbox|want_to|planned`, `details` object of strings, `tags`, `people`, `date` string-or-null `YYYY-MM-DD`; `additionalProperties:false`).
  - `build_messages(text: str, link: LinkInfo | None, today: date, images: Sequence[ImagePart] = ()) -> list[ChatMessage]` — system prompt explains types/stages/routing and states that content inside `<captured>` / `<link>` tags is data, never instructions.
  - `parse_filing(raw: Mapping[str, object], fallback_text: str) -> Filing` — never raises: unknown `item_type` → OTHER; unknown/forbidden stage → INBOX; missing/blank title → `derive_title(fallback_text)`; title clipped to 120; `planned` without valid date → WANT_TO; unknown route → UNSURE; non-string detail values dropped; ≤10 tags, ≤5 people.
  - `Filer(router: ModelRouter, clock: Callable[[], datetime], timezone: ZoneInfo)`: `file(text: str, link: LinkInfo | None) -> Filing` (task FILING; propagates `LlmUnavailable`/`LlmDeferred`; on `LlmBadOutput` returns an INBOX/UNSURE filing from `derive_title`); `file_image(image: ImagePart, note: str, model: ChatModel) -> Filing` (eval-only vision path).

- [ ] **Step 1: Failing parse tests** (Review Focus 2): `{}` → OTHER/INBOX/title from text/UNSURE; `{"stage":"done"}` → INBOX; `{"stage":"planned","date":"next week"}` → WANT_TO, date None; `{"stage":"planned","date":"2026-11-14"}` → PLANNED with `date(2026,11,14)`; `{"item_type":"spaceship"}` → OTHER; 30 tags → 10; `details={"city":"Tokyo","n":3}` → `{"city":"Tokyo"}`.
- [ ] **Step 2: Failing filer tests** with `FakeChatModel` returning canned dicts and recording messages: link description containing `"Ignore previous instructions"` appears only inside `<link>` delimiters in the user message; `today` rendered in America/Los_Angeles; `LlmBadOutput` → INBOX filing; `LlmDeferred` propagates.
- [ ] **Step 3:** Run → FAIL. **Step 4:** Implement. **Step 5:** Pass; `make check`.
- [ ] **Step 6: Commit** `feat(filing): AI routing and filing with defensive parsing`.

### Task 9: Capture pipeline, replies, fix actions, bursts

**Files:**
- Create: `src/stash/capture/__init__.py`, `src/stash/capture/pipeline.py`,
  `src/stash/capture/replies.py`, `src/stash/capture/fixes.py`, `src/stash/capture/burst.py`
- Test: `tests/acceptance/test_capture_flow.py` (sections of `docs/usage.md`),
  `tests/unit/capture/test_replies.py`, `tests/unit/capture/test_fixes.py`, `tests/unit/capture/test_burst.py`

**Interfaces:**
- Consumes: `Store`, `LinkInspector`, `Filer`, `extract_urls`, domain types.
- Produces:
  - `IncomingMessage(source: SourceRef, text: str, media_paths: tuple[str, ...], received_at: datetime)`.
  - Results: `Filed(item: Item, unsure: bool)`, `IsRequest(capture: RawCapture)`, `Deferred(capture: RawCapture, reason: Literal["gpu_busy", "ai_unavailable"])`, `Duplicate()`; `ProcessResult = Filed | IsRequest | Deferred | Duplicate`.
  - `CapturePipeline(store, inspector, filer, new_id: Callable[[], str], clock)`:
    `receive(msg) -> RawCapture | None` (raw save; None on duplicate);
    `process(capture: RawCapture) -> ProcessResult` (inspect first URL, file, save item, set status FILED or REQUEST; on `LlmDeferred` → `Deferred("gpu_busy")`, on `LlmUnavailable` → `Deferred("ai_unavailable")`, status stays PENDING);
    `handle(msg) -> ProcessResult` = receive + process;
    `retry_pending() -> list[ProcessResult]`.
  - `Button(label: str, data: str)`; `Reply(text: str, buttons: tuple[tuple[Button, ...], ...])`.
  - `replies.py`: `confirmation(item: Item, unsure: bool) -> Reply` — text `✅ {item_type.label} · {detail} · {stage.label}` where detail = first present of `details["city"]`, `details["author"]`, `details["platform"]`, else omitted (`✅ Ideas · Want to`); buttons row `[("Type", "stash:t:<id>"), ("Stage", "stash:s:<id>")]`, plus row `[("That was a question →", "stash:q:<capture_id>")]` when unsure;
    `deferred(reason) -> Reply` — `"📥 Saved — I'll file it when the GPU is free."` / `"📥 Saved — I'll file it once the AI is reachable."`;
    `type_menu(item) -> Reply`, `stage_menu(item) -> Reply` (callback `stash:T:<id>:<type>` / `stash:S:<id>:<stage>`; stage menu offers inbox/want_to/planned only when the item has a date, else inbox/want_to/doing/dropped);
    `gone() -> Reply` — `"That item no longer exists."`. All callback data ≤ 64 bytes (ids are 32-char hex).
  - `FixHandler(store, clock)`: `apply(data: str) -> Reply | Reroute` where `Reroute(text: str)` signals "send this text to the agent as a question" (deletes the item, sets capture status REQUEST).
  - `BurstCoalescer(window_seconds: float)`: `add(result: Filed | Deferred, now) -> None`; `due(now) -> Reply | None` — one result → its normal reply; ≥2 → `"✅ Saved {n} items:\n• …"` (one line per item, type + title, truncated so total ≤ 4096), no buttons; `None` until `now - first_added ≥ window`.

- [ ] **Step 1: Failing acceptance tests** (MemoryStore, FakeLinkInspector, FakeChatModel through a real `ModelRouter`/`Filer`): shared link → item WANT_TO, reply `"✅ Places · Tokyo · Want to"` with Type/Stage buttons; question → `IsRequest`, no item; GPU busy (FakeBusy) → `Deferred("gpu_busy")` reply text exact, capture pending, then `retry_pending()` after busy clears → `Filed`; model raising `LlmUnavailable` → `Deferred("ai_unavailable")`; same `SourceRef` twice → second `handle` returns `Duplicate` and one item exists (Review Focus 1); image-only message (text "", one media path) → saved, title "Untitled" or note-derived, Filed (Review Focus 5); 10 000-char text → title ≤ 120 and reply ≤ 4096.
- [ ] **Step 2: Failing fix tests:** `stash:t:<id>` → type menu; `stash:T:<id>:recipe` → item retyped + confirmation; `stash:q:<capture_id>` → `Reroute(original text)` and item deleted; unknown id, `"stash:zz"`, `"garbage"` → `gone()` (Review Focus 4); every generated `Button.data` encodes to ≤ 64 bytes.
- [ ] **Step 3: Failing burst tests:** single result → normal confirmation after window; 3 results → combined text with 3 bullets; before window → None.
- [ ] **Step 4:** Run → FAIL. **Step 5:** Implement. **Step 6:** Pass; `make check`.
- [ ] **Step 7: Commit** `feat(capture): raw-first pipeline, confirmations, fix buttons, bursts`.

### Task 10: Eval harness (local vs OpenRouter, text/vision/OCR arms)

**Files:**
- Create: `src/stash/evaluation/__init__.py`, `src/stash/evaluation/cases.py`,
  `src/stash/evaluation/runner.py`, `src/stash/evaluation/report.py`,
  `src/stash/evaluation/ocr.py`, `evals/cases.jsonl`, `evals/make_images.py`, `evals/images/*.png`
- Test: `tests/unit/evaluation/test_cases.py`, `tests/unit/evaluation/test_runner.py`, `tests/unit/evaluation/test_report.py`

**Interfaces:**
- Consumes: `Filer`, `ChatModel`, `LinkInfo`, `ImagePart`, `Filing`.
- Produces:
  - `EvalCase(id: str, arm: Literal["text","image"], text: str, link: LinkInfo | None, image_path: Path | None, expect: Expectation)`; `Expectation(route: Route, item_type: ItemType | None, stage: Stage | None, date: date | None, details: Mapping[str, str])` (details matched case-insensitively by substring).
  - `load_cases(path: Path) -> list[EvalCase]` (JSONL; `ValueError` naming the line on bad input).
  - `Ocr(Protocol)`: `read(path: Path) -> str`; `TesseractOcr()` via `pytesseract.image_to_string`.
  - `run_eval(cases, model: ChatModel, model_label: str, arms: Sequence[Literal["text","vision","ocr"]], ocr: Ocr | None, clock) -> EvalRun`; `EvalRun(label, results: list[CaseResult])`; `CaseResult(case_id, arm, passed_fields: frozenset[str], failed_fields: frozenset[str], latency_s: float, error: str | None)`.
  - `render_report(runs: Sequence[EvalRun]) -> str` — Markdown table per arm: route/type/stage/date/details accuracy %, p50 latency, errors; one column per model.
- [ ] **Step 1:** Main loop writes `evals/cases.jsonl` with 25 **fake** cases: 17 text filing (places, recipes, books, podcast, business idea, date night with date, purchase, gift for "Ana", course, trip), 5 routing (questions like "what can I do Saturday afternoon?", "books I read this year", plus 2 ambiguous), 3 image cases (recipe card, event poster with date, product screenshot) referencing `evals/images/*.png`.
- [ ] **Step 2: Failing tests:** `load_cases` parses a 2-line sample; bad JSON line → `ValueError("line 2 …")`; runner with FakeChatModel scoring (correct type passes `item_type`, wrong stage fails `stage`), model raising `LlmUnavailable` → `error` set, counted as failed; `ocr` arm uses the fake OCR text; report contains a header row with both model labels and a percentage cell.
- [ ] **Step 3:** Run → FAIL. **Step 4:** Implement; `evals/make_images.py` renders the three PNGs with Pillow (fake content); run it once and commit the PNGs.
- [ ] **Step 5:** Pass; `make check`.
- [ ] **Step 6: Commit** `feat(eval): scripted eval comparing providers across text/vision/OCR`.

### Task 11: Composition root, CLI, doctor

**Files:**
- Create: `src/stash/app.py`, `src/stash/doctor.py`; Modify: `src/stash/cli.py`
- Test: `tests/acceptance/test_cli.py`, `tests/unit/test_doctor.py`

**Interfaces:**
- Consumes: everything above.
- Produces:
  - `StashApp(config, store, pipeline, fixes, gpu, router, doctor, ollama_control, burst_factory)` dataclass; `build_app(config: StashConfig, *, client: httpx.Client | None = None, run: CommandRunner | None = None) -> StashApp` — the only place adapters are constructed.
  - `Doctor(checks: Sequence[tuple[str, bool, Callable[[], ProbeResult]]])` (name, required, check) → `run() -> list[DoctorLine(name, ok, required, detail)]`; checks: config, database (open + migrated), each configured provider probe (required if used by any task or as fallback), `nvidia-smi` (optional), yt-dlp import + `deno` on PATH (optional), `tesseract` on PATH (optional).
  - CLI subcommands (all take `--config PATH`, default `$STASH_CONFIG` or `~/.config/stash/stash.toml`):
    `doctor` (prints `✔/✖/! name — detail`, exit 1 if a required check fails);
    `list [--stage S] [--type T] [--limit N]`;
    `retry` (processes pending captures, prints one line each);
    `gpu status|off|on` (`off` also calls `OllamaControl.unload`);
    `eval [--providers ollama,openrouter] [--arms text,vision,ocr] [--cases evals/cases.jsonl] [--out PATH]`;
    `backup --to DIR` (writes `stash-YYYYMMDD.db`, keeps the newest 30).
- [ ] **Step 1: Failing acceptance tests** invoking `main([...])` with a temp config whose `client` is a MockTransport-backed httpx client injected via `build_app` (test helper builds the app; CLI accepts an injected app factory): `doctor` with OpenRouter key rejected → exit 1 and a `✖ openrouter` line; `list --stage want_to` prints items; `gpu off` prints expiry and posts `keep_alive: 0`; `backup` keeps 30 newest of 32 files; invalid config → exit 2 with the `ConfigError` message.
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement. **Step 4:** Pass; `make check`.
- [ ] **Step 5: Commit** `feat(cli): composition root, doctor, list/retry/gpu/eval/backup commands`.

### Task 12: Hermes plugin adapter

**Files:**
- Create: `src/stash/hermes_adapter/__init__.py`, `src/stash/hermes_adapter/plugin.py`,
  `src/stash/hermes_adapter/telegram_io.py`, `src/stash/hermes_adapter/tools.py`,
  `deploy/hermes-plugin/stash/plugin.yaml`, `deploy/hermes-plugin/stash/__init__.py`,
  `tests/fakes/hermes_ctx.py`
- Test: `tests/unit/hermes_adapter/test_plugin.py`, `tests/unit/hermes_adapter/test_telegram_io.py`, `tests/unit/hermes_adapter/test_tools.py`

**Hermes facts this task relies on** (source @ 43a35e8; verify in the M0 spike):
`register(ctx)`; `ctx.register_hook("pre_gateway_dispatch", cb)` where `cb(event, gateway, session_store, **kw)` may be async and returns `{"action": "skip"|"allow"}`; `event.text`, `event.source.chat_id/user_id`, `event.message_id`, `event.media_urls` (local paths); `ctx.register_platform_handler("telegram", factory)` with `factory(application, adapter)` (PTB `Application`); callback handlers **must** use `pattern=r"^stash:"`; `ctx.register_command(name, handler, description=...)` with `handler(raw_args: str) -> str | None`; `ctx.register_tool(name=, toolset="stash", schema=, handler=)` with `handler(args: dict, **kw) -> str` (JSON string, never raises); `ctx.inject_message(text, role="user", session_key=...) -> bool` (requires `plugins.entries.stash.allow_gateway_injection: true`); `ctx.get_config(key, default)`; `plugins.plugin_storage.plugin_data_dir("stash")`. Plugins must run **in-process** (host isolation refuses platform handlers).

**Interfaces:**
- Consumes: `StashApp` / `build_app`, `load_config`, `IncomingMessage`, `ProcessResult`, `Reply`, `FixHandler`, `BurstCoalescer`.
- Produces:
  - `register(ctx) -> None` in `stash.hermes_adapter.plugin`. The shim
    `deploy/hermes-plugin/stash/__init__.py` defines `register(ctx)` that puts
    `<repo>/src` on `sys.path` (found via `Path(__file__).resolve().parents[3] / "src"`,
    so it works when `~/.hermes/plugins/stash` is a **symlink** to
    `deploy/hermes-plugin/stash`) and delegates to `stash.hermes_adapter.plugin.register`.
    Hermes installs plugin deps only from a `pyproject.toml` next to `plugin.yaml`
    (direct-URL/path requirements are not managed), so
    `deploy/hermes-plugin/stash/pyproject.toml` lists stash's **runtime** deps
    (`httpx>=0.28.1,<0.29`, `yt-dlp[default]>=2026.10.26`, `pytesseract>=0.3.13,<0.4`,
    `pillow>=11,<13`) with upper bounds, `requires-python = ">=3.11"`, no build-system.
    Hermes' managed runtime is Python 3.11–3.13.
  - `StashPlugin(app: StashApp, outbox: Outbox, inject: Callable[[str, str], bool])` with:
    `async on_dispatch(event, gateway, session_store, **kw) -> dict[str, str]` — `/`-prefixed text → `{"action":"allow"}`; otherwise `receive` in a worker thread (`asyncio.to_thread`), schedule processing as a background task, return `{"action":"skip"}`; duplicate → skip silently;
    processing: `Filed`/`Deferred` → `BurstCoalescer` → `outbox.send(chat_id, reply)` when due; `IsRequest` → `inject(text, session_key)`; any exception → log, capture stays pending.
    `async on_callback(data: str, chat_id: str, message_id: str) -> None` → `FixHandler.apply` → `outbox.edit(...)` or `inject` on `Reroute`.
  - `Outbox(Protocol)`: `async send(chat_id: str, reply: Reply) -> None`, `async edit(chat_id: str, message_id: str, reply: Reply) -> None`; `TelegramOutbox(bot)` using PTB `InlineKeyboardMarkup`/`InlineKeyboardButton`; `to_keyboard(reply) -> InlineKeyboardMarkup | None`.
  - Commands: `/list [stage]`, `/gpu on|off|status`, `/retry` (text replies).
  - Agent tools (toolset `stash`): `stash_search {query}`, `stash_list {stage?, item_type?, limit?}` → JSON string `{"items":[{"id","type","title","stage","date"}...]}`; errors → `{"error": "..."}`.
  - `deploy/hermes-plugin/stash/plugin.yaml`: `name: stash`, `version: 0.1.0`, `description`, `provides_tools: [stash_search, stash_list]`, `provides_hooks: [pre_gateway_dispatch]`.
- [ ] **Step 1: Failing tests** with `FakeHermesContext` (records registrations, provides `get_config`, `inject_message`) and `FakeOutbox`: `register` registers hook, telegram platform handler, three commands, two tools; dispatch of a plain message → returns skip, item stored, after window one `send` with the confirmation; `/list` text → allow and nothing stored; duplicate event → one capture; `IsRequest` → `inject` called with the text; callback `stash:T:<id>:book` → `edit` with updated confirmation; `stash_search` returns valid JSON for a hit and `{"error":…}` when the store raises; `to_keyboard` builds a real PTB `InlineKeyboardMarkup` with matching `callback_data`.
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement (Hermes modules imported lazily inside `register` only). **Step 4:** Pass; `make check`.
- [ ] **Step 5: Commit** `feat(hermes): plugin adapter with raw-first hook, buttons, commands, tools`.

### Task 13: PC deploy kit and M0 spike checklist (main loop, no Python)

**Files:**
- Create: `docs/deploy/wsl-setup.md`, `docs/spike-m0.md`,
  `deploy/hermes/config.yaml.example`, `deploy/systemd/ollama.override.conf`,
  `deploy/windows/wslconfig.example`

- [ ] **Step 1:** `config.yaml.example`: `model: {provider: custom, default: <ollama model>, base_url: http://localhost:11434/v1, context_length: 65536}` with commented OpenRouter alternative (`provider: openrouter`, key in `~/.hermes/.env`); `platform_toolsets: {telegram: [web, stash]}`; `agent: {disabled_toolsets: [terminal, file, code_execution, browser, delegation]}`; `plugins: {enabled: [stash], entries: {stash: {allow_gateway_injection: true, settings: {config_path: ~/.config/stash/stash.toml}}}}`; Telegram `TELEGRAM_ALLOWED_USERS`.
- [ ] **Step 2:** `ollama.override.conf`: `OLLAMA_CONTEXT_LENGTH=65536`, `OLLAMA_KEEP_ALIVE=5m`. The gateway service comes from Hermes itself (`hermes gateway setup` / `hermes gateway install`, a systemd user unit) — no hand-written unit. WSL kept alive by a Task Scheduler entry at logon: `C:\Windows\System32\wsl.exe -d Ubuntu --exec /bin/sh -c "sleep infinity"` (Hermes' WSL guide). `.wslconfig`: `networkingMode=mirrored`.
- [ ] **Step 3:** `wsl-setup.md`: step-by-step (WSL2 Ubuntu + systemd, NVIDIA driver/CUDA in WSL, Ollama, pull candidate models, Hermes v0.22.6 install pinned, `uv pip install -e` stash into Hermes' environment, plugin shim copy, BotFather token, `stash doctor`, `stash eval`, deno for yt-dlp, tesseract).
- [ ] **Step 4:** `spike-m0.md`: the six unverified points from the spec, each with how to verify on the PC and the expected observation; the **go/no-go criteria** (raw save before LLM via `pre_gateway_dispatch`; buttons sent and callbacks received); what to record and where (ADR in `docs/adr/`).
- [ ] **Step 5: Commit** `docs: WSL deploy kit and M0 spike checklist`.

---

## Later plans (each written and executed after the previous one lands)

- Plan 2 — M2 lifecycle: outcomes, keep/library, repeats, groups, stage transitions, `/done`, agent tools for lifecycle.
- Plan 3 — M3 planning & nudges: AI-proposed steps with confirm, reminders, Sunday digest, morning-after follow-ups, catch-up, scheduler (spawn_task or no-agent cron per spike), nightly NAS backup wiring.
- Plan 4 — M4 people and key dates.
- Plan 5 — M5 transcripts (captions + faster-whisper queue, VRAM-aware) and image reading (OCR or vision per eval).
- Plan 6 — M6 HTML library (Telegram file + LAN server).
