# 0005 - stash runs in its own Hermes profile, as a hardened systemd user service

**Status:** Accepted (2026-11-04). Supersedes the "edit the default Hermes config" choice made earlier the same day.

## Context
The PC's Hermes was already in use. Following `wsl-setup.md` literally edited its default config:
local model, Telegram toolset `[web, stash]`, and a *global* `agent.disabled_toolsets` that also
disabled terminal/file tools in the owner's own `hermes` CLI. The gateway ran in a terminal as the
owner with full access to the owner's home folder (SSH key to the Mac, Claude credentials, history).
Hermes is not sandboxed (terminal backend `local`, plugins in-process); its protection is an
allowlist of toolsets.

## Decision
1. **Own profile.** `hermes profile create stash --no-alias --no-skills` (`--no-alias` because the
   wrapper would be named `stash` and clobber the stash CLI). The profile holds the local-model
   settings, the Telegram toolset `[web, stash]`, the disabled toolsets, the plugin and the bot
   token (copied across without printing). The default profile was restored from its backup:
   terminal/file tools on, no Telegram token.
2. **Own process.** `gateway.standalone: true` in the stash profile's config. Hermes calls this "a
   temporary compatibility shim, not a supported topology"; the default is one multiplexing host
   gateway for all profiles. Revisit when Hermes is updated (updates are reviewed, never run
   casually).
3. **Hardened user service.** `hermes -p stash gateway install` (unit `hermes-gateway-stash.service`,
   enabled at login, lingering already on) plus a drop-in, saved as
   `deploy/systemd/hermes-gateway-stash.hardening.conf` (tested as written, paths are for user
   `ismael`): no new privileges, private /tmp, read-only system, `ProtectHome=tmpfs`, Windows drives
   inaccessible, the stash source/config/deno read-only, `~/.hermes` and the stash data directory
   writable, and the default profile's `.env`, backups, sessions and memories inaccessible.

## Verified (through the running service's mount namespace)
`~/.ssh`, `~/.claude`, shell history and other projects do not exist for the service;
`/mnt/c` is denied; writes to `/etc` and to the stash repo fail; the default `.env` is denied;
Telegram still connects (polling mode). The stash database is `700`/`600`.

## Consequences and remaining risk
- The service can still read the stash profile's own `.env` (the bot token, which it needs), write
  to `~/.hermes` (including Hermes's own code, because its launcher keeps lock and state files in
  the root: a read-only mount made it crash-loop), use the network freely, and read the stash
  database.
- The launcher warns that it cannot read `~/.hermes/.env` ("terminal policy unavailable") or back up
  into `~/.hermes/backups`; both are expected and harmless (the terminal toolset is off).
- **Plugin hot-reload still breaks stash's replies** until the gateway restarts (ADR 0001): restart
  with `systemctl --user restart hermes-gateway-stash` after any `hermes plugins enable/disable`.
- Unit management: `systemctl --user {status,restart,stop} hermes-gateway-stash`,
  `journalctl --user -u hermes-gateway-stash`.
- WSL still needs the Windows Task Scheduler entry (`wsl-setup.md` section 2) so Ubuntu, and therefore
  the service, is running after a reboot.
