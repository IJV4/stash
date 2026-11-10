# Deploying stash on the Windows PC (WSL2)

Everything runs inside WSL2 Ubuntu. Steps are in order; each ends with a check.
Commands marked **(unverified)** could not be tested from the dev Mac — confirm
them on the PC and fix this file if they differ.

## 1. WSL2 + systemd + GPU

1. Install the normal **NVIDIA driver on Windows** (do not install a Linux NVIDIA
   driver inside WSL).
2. In PowerShell: `wsl --install -d Ubuntu`.
3. Inside Ubuntu, enable systemd — `/etc/wsl.conf`:
   ```ini
   [boot]
   systemd=true
   ```
   then `wsl --shutdown` from PowerShell and reopen Ubuntu.
4. Copy `deploy/windows/wslconfig.example` to `%USERPROFILE%\.wslconfig`, then
   `wsl --shutdown`. It sets mirrored networking (Windows 11 22H2+), so `localhost` works
   both ways between Windows and WSL.

**Check:** `ps -p 1 -o comm=` prints `systemd`; `nvidia-smi` shows the RTX 3080 Ti.

## 2. Keep WSL alive at logon

Task Scheduler → Create Task:
- Trigger: **At log on** (your user)
- Action: Program `C:\Windows\System32\wsl.exe`,
  arguments `-d Ubuntu --exec /bin/sh -c "sleep infinity"`

**Check:** after a reboot and login, `wsl -l -v` in PowerShell shows Ubuntu *Running*.

## 3. Ollama (local models)

```bash
curl -fsSL https://ollama.com/install.sh | sh
sudo systemctl edit ollama        # paste deploy/systemd/ollama.override.conf
sudo systemctl restart ollama
```
Baseline model is `qwen3.5:latest` (text, tools and vision; see
`docs/adr/0004-local-model.md`). Candidates to compare with `stash eval`:
```bash
ollama pull qwen3.5               # baseline, 6.6 GB
ollama pull gemma4:12b            # tag exists in the Ollama library; check size vs 64k context
# qwen3:8b: tested, rejected (context cap 40960 < 64k, spills to CPU), see ADR 0004
```
**Check:** `curl -s localhost:11434/api/tags` lists the models, and after a request
`ollama ps` shows `CONTEXT 65536` (if it shows 4096, the override above was not applied).

## 4. System tools stash uses

```bash
sudo apt update && sudo apt install -y tesseract-ocr cifs-utils git
curl -fsSL https://deno.land/install.sh | sh     # yt-dlp needs a JS runtime for YouTube
```
**Check:** `tesseract --version`, `deno --version`.
`tesseract-ocr` is only for the eval's OCR arm and is optional until it beats the vision
model (`docs/adr/0003-ocr-optional.md`); install the Python side with `uv sync --extra ocr`.

## 5. Get the code and install stash

Copy the repo to `~/projects/stash` (inside WSL, not under `/mnt/c` — much faster).
Keep this exact path: the systemd units in `deploy/systemd/` and the gateway hardening drop-in
(`hermes-gateway-stash.hardening.conf`, `BindReadOnlyPaths=`) all name it. If you check out
somewhere else, change every one of them to match.
```bash
cd ~/projects/stash
python3 -m venv .venv && .venv/bin/pip install uv
make install
mkdir -p ~/.config/stash
cp deploy/stash.toml.example ~/.config/stash/stash.toml   # edit model names
```
**Check:** `.venv/bin/stash --version`.

If WSL has `HTTP_PROXY`/`HTTPS_PROXY` set, also set
`NO_PROXY=localhost,127.0.0.1` — stash's HTTP client honours proxy env vars, and
local Ollama traffic must not go through a proxy.

> **Update 2026-11-04 (ADR 0005):** do not edit your default Hermes. Create a dedicated profile
> (`hermes profile create stash --no-alias --no-skills`), put the model, toolset, plugin and
> Telegram settings in it (`hermes -p stash ...`, plus `gateway.standalone true`), then
> `hermes -p stash gateway install` and add `deploy/systemd/hermes-gateway-stash.hardening.conf`
> as a drop-in under `~/.config/systemd/user/hermes-gateway-stash.service.d/`. Sections 6-7 below
> describe the original default-profile setup.
>
> **Restart the stash gateway after any `hermes -p stash plugins enable/disable`** (for example
> `systemctl --user restart hermes-gateway-stash`). A plugin hot-reload leaves stash unable to
> send replies until a restart (ADR 0001, "stash breaks after a plugin hot-reload"). Drop this
> step once spike-m0 #24 passes.

