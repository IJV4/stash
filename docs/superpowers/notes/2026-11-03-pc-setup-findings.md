# PC bring-up findings (2026-11-03)

> Snapshot from the start of the session. Where it differs from the ADRs (`docs/adr/`), the ADRs are current.

Session on the Windows PC (WSL2 Ubuntu, RTX 3080 Ti 12 GB). Sources are noted; web
claims come from third-party pages unless marked official, and free-tier numbers move.

## State of the PC

| Item | State |
|---|---|
| Repo | cloned from `stash.bundle` (HEAD `3d969d8`); `origin` = the Mac's repo over SSH |
| `make install` / `make check` | pass: 3035 unit, 60 integration (after `uv.lock` host fix, below) |
| systemd, GPU | on; RTX 3080 Ti 12288 MiB |
| Ollama 0.33.2 | running; the 64k override was **applied later the same day** (ADR 0004) |
| Hermes | git checkout `b7736eca98` (2026-11-03), 412 commits past pin `43a35e8`; `--version` label is stale |
| tesseract 5.3.4, deno 2.9.8, cifs-utils | installed; deno is in `~/.deno/bin`, **not on PATH** |
| Telegram bot, stash plugin | **done 2026-11-04** (ADR 0001); NAS mount not done |
| `~/.config/stash/stash.toml` | created; model and vision model = `qwen3.5:latest` |

## Findings

1. **`uv.lock` points at the Mac's mirror.** All 902 URLs are on `pypi.apple.com`, which does
   not resolve here. Locally rewritten to `pypi.org` / `files.pythonhosted.org` (same
   versions and hashes) and re-locked after the OCR extra. **Uncommitted. Regenerate on the Mac with `uv lock --default-index https://pypi.org/simple` (a plain `uv lock` would re-pin the mirror); do not commit this PC's lock blindly.**
2. **Hermes version is not a blocker.** The installed source already has `inject_message`
   (with `origin`), `spawn_task`, `register_hook`, `register_command` and
   `pre_gateway_dispatch`. A web mirror said `inject_message` returns False in gateway mode;
   the installed source contradicts that. Spike #14 confirms. Do not run `hermes update`.
3. **Ollama context was not 64k (fixed 2026-11-04).** Apply `deploy/systemd/ollama.override.conf` (needs
   sudo). Hermes needs ≥ 64k and `/v1` cannot set it per request.
4. **Model fit (measured).** `qwen3.5:latest` (9.7B Q4_K_M; text, vision, tools, thinking) at
   `num_ctx=65536`: 7.6 GB, 100% GPU, 9.4 GB total in use, ~40 s cold load.
   `qwen3.8` (17 GB) and `glm-4.7-flash` (19 GB) are too big for 64k here. Candidate tags
   confirmed in the Ollama library: `gemma4:12b`, `qwen3:14b` (too big with 64k), `qwen3-vl`;
   `qwen3:8b` was later tested and rejected (ADR 0004).
5. **OCR may be redundant.** The vision-capable local model may make Tesseract unnecessary.
   Done: `ocr` optional extra, `make_ocr` falls back to `NoOcr` if the package is missing
   (new test). Decision rule in ADR 0003.
6. **Hosted free tiers (research, not decided).**
   - OpenRouter is already implemented in stash. Official docs: `:free` models 20 req/min;
     50 req/day, or 1,000/day after a one-time $10 credit purchase; limits are per account.
   - Gemini API: only option with native video input (public YouTube URLs; free tier 8 h of
     video/day). One aggregator says free-tier prompts may improve Google products
     (unconfirmed). Plan 5 summarizes captions/Whisper text, so it does not need this.
   - NVIDIA build.nvidia.com (OpenAI-compatible, ~40 req/min reported, credit rules conflict),
     Groq, Cerebras, Mistral: all would need a third provider (the provider enum is
     hard-coded to Ollama and OpenRouter). No search result gave data-retention terms.
   - Use only for **public** content (transcripts, articles); the request must carry no
     owner notes. Treat fetched text as untrusted.
7. **Config example has an invalid OpenRouter model id** (`nousresearch/hermes-4-70b`;
   `stash doctor` warns). Needs a real id before the eval.

8. **Filing is slow because the model thinks (2026-11-04).** First live messages filed in 45.6 s
   (cold) and 25.5 s (warm). Thinking costs ~4.5 s on a tiny prompt; `reasoning_effort: "none"`
   on `/v1` cut it to 0.2 s. stash has no thinking control yet. See ADR 0004. Mac follow-up.
9. **Smoke test passed (2026-11-04).** Telegram message to stash: raw capture saved, hook
   returned `skip` (no Hermes agent turn), local model filed it (`place / want_to`), reply
   delivered. `/retry` becomes `/stash_retry`. Gate checks #1 and #6 still to run.

## Decisions made

- Python stays (ADR 0002). OCR optional (ADR 0003). Local baseline `qwen3.5` (ADR 0004).
- Hosted free tier: start with OpenRouter; add no new provider until the eval shows a gain.

## Open

- Remaining spike M0 checks (the go/no-go is decided: Go, ADR 0001).
- Pin policy for Hermes; whether to build the Gemini provider later (video).
- Whether the Mac starts Plan 2 before the spike ends (see the plan).

Sources: Ollama library pages (checked live), OpenRouter limits docs
(https://openrouter.ai/docs/api-reference/limits), Gemini video docs
(https://ai.google.dev/gemini-api/docs/generate-content/video-understanding), plus
aggregator comparisons listed in the chat session.
