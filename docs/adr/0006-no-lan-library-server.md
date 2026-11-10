# 0006 - no LAN library server: the Telegram file is the one way to read the library

**Status:** Accepted (2026-11-09). Replaces the "served on the home LAN" part of the spec's Browsing section and milestone M6.

## Context
M6 planned two ways to read the HTML library: a file sent in Telegram on `/library`, and
`stash serve`, a read-only page on the home network (a token in the URL, WSL mirrored networking, a
Windows Firewall rule plus a Hyper-V firewall rule, its own systemd unit). The Telegram file came
first (`/library html`, also kept on the PC as `latest.html`). The server landed on 2026-11-07 and
its phone reachability (spike #28) was still unverified on the PC.

## Decision
Delete `stash serve`. The Telegram file is the only delivery: the owner already has the bot open on
the phone, the file is one self-contained HTML page, and the PC keeps the latest copy. The server's
one advantage was a page that is always current. That does not justify a second network surface
with a token as its only lock, two firewall rules, a service to run, and the parked defects of a
hand-written single-threaded HTTP server (slow clients, query and cookie parsing, token-load
failure, the snapshot lock). A library over the 45 MB send limit is still written to the PC copy
before the size check, and the reply points at that copy.

**Rejected:** keep the server and fix its parked items (a threaded server, stricter parsing, a
probe that does not share the HTTP client). That keeps every deployment step and the exposure, and
adds code, for a convenience the Telegram file already covers.

## Consequences
- `stash.library_server`, `stash.library_access`, `stash.library_server_probe`, the `[library]`
  table in `stash.toml`, the `serve` command, the doctor's library-server line,
  `Store.read_snapshot` and `deploy/systemd/stash-serve.service` are gone. stash refuses a config
  that still has a `[library]` table.
- `networkingMode=mirrored` stays in `.wslconfig` (it makes `localhost` work both ways); stash
  itself exposes nothing to the home network.
- A PC that set `stash serve` up from an earlier version follows the note at the end of
  `docs/deploy/wsl-setup.md`.
- Spike row #28 is dropped; row #27 expects the new too-big reply.
- The phone holds a snapshot: after the library changes, `/library html` sends it again.
