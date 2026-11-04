# 0003 — OCR is an optional extra, adopted only if it beats vision

**Status:** Accepted (2026-11-03)

## Context
Images can be read two ways: send them to a vision model, or OCR them with Tesseract and
file the text. The local model `qwen3.5` accepts images, so the vision arm may already do
the job without a second system dependency (`tesseract` binary plus `pytesseract` and
`pillow`). The spec makes the eval decide (spike #12, `stash eval --arms text,vision,ocr`).

## Decision
- `pytesseract` and `pillow` move to the optional extra `ocr` (`uv sync --extra ocr`).
  They stay in the dev group so `make check` still tests the adapter.
- `make_ocr` falls back to `NoOcr` when the `tesseract` binary is missing **or** the extra
  is not installed (previously the second case raised `ImportError`).
- Adopt OCR in the pipeline only if the eval's OCR arm scores clearly better than vision
  or is much faster on the 12 GB card. Otherwise drop the extra.

## Consequences
- The extra is installed with the dev group (`make install`); a runtime-only install can skip it and the apt package. The eval's OCR arm still needs both
  `tesseract-ocr` and the extra.
- Record the eval result here when spike #12 runs.