## 6. Hermes Agent (pinned v0.22.6)

```bash
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
hermes --version          # expect 0.22.6, or a git.<hash> label on a git checkout (the PC runs b7736eca98, ADR 0001); source lives in ~/.hermes/hermes-agent/
```
Hermes updates itself only when you run `hermes update`; don't run it casually.
Record any version change in `docs/adr/`.

Telegram: create a bot with **@BotFather**, then
```bash
hermes gateway setup      # choose Telegram, paste token + your numeric user id;
                          # accept the offer to install the systemd user unit
```
Merge `deploy/hermes/config.yaml.example` into `~/.hermes/config.yaml`.

## 7. Install the stash plugin

```bash
ln -s ~/projects/stash/deploy/hermes-plugin/stash ~/.hermes/plugins/stash
hermes plugins validate ~/.hermes/plugins/stash
hermes plugins enable stash      # consents to stash's Python deps (pyproject.toml)
hermes gateway restart
```
**Check:** `hermes plugins` lists stash as enabled; in Telegram the menu shows
`/list`, `/gpu`, `/stash_retry` (`/retry` is a Hermes built-in).

### Reminders: the ticker and the cron fallback

Reminders, the Sunday digest, follow-ups and step proposals are delivered by an
in-process ticker. The first time Hermes connects Telegram it starts the ticker
(`ctx.spawn_task`); it checks every `[nudges] tick_seconds` (default 60). It
sends to the owner's Telegram DM: the first id in `TELEGRAM_ALLOWED_USERS`, or
`plugins.entries.stash.settings.owner_chat_id` when you set it. With neither,
stash logs one warning and sends no reminders. Nothing else is needed.

**The cron fallback is off by default.** Use it only if the in-process ticker is
not running (spike #26 failed). It sends no buttons, and Hermes wraps the text
in its "Cronjob Response" header and footer.

```bash
cat > ~/.hermes/scripts/stash_tick.sh <<'EOF'
#!/bin/sh
exec ~/projects/stash/.venv/bin/stash tick --config ~/.config/stash/stash.toml
EOF
chmod +x ~/.hermes/scripts/stash_tick.sh
hermes cron create "every 1m" --no-agent --script stash_tick.sh --deliver telegram:<owner id>
```
`--deliver telegram` alone needs a home channel, which there is not, so give the
chat id: `telegram:<owner id>`. `stash tick` prints nothing when nothing is due,
and Hermes then stays silent. `stash tick --dry-run` shows what it would send
and marks nothing. Never run the cron job and the ticker together on purpose:
both record what they sent in the same ledger, so a nudge is not sent twice,
but a message one of them sent is simply never shown by the other.
**Check:** `stash tick --dry-run` prints nothing on a quiet day and the due
reminders otherwise.

## 8. Doctor and eval

```bash
export STASH_CONFIG=~/.config/stash/stash.toml
.venv/bin/stash doctor
.venv/bin/stash eval --providers ollama            # add openrouter once a key is set
```
To enable OpenRouter: put `OPENROUTER_API_KEY=...` in `~/.hermes/.env` **and** in
the environment stash runs with, set `[llm] provider = "openrouter"` (or a
`[llm.tasks]` override) in `stash.toml`, switch the Hermes `model:` block, run
`stash doctor`.

## 9. NAS backups

```bash
sudo mkdir -p /mnt/nas/stash-backups
# /etc/fstab (credentials file chmod 600; values for your Synology share):
# //<nas-ip>/<share>/stash-backups /mnt/nas/stash-backups cifs credentials=/home/<you>/.nas-cred,uid=<you>,gid=<you>,_netdev,nofail 0 0
sudo mount -a
mkdir -p ~/.config/systemd/user
cp deploy/systemd/stash-backup.{service,timer} ~/.config/systemd/user/
systemctl --user daemon-reload && systemctl --user enable --now stash-backup.timer
```
**Check:** `systemctl --user list-timers` shows `stash-backup.timer`;
`systemctl --user start stash-backup.service` writes `stash-YYYYMMDD.db` on the NAS.

## 10. M0 spike

Work through `docs/spike-m0.md` and record the go/no-go decision.

> **If you set up `stash serve` from an earlier version:** disable `stash-serve.service`, delete
> `~/.config/stash/serve.env`, remove both firewall rules (Windows Firewall and Hyper-V, both with
> the display name "stash library") and any `[library]` table in `stash.toml` (stash refuses
> unknown config tables).
