# stash — design

Date: 2026-11-02 · Status: draft for approval

## Intent

A personal organizer/assistant for **things I want to do**: stuff seen on
social media (Instagram, YouTube, X, Reddit, the web, podcasts) or thought of
on my own. Today these are scattered across app "saves", screenshots, Google
notes and Gmail; I forget them, never act on them, and when I do have free
time I can't choose from the pile. stash fixes all four: one inbox, things
resurface, it nudges me to act, and it helps me choose.

Single user (the owner), long-lived tool, standalone project.

**Success looks like:** I share a reel or type a thought in two taps; it is
filed without fuss; on Sunday I get a digest that makes me actually plan
something; a date night gets its reservation made on time; books, podcasts and
recipes I liked leave a trail of takeaways and favorites I can browse.

### Goals
- Frictionless capture from Android and Windows, platform-independent.
- AI files each capture (type, details, stage) and lets me correct it.
- A lifecycle that fits very different things (recipe, book, business idea,
  date night) without per-type special cases in the core.
- Proactive nudges: weekly digest, time-based and lead-time reminders,
  suggestions on demand.
- A browsable library of what I did and kept.

### Non-goals (v1)
- Multi-user / sharing (my wife does not use it in v1).
- Automatic import from Gmail / Google (comes after deployment; Google Keep has
  no personal-account API, so Keep import is out entirely).
- Location-based reminders.
- A writable web UI (the HTML library is read-only).
- 24/7 availability.

### Anti-goals (failure even if it "works")
- Capture that needs more than a share + optional one-line note.
- A noisy bot: confirmations, questions or reminders I learn to ignore.
- Losing items.
- My real personal data on the Apple work Mac.

## Constraints

- **Runtime host:** the owner's Windows PC (RTX 3080 Ti 12 GB VRAM, 32 GB
  RAM), **everything inside WSL2 Ubuntu**. The PC is *not* on 24/7 — accepted.
  Consequences: reminders/digest are late while it is off (must catch up on
  start), and Telegram only retains undelivered bot updates for ~24 h, so
  shares made during a longer shutdown are lost — accepted for v1.
- **Backup target:** Synology NAS, a 'j'/value ARM model (cannot run
  containers) on the home LAN. Backups only.
- **Development host:** an Apple-managed Mac (this one). Its sandbox blocks
  api.telegram.org, openrouter.ai and the Ollama registry; GitHub and PyPI are
  reachable; no Docker. So: code + unit tests with fakes here; end-to-end runs
  only on the PC. Only fake data on the Mac.
- **Code flow:** private repo on the owner's personal GitHub; Mac → push
  (always ask before pushing) → pull on the PC.
- **Python:** 3.12 on the Mac (`python3`), per-project `.venv`. Hermes Agent
  accepts Python 3.11–3.14.
- **Language:** bot speaks English. **Timezone:** America/Los_Angeles.
- **Access:** only the owner's Telegram user ID (`TELEGRAM_ALLOWED_USERS`).

## Approaches considered

Interface (decided in conversation):
1. **Telegram chat bot** — chosen. Share-sheet capture on Android, desktop
   client on Windows, push messages for free, natural "assistant" UX, no UI to
   build.
2. Installable web app (PWA) — nicer browsing, but more UI to build and
   maintain, and push notifications are harder.
3. Bot first, web later — two front ends.
4. Google-based (Sheets/Tasks + Apps Script) — free hosting, but cramped UI and
   awkward for an assistant.

Engine (decided in conversation):
1. **Hermes Agent (Nous Research) + a custom `stash` plugin** — chosen. Hermes
   provides the Telegram gateway (text, voice transcription, images, files,
   inline buttons), cron scheduling, provider-agnostic LLM access (Ollama,
   llama.cpp, OpenRouter, Nous Portal…), a Google Workspace skill for later,
   Windows/WSL/Linux support. Trade-off: we inherit its design and a fast
   release cadence (v0.22.6 released 2026-11-02), and its built-in memory is
   unsuitable for the item store, so the core is our own plugin.
