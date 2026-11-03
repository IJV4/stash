# stash Plan 5 — Transcripts, summaries and image reading (M5)

> **For agentic workers:** Python only through
> `python-development:python-coding-orchestrator`; the main loop commits.
> Requires Plans 2–3. Build after the M0 spike and the M1 eval, which picks the
> image reader and confirms Whisper VRAM. Steps use checkbox (`- [ ]`) syntax.

**Goal:**
- Media items get a transcript, from existing captions where possible and
  otherwise from local faster-whisper on the 3080 Ti.
- Each transcript yields a summary and draft takeaways, which can be adopted
  when the item is marked Done.
- Screenshots and photos are read with the reader the eval chose (OCR or a
  vision model), and that text informs filing.

**Architecture:**
- A durable job queue (migration `0005`).
- A separate **worker process** (`stash worker`, a systemd user service in the
  project's own venv). It keeps the heavy GPU dependency (`faster-whisper`/
  CTranslate2) out of the Hermes gateway's shared environment.
- GPU exclusivity: the worker runs a job only while the GPU gate is free and
  Ollama holds no VRAM. While it runs it publishes a heartbeat, which makes the
  router defer LLM work.
- Results reach Telegram through Plan 3's ticker as a new nudge kind.
- Image reading is a new `stash.images` feature behind an `ImageReader` port.
  `TesseractOcr` moves there from `stash.evaluation`, which then imports it.

**Tech Stack:** Plan 1 stack, plus `faster-whisper>=1.2.1,<2` as an optional
extra `transcribe` (installed only on the PC with `uv sync --extra transcribe`;
never imported on the Mac). CUDA 12 and cuDNN 9 are needed on the PC.

**Spec:** design doc → Capture flow 6–7, GPU sharing; `docs/spike-m0.md` #4, #5, #12.

## Global Constraints

- Plan 1–3 Global Constraints apply.
- **`[transcripts]` defaults (builder calls, configurable):**

  | Key | Default | Notes |
  |---|---|---|
  | `whisper_model` | `"large-v3-turbo"` | VRAM unverified; the spike measures it |
  | `compute_type` | `"int8_float16"` | |
  | `max_minutes` | `180` | |
  | `max_download_mb` | `300` | |
  | `caption_languages` | `["en", "es"]` | Then the original language |
  | `idle_seconds_before_gpu` | `120` | Ollama must have held 0 MiB this long |

- **`[images]` defaults:**
  - `reader = "none"`, then set to `"ocr"` or `"vision"` after the eval.
  - `media_root`: required when `reader != "none"`. It is the Hermes media
    cache path, which the spike confirms.
  - `max_image_mb = 10`.
- **Downloads:** captions and direct audio URLs (`.mp3`, `.m4a`, `.ogg`,
  `.opus`, `.wav`) go through the existing public-URL check, via
  `http_url_host` / `is_public_http_url`, with a size cap. yt-dlp audio
  downloads keep `allowed_extractors = ["default", "-generic"]`. Temp files
  stay in `data_dir/tmp` and are deleted in a `finally`.
- **Never at the same time:** the worker starts a Whisper job only if all of
  these hold:
  - `GpuGate.is_busy(now)` is false;
  - `OllamaVramUsage.own_mib()` is 0 and has been for `idle_seconds_before_gpu`;
  - the `gpu.manual_off_until` switch is not active.
  While a job runs, the worker refreshes the setting `gpu.worker_heartbeat`
  (every 15 s), and `ModelRouter`'s busy check treats a heartbeat newer than
  45 s as busy, so filing defers.
- Long transcripts are summarized map-reduce style:
  - chunks of ≤ 24 000 chars;
  - a summary of ≤ 1200 chars;
  - 3–7 draft takeaways, each ≤ 300 chars.
  All of this runs on `LlmTask.SUGGESTIONS`.

## Review Focus

1. **Process crash mid-job** (worker killed during Whisper): the job returns to
   `queued` after a lease timeout (10 min). The temp file is cleaned on the next
   start, and no half transcript is saved.
2. **The owner starts a game mid-transcription**: the gate turns busy, the
   current job stops at the next segment boundary and is requeued, and VRAM is
   freed (model released).
3. **Hostile media**:
   - a 6-hour video → refused with the reason "longer than 180 minutes";
   - a redirect to a private IP → refused;
   - a fake `.mp3` that is HTML → refused;
   - an image path outside `media_root`, or a non-image file → ignored, and
     filing continues from the note.
4. **Caption files** with markup, duplicate cue lines (the YouTube rolling
   captions) and timestamps are cleaned into plain, de-duplicated text.
5. **LLM unavailable during summarizing**: the transcript is saved, and the
   summary job is retried later without re-transcribing.

---

