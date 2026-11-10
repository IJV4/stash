# Architecture decision records

One short file per decision: context, options, decision, consequences. Numbered in
order; a changed decision gets a new ADR that supersedes the old one.

| # | Decision | Status |
|---|----------|--------|
| 0001 | Keep Hermes as the Telegram host (M0 go/no-go) | Go (gate #1, #6 passed 2026-11-04); other checks open |
| 0002 | Python as the implementation language | Accepted |
| 0003 | OCR is an optional extra, adopted only if it beats vision | Accepted |
| 0004 | Local model: qwen3.5 as baseline, 64k context set server-wide | Accepted (provisional) |
| 0005 | stash in its own Hermes profile, hardened user service | Accepted |
| 0006 | No LAN library server: the library is a Telegram file | Accepted |