2. Custom bot (python-telegram-bot + our own LLM calls + scheduler) — full
   control, more code, no agent features for free.

Hosting (decided): PC now in WSL2 with NAS backups; NAS hosting ruled out by its
ARM 'j' model; VPS / always-on hosting deferred. Keep the setup portable
(Linux services in WSL move to a VPS unchanged).

AI backend (decided): **local first** (Ollama in WSL2 with CUDA on the 3080 Ti,
~8B model with tool calling), measured by a scripted eval; **OpenRouter** is
the fallback, switchable by config.

## Hermes Agent facts relied on

Researched 2026-11-02 from the GitHub repo docs
(github.com/NousResearch/hermes-agent, `website/docs/...`). MIT license.

- Telegram gateway on python-telegram-bot; BotFather token +
  `TELEGRAM_ALLOWED_USERS`; polling or webhook; inline buttons; proactive
  delivery via cron jobs targeting `telegram` / `telegram:<chat_id>`.
  `send_message` is intentionally **not** an agent-callable tool.
- Cron: `in 30m`, ISO timestamps, `every monday 9am`, 5-field cron; jobs in
  `~/.hermes/cron/jobs.json`; gateway daemon must be running; 60 s tick; each
  job runs in a **fresh agent session** (an LLM run, no chat context).
- Memory: `MEMORY.md` (~2.2 KB) + `USER.md` (~1.4 KB) and a session SQLite
  (`~/.hermes/state.db`). Not a structured store → stash owns its own DB.
- Plugins: `~/.hermes/plugins/<name>/` with `plugin.yaml` and
  `register(ctx)` → `ctx.register_tool(name, toolset, schema, handler)`;
  enabled with `hermes plugins enable`. MCP servers and skills also supported.
- Providers: requires **≥64k context**. Ollama defaults to 4k → set
  `OLLAMA_CONTEXT_LENGTH`; llama.cpp needs `--jinja` for tool calls.
- Bundled `google-workspace` skill (Gmail, Calendar, Drive, Sheets, Docs) for
  the later Gmail phase.

**Unverified — must be confirmed by an M0 spike before building on them:**
1. Whether a plugin tool can send a reply with **inline buttons** and receive
   the **button callbacks** (needed for "fix" buttons and confirming steps).
2. Whether the plugin can run **deterministic scheduled code** (reminder checks,
   backups) without spawning an LLM agent session per tick; if not, the plugin
   runs its own lightweight scheduler thread or a systemd timer calls a stash
   CLI, and only the digest uses a Hermes cron/agent run.
3. How the agent receives shared links from the Android share sheet (plain
   message text expected).
4. Hermes' voice transcription backend and whether it can share the Whisper
   setup.
5. Which local model gives reliable tool calls at 64k context within 12 GB
   VRAM (candidates: Hermes 3 8B, Qwen-family 7–8B; Q4 weights + quantized KV
   cache).

6. Whether a plugin can **see every incoming message before the LLM does**
   (a pre-agent hook), so the raw save never depends on the model choosing to
   call a tool.

The spike's findings get written into this doc (or an ADR) before M1.