### Task 1: Jobs queue + transcripts store (migration 0005)

**Files:** Create `src/stash/domain/job.py` and `store/migrations/0005_jobs_transcripts.sql`.
Modify the store port, sqlite, rows and `MemoryStore`. Tests: the contract
tests for jobs and transcripts, plus a 0004→0005 migration test.

**Interfaces:**
- `JobKind(StrEnum)`: `CAPTIONS`, `TRANSCRIBE`, `SUMMARIZE`.
- `JobStatus`: `QUEUED`, `RUNNING`, `DONE`, `FAILED`.
- `Job(id, kind, item_id, status, attempts, not_before, lease_until, last_error ≤ 300)`.
- `JobStore`:
  - `enqueue(job)`: idempotent on `(kind, item_id)` while not DONE.
  - `claim(kinds, now, lease) -> Job | None`: an atomic claim; expired leases
    are re-claimable (RF1).
  - `complete(job_id)`.
  - `fail(job_id, error, retry_at | None)`: at most 3 attempts, then FAILED.
  - `jobs_for(item_id)`.
- `Transcript(item_id, source: "captions" | "whisper", language, text, created_at)`
  and `MediaNotes(item_id, summary, draft_takeaways: tuple[str, ...], created_at)`.
- `TranscriptStore`: `save_transcript`, `get_transcript`, `save_media_notes`, `get_media_notes`.
- [ ] **Step 1: Failing contract tests**, including the RF1 lease expiry and the
  claim race between two connections (SQLite, integration).
- [ ] **Step 2–4:** Implement; `make check`. **Step 5: Commit** `feat(store): job queue and transcripts (migration 0005)`.

### Task 2: Captions — fetch and clean

**Files:** Create `src/stash/transcripts/{__init__,captions,vtt}.py` (a pure
parser) and the adapter `src/stash/transcripts/caption_fetch.py` (httpx +
yt-dlp info). Tests: `tests/unit/transcripts/test_vtt.py` (RF4) and the
caption-selection tests.

**Interfaces:**
- `parse_captions(text: str, fmt: Literal["vtt", "srt"]) -> str`.
- `choose_track(subtitles, automatic_captions, languages) -> CaptionTrack | None`.
  Manual tracks win over automatic ones. Within a track, formats are preferred
  in the order vtt > srt > srv3.
- `CaptionFetcher(extract_info, client, monotonic).fetch(url) -> Transcript | None`.
- The pipeline enqueues CAPTIONS for MEDIA/LEARN items whose
  `LinkInfo.has_captions` is true. Otherwise it enqueues TRANSCRIBE when the
  platform is supported or the URL is a direct audio URL.
- [ ] **Step 1: Failing tests:** RF4 fixtures (fake VTT with rolling duplicates
  and `<c>` tags); track choice; a 404 → None.
- [ ] **Step 2–4:** Implement; architecture guard (caption_fetch is an adapter); `make check`.
- [ ] **Step 5: Commit** `feat(transcripts): caption tracks to clean text`.

### Task 3: Whisper transcription adapter + GPU exclusivity

