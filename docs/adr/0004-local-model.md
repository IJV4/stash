# 0004 — Local model: qwen3.5 as baseline, 64k context set server-wide

**Status:** Accepted, provisional until `stash eval` (spike #5)

## Context
Target GPU: RTX 3080 Ti, 12 GB. Hermes needs ≥64k context; Ollama's `/v1` API cannot set
context per request, so it must be set server-wide (`OLLAMA_CONTEXT_LENGTH`).

## Measured (2026-11-03, Ollama 0.33.2)
- `qwen3.5:latest` (9.7B, Q4_K_M; capabilities: completion, vision, tools, thinking) at
  `num_ctx=65536`: 7.6 GB, 100% GPU, 9.4 GB total VRAM in use with the desktop's own use.
  Cold load ≈ 40 s.
- Already installed and too big for this card with 64k: `qwen3.8` (17 GB), `glm-4.7-flash`
  (19 GB). `ornith` (9B, no vision) also fits.

## Fit tests at 64k (2026-11-03, after the Ollama override was applied)
| Model | Result |
|---|---|
| `qwen3.5:latest` | 7.6 GB, context 65536, 100% GPU. Fits with ~2.8 GB to spare. |
| `gemma4:12b` | 8.0 GB on disk; context 65536, 100% GPU; 10.9 GB in use on the card in total. Fits, ~1.3 GB spare, so little headroom for a second load. |
| `qwen3:8b` | **Rejected for Hermes use.** Context capped at 40960 (below the 64k Hermes needs) and 11% CPU / 89% GPU split at 11 GB. |

Eval candidates are therefore `qwen3.5` and `gemma4:12b`.

## Latency finding: thinking (2026-11-04)
Two fake messages through the live gateway: capture-to-filed 45.6 s (cold load) and 25.5 s
(warm). stash sends no reasoning control, so `qwen3.5` (thinking-capable) reasons before
every filing answer. Measured on a small classify prompt, warm, via Ollama `/v1`:

| Request | Wall time | Completion tokens |
|---|---|---|
| default | 4.7 s | 441 |
| `"reasoning_effort": "none"` | 0.2 s | 11 |

`reasoning_effort: "none"` works on `/v1` with Ollama 0.33.2. Follow-up for the Mac: add a
per-task setting (filing off by default) and let `stash eval` score thinking on vs off for
quality before it becomes the default. Not changed on the PC.

## Eval baseline: qwen3.5 (2026-11-04, fake cases, thinking on)
`stash eval --providers ollama --arms text,ocr` on `evals/cases.jsonl` (25 cases):

| arm | route | type | stage | date | details | p50 latency | errors |
|---|---|---|---|---|---|---|---|
| text (22) | 91% | 100% | 94% | **0%** | 100% | 31.7 s | 0 |
| ocr (3) | 67% | 67% | 100% | 0% | n/a | 17.9 s | 1 |

Single-case reruns: the two cases that expect a **date** both fail. `t10` ("Date night at the Harbor
Jazz Club on 2027-03-14 at 8pm", expects stage `planned`, date `2027-03-14`) routes correctly but gets
the stage and the date wrong. The OCR arm case `i02` (event poster) errors; Tesseract itself read the
poster text correctly ("Saturday 22 May 2027"), so the failure is after OCR (not isolated further;
the report shows only aggregates). `i01` and `i03` pass. Date handling is the weak spot to
investigate on the Mac: print per-case model output in the eval report, reproduce `t10`, and rerun
with thinking off (see the latency finding above). Vision arm and gemma4:12b not run yet.

## Decision
Use `qwen3.5:latest` for filing and for the vision arm as the baseline. Compare against
`gemma4:12b` with `stash eval` (`qwen3:8b` was rejected, see above); adopt the winner on score and latency.
The server override (`deploy/systemd/ollama.override.conf`) must be applied; verify with
`ollama ps` showing `CONTEXT 65536`.

## Consequences
- One model can serve both text and image cases, so no second model competes for VRAM
  (the spec forbids the LLM and Whisper loading together).
- Web rankings of 12 GB models disagree; only the local eval counts.