**Go/no-go gate after M0 (owner decision).** Hermes stays only if the spike
shows a plugin can (a) save every message raw before the LLM runs (#6) and
(b) send inline buttons and receive their callbacks (#1). If either fails,
**drop Hermes and switch to approach 2** (own bot on python-telegram-bot,
direct calls to Ollama/OpenRouter, own scheduler). The Hermes-free core makes
this a swap of the adapter layer, not a rewrite. Gmail later would then use the
Google API directly instead of Hermes' skill.

## Design

### Architecture

```
Android share sheet / Telegram desktop
        │
   Telegram Bot API (polling)
        │
┌─ WSL2 Ubuntu on Windows PC ─────────────────────────────┐
│  Hermes gateway (systemd service, pinned version)        │
│     ├─ LLM provider → Ollama (CUDA, local)  | OpenRouter │
│     ├─ cron → weekly digest (agent run)                  │
│     └─ stash plugin (our code)                           │
│          ├─ tools: capture, update, list, search,        │
│          │   plan/steps, outcome, people, library, …     │
│          ├─ SQLite store (stash.db)                      │
│          ├─ link enrichment (yt-dlp metadata/captions)   │
│          ├─ job queue: enrichment, Whisper transcription │
│          ├─ scheduler: due reminders, catch-up, backups  │
│          └─ HTML library renderer                        │
│  NAS SMB share mounted → nightly DB backup (30 days)     │
└──────────────────────────────────────────────────────────┘
Windows Task Scheduler: start WSL + services at logon, keep WSL from idling out.
```

The plugin's core (domain model, store, scheduling logic, rendering) is plain
Python with **no Hermes imports**, behind a thin adapter that registers tools
with Hermes. This keeps it unit-testable on the Mac with fakes and insulates it
from Hermes churn.

### Data model

**Item** — anything I want to do.
- `type`: place/travel, recipe, purchase, learn (course/tutorial/video),
  book, podcast/video/article (media), idea (business/project), plan/event
  (incl. dates), activity/habit, gift, other. Types drive *suggested* fields
  and prompts, not the lifecycle. Habits have **no recurrence in v1** (they
  are ordinary items; builder call). General recurrence rules can come later.
- `title`, `source_url`, `source_platform`, `my_note`, `captured_at`.
- Extracted `details` (type-specific, JSON): e.g. place → city, cost level,
  duration; recipe → ingredients, time; book → author; media → duration,
  summary, transcript ref.
- `tags`, optional `people` links, optional `parent` (groups).
- `stage` (below), `due`/`date` (for Planned), `cool_off_until` (purchases).

**Stages** — one lifecycle for all types:

| Stage | Meaning |
|---|---|
| Inbox | Captured, not yet reviewed |
| Want to | I intend to, someday |
| Planned | Has a date; carries a prep checklist |
| Doing | Multi-session: reading, trying an idea, a course |
| Done | Records an outcome |
| Dropped | Not for me (with reason); hidden but searchable |

AI filing normally moves a capture straight to **Want to** (or **Planned** if
it has a date); Inbox holds what it couldn't confidently file.

**Steps** — checklist on an item; each step has optional `lead_time` relative
to the item date (e.g. "book table — 5 days before", "buy flowers — same
day") or an absolute due time, and a done flag. For Planned items the AI
proposes steps; **I confirm/edit before they are saved**. Each step with a due
time produces a reminder. Business-idea "experiments" are steps too.

**Outcome** — on Done: date, rating, notes, takeaways (list), `keep` flag.
`keep` puts the item in my **library** (favorite recipes, book notes, kept
podcast takeaways, favorite places). **Repeats:** a done item can be done
again; each completion is an outcome record (made the recipe 3 times).

**Groups** — an item can contain items (a trip holds places, restaurants,
a packing checklist; a date night may link a restaurant).

**People** — name, relation, key dates (birthday, anniversary — yearly).
Gifts and plans link to people; key dates generate reminders early enough to
prepare (and pull in linked gift ideas).

Per-type examples (expected behavior):
- Recipe: Want to → Planned (shopping list as steps) → Done (rating) → keep →
  "My recipes", repeatable.
- Book: Want to → Doing (start date) → Done (finish date, main ideas, rating).
- Podcast/video: Want to → Done + takeaways (transcript-assisted drafts).
- Business idea: Want to → Doing (experiments as steps, notes over time) →
  Done ("pursued") or Dropped ("parked").
- Date night: Planned with date + lead-time steps → Done (memory note,
  "would repeat").
- Purchase: Want to → Doing (comparing/cool-off) → Done (bought) / Dropped.
- Gift: linked to a person + occasion; surfaces before that date.

### Message routing (capture vs request)

Plain text can be a capture ("try pottery class") or a request ("I have 2 h
free Saturday", "books I read this year"). **The AI decides**, with a safe
default (owner decision):
- Every incoming message is saved raw first, before any AI step.
- If the AI judges it a request, it answers and the raw copy is discarded.
- If it is unsure, it treats it as a capture and adds a button "That was a
  question →" that re-runs it as a request.
- `/commands` (e.g. `/suggest`, `/find`, `/library`) are always requests.
The eval set covers routing.

### Capture flow

1. I share a link (optionally with a note), type a thought, or send an image.
2. stash saves it **immediately** (raw) so nothing is lost if AI fails.
   Images are stored as files.
3. Enrichment: yt-dlp / page metadata (title, description, caption). Instagram
   often needs a login; my note covers that gap.
4. AI files it: type, title, details, stage, tags, people.
5. Reply: one line, e.g. `✅ Places · Tokyo · Want to`, with **fix buttons**
   (change type / stage / edit). It asks a question only if it truly can't
   tell.
6. Transcripts (media): use existing captions (yt-dlp) when available;
   otherwise enqueue **faster-whisper** (GPU). The queue runs when the LLM is
   idle because both share 12 GB VRAM. Transcript enables summary + draft
   takeaways.
7. **Images / screenshots (owner: decide later, by what works).** v1 saves the
   image with my note and files it from the note alone. The M1 eval includes
   image cases and compares local OCR → text model against a local vision
   model (and OpenRouter vision as a reference). The winner is adopted;
   recorded as an ADR.
8. **Bursts (builder call):** several messages arriving within a short window
   (e.g. forwarding a backlog) get one combined confirmation instead of one
   reply each; filing and enrichment are queued. If any of them is deferred
   (see *Busy mode* below), the confirmation's first line names `/stash_retry`.

### Tool scope (builder call)

The Hermes agent gets **only stash's tools plus read-only web fetching** for
enrichment. No terminal, file or code-execution toolsets. Reasons: a small
local model calls tools more reliably with fewer of them, tool definitions use
up context, and a Telegram-reachable agent with shell access is a security risk.
The owner can widen this later.

### GPU sharing (owner games on the 3080 Ti sometimes)

stash must stay out of the way when the GPU is busy:
- **Unload when idle:** Ollama `keep_alive` short (≈5 min), so VRAM is free
  except right after stash used it. Cost: a slow first reply after idle.
- **Busy detection:** before any GPU job, check `nvidia-smi` (works in WSL2)
  for free VRAM / utilization caused by others. Below threshold → busy mode.
- **Manual switch:** `/gpu off` / `/gpu on` (also auto-expires after a few
  hours) for when I know I'm about to game.
- **Busy mode:** captures are still saved raw and acknowledged ("saved, not
  filed yet; `/stash_retry` files it"); AI filing does not run while the GPU is busy, and the
  Whisper queue likewise.
  Optional config `busy_fallback = openrouter` sends filing to OpenRouter
  instead of waiting (default: wait — builder call, keeps it free and
  private). See *LLM providers* below.
- Whisper and the LLM never load at the same time.

### Nudges

- **Weekly digest — Sunday 10:00 America/Los_Angeles:** new items, forgotten
  old ones, upcoming dates/steps/people dates, and a few suggestions.
- **Time-based reminders:** item dates, step lead times, people key dates.
- **On-demand suggestions:** "I have 2 h free Saturday afternoon, at home" →
  2–3 picks from my list with reasons.
- **Morning-after follow-up (owner decision):** the morning after a Planned
  item's date, one short message "How was <date night>?" with rate / keep /
  notes / didn't happen buttons. Noise rules (builder call): at most one
  follow-up message per day (batch several items into it), skip items that
  already have an outcome, never ask twice about the same item. Items stuck in
  Doing for weeks (a book) are asked about in the Sunday digest instead.
- **Catch-up:** on startup, send anything that came due while the PC was off
  (digest included), batched into one message rather than a flood.

### LLM providers: plug and play (owner request)

OpenRouter is **fully implemented and tested from M1**, not just a future
option. Switching takes one config line plus an API key:

```toml
[llm]
provider = "ollama"            # or "openrouter"
busy_fallback = "wait"         # or "openrouter" when the GPU is busy

[llm.ollama]
base_url = "http://localhost:11434/v1"
model = "<chosen by eval>"

[llm.openrouter]
model = "<chosen by eval>"     # key comes from env OPENROUTER_API_KEY
```

- One provider interface in the core (OpenAI-compatible chat + tool calls)
  with two implementations, both covered by the same contract tests (fake
  HTTP on the Mac, real calls on the PC).
- **Per-task override** (builder call), e.g. `[llm.tasks] suggestions =
  "openrouter"`, so routine filing can stay local while heavier tasks use the
  cloud ("hybrid" without code changes).
- The setting reaches both stash's own LLM calls and Hermes' agent provider
  config, so the whole bot switches together. A `stash doctor` command checks
  the active provider is reachable and the key and model are valid.
- If the active provider fails (Ollama down, OpenRouter error), captures are
  still saved raw and stay saved; `/stash_retry` files them. Nothing is lost.
- The eval runs the same cases against both providers, so the switch is an
  informed one.

### Browsing

- Chat: list/filter/search ("books I read this year", "kept recipes"), inline
  paging.
- Read-only **HTML library**: single self-contained HTML file, sent via
  Telegram on `/library` and kept on the PC. Nothing published to the
  internet.

### Backups

Nightly (or on startup if missed) copy of `stash.db` (SQLite online backup
API, not a raw file copy) to the NAS SMB share; keep 30 days.

### Local-model eval

A scripted eval set ships in M1: ~25 realistic **fake** captures and queries
(filing, field extraction, tool-call correctness, suggestions, step
proposals). One command runs it against local Ollama and OpenRouter and prints
a scored comparison. Decides whether local is good enough.

## Milestones

Each is usable on its own.

- **M0 — Skeleton + spike.** Hermes in WSL2 talking to Telegram and Ollama;
  stash plugin with capture → SQLite → `/list`. Resolve the six unverified
  points above, record findings, and apply the **go/no-go gate**.
- **M1 — AI filing.** Provider layer with **Ollama and OpenRouter both
  working** (config switch, per-task override, `stash doctor`), message
  routing, link metadata, AI type/details/stage, fix buttons, burst handling,
  GPU busy mode, eval set (local vs OpenRouter, incl. routing and image
  cases), model choice.
- **M2 — Lifecycle.** Stages, outcomes, keep/library, repeats, groups.
- **M3 — Planning & nudges.** AI-proposed steps (confirm), reminders, Sunday
  digest, morning-after follow-ups, catch-up, NAS backups.
- **M4 — People** and key dates.
- **M5 — Transcripts:** captions + Whisper queue, summaries, draft takeaways.
  Image reading (OCR or vision, per M1 eval).
- **M6 — HTML library:** Telegram file.
- **Later:** Gmail / Google import via Hermes' google-workspace skill.

## Decisions left to the builder

- Exact SQLite schema, migrations approach, and module layout (core vs Hermes
  adapter).
- Scheduler mechanism, subject to spike finding #2.
- Local model and quantization, subject to the eval.
- Tool names/schemas exposed to the agent and the system prompt/skill text.
- HTML styling.
- Hermes version to pin and the upgrade procedure.
- WSL service setup details (systemd units, Task Scheduler entry,
  `.wslconfig`, SMB mount).
- Python tooling (uv vs pip, ruff, pytest) — follow the python-development
  skill's conventions.