**Files:** Create `src/stash/transcripts/{audio,transcriber,exclusive}.py`
(ports and pure logic) and the adapters `src/stash/transcripts/whisper.py`
(faster-whisper, imported lazily) and `audio_fetch.py` (yt-dlp `bestaudio`
plus direct downloads). Modify `src/stash/llm/router.py` usage at the
composition root (a composite BusyCheck). Tests: unit tests with
`FakeTranscriber`/`FakeAudioSource`, and `tests/integration/test_whisper_import.py`
(skipped when faster-whisper isn't installed).

**Interfaces:**
- `Transcriber(Protocol)`: `transcribe(path: Path, should_stop: Callable[[], bool]) -> TranscriptText | Stopped`.
  It iterates segments lazily and checks `should_stop` between segments (RF2).
- `AudioSource(Protocol)`: `fetch(url, dest_dir, limits) -> AudioFile | Refused(reason)`.
- `ExclusiveGpu(gate, own_vram, store, clock, config)`:
  - `may_start(now) -> bool` (the Global Constraints rule);
  - `heartbeat(now)`, `release()`;
  - `busy_for_llm(now) -> bool` (heartbeat < 45 s).
- `CompositeBusy(gate, exclusive)` satisfies `BusyCheck` and is what
  `build_app` hands to `ModelRouter`.
- `WhisperTranscriber(model_name, compute_type)` loads the model on first use
  and releases it after each job (`del` plus `gc`) so VRAM is returned.
- [ ] **Step 1: Failing tests:**
  - `may_start` truth table.
  - The router defers while the heartbeat is fresh.
  - `should_stop` flips mid-job → `Stopped`, then requeue (RF2).
  - RF3 refusals in `AudioSource`, using MockTransport.
- [ ] **Step 2–4:** Implement; `pyproject` gets the `transcribe` extra and a mypy override; guard; `make check`.
- [ ] **Step 5: Commit** `feat(transcripts): Whisper adapter with GPU exclusivity`.

### Task 4: Summaries, draft takeaways, worker loop, notifications

**Files:** Create `src/stash/transcripts/{summarize,worker}.py` and the CLI
`stash worker` command. Modify `src/stash/domain/nudge.py` (`TRANSCRIPT_READY`),
`src/stash/nudges/*` and `src/stash/capture/{callbacks,fixes}.py`
(`FixKind USE_DRAFT="u"`). Add `deploy/systemd/stash-worker.service`. Tests:
the unit summarizer and worker tests, `tests/acceptance/test_transcripts.py`.

**Interfaces:**
- `Summarizer(models, clock).summarize(title, text) -> MediaNotes` (map-reduce;
  propagates `LlmUnavailable`; RF5).
- `Worker(jobs, captions, audio, transcriber, summarizer, exclusive, store, clock,
  tmp_dir).run_once() -> WorkResult`. It claims a job, does it, then completes
  it or fails it with a backoff (5 min, 30 min, 3 h).
  - CAPTIONS done → enqueue SUMMARIZE.
  - TRANSCRIBE done → enqueue SUMMARIZE.
  - SUMMARIZE done → a TRANSCRIPT_READY nudge becomes due.
- `stash worker [--once]` loops `run_once` with a 10 s idle sleep. It handles
  SIGTERM gracefully: it releases the lease, stops Whisper at the next segment
  and deletes temp files.
- Ticker message: `"📝 Notes ready for {title}: {summary first 300 chars}…"`.
- Plan 2's `done_reply` gains the button `"Use draft takeaways"`
  (`stash:u:<outcome_id>`) when MediaNotes exist.
- `stash show` prints the summary and draft takeaways.
- [ ] **Step 1: Failing acceptance** (clock-driven, with fakes):
  - A podcast link with no captions → TRANSCRIBE → SUMMARIZE → the nudge.
  - Marking it Done shows "Use draft takeaways", and tapping it copies the
    drafts into the outcome.
  - A summarizer outage → retried without re-transcribing.
- [ ] **Step 2–4:** Implement; `make check`.
- [ ] **Step 5:** Update `docs/deploy/wsl-setup.md` (`uv sync --extra transcribe`,
  the worker service, CUDA/cuDNN checks), `docs/usage.md` ("Transcripts and
  notes") and `docs/spike-m0.md` (measure Whisper VRAM and speed on a
  30-minute podcast).
- [ ] **Step 6: Commit** `feat: transcription worker, summaries and draft takeaways`.

### Task 5: Image reading for captures

**Files:** Create `src/stash/images/{__init__,reader,loader}.py`. Move
`src/stash/evaluation/tesseract.py` → `src/stash/images/tesseract.py`, and the
`Ocr` port → `stash.images`, with the evaluation imports updated. Modify
`src/stash/capture/pipeline.py`, `src/stash/filing/prompt.py` (an
`<image_text>` data block), `config` (`[images]`) and `app/*`. Tests:
`tests/unit/images/*`, `tests/acceptance/test_image_capture.py`, and the
existing eval tests still green.

**Interfaces:**
- `MediaLoader(media_root, max_bytes).load(path) -> ImageBytes | None`. It
  rejects:
  - paths that, once resolved, fall outside the root;
  - symlinks that escape the root;
  - files over the size limit;
  - files that aren't PNG, JPEG or WebP by their magic bytes.
- `ImageReader(Protocol)`: `read(images: Sequence[ImageBytes], note: str) -> ImageReading`.
  - `OcrReader(ocr)` → `ImageReading(text=…)`.
  - `VisionReader(models)` → `ImageReading(filing=Filing)` via
    `Filer.file_image` on `LlmTask.VISION`.
  - `NoReader`.
- The pipeline:
  - **OCR**: the text is appended to the filer input inside `<image_text>`;
    filing is otherwise unchanged.
  - **Vision**: the vision filing is used directly.
  - **Failure**: the pipeline falls back to the note alone.
- [ ] **Step 1: Failing acceptance:**
  - OCR on the fake `recipe_card.png` (through FakeOcr text) → files as RECIPE.
  - A path outside `media_root` → filed from the note, and a WARNING without the
    path contents.
  - Vision mode with FakeChatModel → uses the vision filing.
- [ ] **Step 2–4:** Implement; architecture guard updates (`images` is a feature,
  `tesseract` is an adapter); `make check`.
- [ ] **Step 5: Commit** `feat(images): read screenshots with OCR or a vision model`.
