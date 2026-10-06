# Changelog

All notable changes to the Paired skill are documented in this file. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.3.0] — 2026-10-06 — ClawHub audit Phase 2: safe-by-default auto-actions

Phase 2 of the v2.1.1 ClawHub security-audit remediation. This changes two
runtime defaults so the skill no longer acts on the user's behalf without
either an opt-in or confirmation. Previous behaviour is restorable with one
config line each.

### Changed (behavioural — safe defaults, opt-in to restore)
- **LLM SMS auto-reply is now draft-only by default** (`wrappers/paired-respond.py`). Previously a Gemini-drafted answer to a whitelisted "Hi paired," SMS was **texted back to the sender automatically**, contradicting the SKILL.md claim of "no automatic SMS reply". Now the draft is posted to Telegram with a tap-to-copy `/sms` command and the owner sends it. Set `llm_auto_reply=true` in `paired.conf` to restore automatic sending (still whitelist- + cooldown-gated). Addresses T09 Finding 1.
- **Trusted incoming calls now honour `incoming_trusted_action`, default `notify`** (`wrappers/paired-call-handler.py`). Previously any trusted caller was **automatically hung up and sent an SMS**, ignoring the `incoming_trusted_action` setting the config template already documented. The handler now reads that key: `notify` (default — alert only, let it ring), `hangup` (hang up only), or `hangup_and_sms` (the previous behaviour). Unknown/missing values fail closed to `notify`. Addresses T09 Finding 2.

### Docs
- SKILL.md: corrected the LLM-reply section (draft-only default + `llm_auto_reply`), documented `incoming_trusted_action` under the calls section, and added both defaults to the `high_impact_actions` frontmatter.
- `config-templates/paired.conf.example.txt`: added `llm_auto_reply` (default false) and aligned `incoming_trusted_action` values to those the code now honours (notify/hangup/hangup_and_sms).
- Version 2.3.0.

### Notes
- No change to the trusted-numbers allowlist gating, the HMAC inbox dispatcher, or any other flow. Owners who want the old behaviour set `llm_auto_reply=true` and `incoming_trusted_action=hangup_and_sms`.

## [2.2.0] — 2026-10-06 — ClawHub audit: structural hardening + credential/env fixes (Phase 1)

Phase 1 of the v2.1.1 ClawHub security-audit remediation. **Phase 1 is non-behavioural** — no change to runtime defaults (LLM auto-reply, `incoming_trusted_action`, etc.); those are a deliberate Phase 2 follow-up.

### Security
- **Hooks now receive a minimal, curated environment, not the full parent environ** (`wrappers/paired-call-watch.py`, `wrappers/paired-sms-watch.py`). Previously `os.environ.copy()` handed every parent variable — including unrelated secrets such as Gemini keys or Telegram tokens — to each hook subprocess. Now only an explicit allowlist (PATH/HOME/locale/XDG/DBUS + the `BTCALL_*`/`BTSMS_*` event vars) is passed. The shipped tg-hooks read their own credentials from a mode-0600 file, so they are unaffected. Addresses the "Env Variable Harvesting" findings.
- **Voice synth validates its output path** (`voice/paired-voice-synth.py`). Since ffmpeg runs with `-y` (overwrite), the output is now required to be a plain `.wav` and is refused if it is a symlink or non-regular file — preventing an unexpected path from being clobbered. Addresses "Unvalidated Output Injection".

### Added
- **Declarative security frontmatter in SKILL.md:** a `binaries:` allow-list under `requires:` (addresses "Undeclared Tool Scope"), `risk_level`/`risk_acknowledged`, and a `prompt_injection_mitigation:` block documenting that incoming SMS/call/notification content is data (never commands), that dispatch is HMAC-inbox-only, and that high-impact actions are allowlist/`--confirm` gated.
- **"Consent, privacy & legal" sections** in SKILL.md and README — own-device-only, other-party consent (recording/SMS/contacts, two-party-consent/GDPR), cloned-voice disclosure (own voice only; tell recipients it is AI-generated; not an impersonation tool), and device/mic access. Addresses "Missing User Warnings".

### Changed
- **Triggers scoped** in the SKILL.md description: dropped bare/ambiguous words ("pause", "next track", "Bluetooth", "BT", "ofono", "AVRCP", "MAP") that collide with ordinary conversation; kept explicit phone/Bluetooth phrasings and slash-commands, with a note to act only on explicit requests. Addresses "Vague Triggers".
- **Marketing copy reframed** (`skill/marketing/README-marketing.md`): replaced undisclosed-impersonation framing ("Nobody asks questions"; "hears you… not a robot") with own-voice-with-disclosure language. Addresses "Natural-Language Policy Violations".

### Notes
- Scanner false positives confirmed and left as-is: the tg-hook `curl` calls (flagged "External Script Fetching / supply chain") only POST notifications to the user's own Telegram bot API — they download nothing; `bin/bt-adb-setup.py` (~line 79) is a hardcoded probe-file `rm`, not injectable.
- **Deferred to Phase 2 (behavioural):** make LLM SMS auto-reply default-off, enforce `incoming_trusted_action` (notify/hangup/…) in the call hook + `paired-call-handler`, and the related `shell=True` hardening on the hook-dispatch path.

## [2.1.1] — 2026-10-02 — Ship config templates + engine Dockerfiles (ClawHub packaging-filter fix)

### Fixed

- ClawHub's publish file-extension allowlist silently dropped `*.conf.example` and `*.Dockerfile` from the package, so the config templates (and voice-engine Dockerfiles) never reached installers — defeating the v2.1.0 packaging fix. Renamed them with a `.txt` suffix (same convention already used for `*.service.txt`): `paired.conf.example.txt`, `trusted-numbers.conf.example.txt`, `voice.conf.example.txt`, `voxcpm.Dockerfile.txt`, `xtts.Dockerfile.txt`. Setup docs updated to copy-then-strip `.txt`.

## [2.1.0] — 2026-10-02 — Security hardening (audit remediation) + packaging fix

### Fixed

- **First-run setup was broken: the `paired.conf.example` and `trusted-numbers.conf.example` templates are now shipped inside the package.** They previously lived only at the repo root, outside the `skill/` tree that `clawhub publish` packages, so a fresh `clawhub install paired` was missing the two templates the SKILL.md setup steps tell you to copy (steps 2 and 3 failed with "no such file"). Both now sit in `skill/config-templates/` alongside `voice.conf.example`.

### Added

- **`messages_pkg` and `send_button_id` config keys** in `paired.conf` — override the Messages app package and Send-button resource-id for non-Samsung firmware (e.g. Google Messages). Defaults are unchanged (Samsung Messages). See `paired.conf.example`. Note: the compose-detection resource-ids remain Samsung-tuned, so non-Samsung support may need further adjustment.

### Changed

- **Voice config guidance:** `voice.conf.example` now notes that XTTS v2 is the more reliable day-to-day engine and that running only XTTS is fine — `paired-voice-synth` health-checks each service and falls through the ladder automatically.

### Security

Remediation of a security audit (six findings). No change to default behaviour except where noted.

- **Voice service no longer binds `0.0.0.0` by default (`engines/voxcpm-server.py`).** The VoxCPM2 HTTP server previously listened on all interfaces with no authentication. It now binds `127.0.0.1` by default, overridable via the `VOXCPM_BIND` env var. An optional shared-secret gate was added: when `VOXCPM_TOKEN` is set, `/synth` requires a matching `X-Paired-Token` header (401 otherwise); `/health` stays open. When `VOXCPM_TOKEN` is unset, behaviour is open on the (now localhost-only) bind. No XTTS Python server ships in `engines/` (only `xtts.Dockerfile`), so no equivalent change was needed there.
- **Over-broad sudoers recommendation tightened (`bin/bt-recover.py`).** The recommended passwordless-sudo rule in the header docstring granted `/usr/bin/sh` (an effective passwordless root shell). It now pins to the exact commands the tool runs (`rfkill block/unblock bluetooth`, `systemctl restart bluetooth`, `hciconfig hci[0-9] up/down/reset`, and `tee` to the USB `authorized` sysfs path). The USB de/re-authorise step was changed from `sudo sh -c 'echo … > …/authorized'` to a shell-free `sudo tee` helper so the code matches the narrowed rule.
- **Private message logs now created mode 0600 (`wrappers/paired-sms-watch.py`).** The SMS event log (`sms-events.jsonl`, holds full message bodies) and the dedup DB (`sms-seen.db`, holds sender/subject fragments) are now opened with `os.open(..., 0o600)` and `os.chmod`-enforced, instead of inheriting the umask.
- **`respond_local_only` config guard added (`wrappers/paired-respond.py`).** The opt-in LLM-reply feature can now be restricted to on-host processing: when `respond_local_only = true` in `~/.config/paired/paired.conf`, the responder refuses to send any message content to the external Gemini provider and skips the LLM call. Default (unset/false) behaviour is unchanged. An explicit log line now records every time content is about to be sent to an external provider (sender + provider name).
- **Input bounds validation (`setup/paired-voice-setup.py`).** The "which take is cleanest?" prompt parsed `int(input(...))` with no validation and used it to index a list / build an ffmpeg command. It now re-prompts on non-integer or out-of-range input and aborts cleanly on EOF.
- **Silent SMS send gated behind explicit opt-in (`bin/bt_adb.py`).** `sms_send_silent()` (sends SMS via `service call isms` with no UI/consent) now refuses unless `PAIRED_ALLOW_SILENT_SMS=1`, raising `AdbError` otherwise, with a prominent docstring warning. The function is retained so callers are not broken; its only caller, `bin/bt-adb-sms.py --silent`, already surfaces the error cleanly.

## [2.0.1] — 2026-05-26 — Security: historical git scrub + documentation note

### Changed

- **Git history rewrite (no functional code changes)** — All commits on `main` and the v2.0.0 tag have new SHAs. The HEAD tree content is byte-identical to the pre-rewrite v2.0.0. Anyone with a local clone should re-clone or run `git fetch --prune --force && git reset --hard origin/main` to sync.

### Removed

- **Pre-1.0 development tags v1.0.1 through v1.0.11 deleted from GitHub.** These older releases contained illustrative-but-real artefacts that have since been replaced with RFC-compliant placeholders (MAC addresses now use `AA:BB:CC:DD:EE:FF` per IEEE 802 standards-reserved range; default location example replaced with London). `git filter-repo` was used to scrub the same artefacts from every blob across the entire object database, eliminating them from any reachable commit, tag, or branch.

### Notes for installers

- `clawhub install paired` (no version flag) resolves to `latest` which is v2.0.0 — unaffected.
- Installs that explicitly pin to v1.0.1 through v1.0.11 via `clawhub install paired --version v1.0.X` will still succeed because ClawHub's per-version archives are immutable by design (auditability/reproducibility guarantee). Those archives are functionally equivalent to v2.0.0 minus this CHANGELOG note. There is no security or operational reason to remain pinned to v1.0.x; all known v1.0.x users should migrate to v2.0.0 at next convenient opportunity.
- No CVE assigned — the historical artefacts were illustrative documentation strings (a sample BT MAC scan output, a default-city fallback) rather than credentials, tokens, or PII of operational concern.

## [1.0.11] — 2026-05-15 — Add: audio settings preset for call-and-speak

### Added

- **`wrappers/paired-call-and-speak.py` v2.2: audio settings preset** — auto-applies a Samsung-verified-good audio preset (`volume_voice_speaker=5`, `call_extra_volume=0`, `call_noise_reduction=0`) on the phone before dialling. Empirically reduces echo/muffle for the recipient by a large margin during TTS-over-cellular calls. Preset is idempotent — re-applies on every call so any manual UI change on the phone gets auto-corrected. Off-switchable via `--no-preset`. Validated against Note 9 on Android 10 / OneUI 12 / EE network across 13 progressive test calls (clear recipient audio with minimal echo when both phones are physically separated). Pre-v2.2 behaviour was reliant on whatever the phone's current settings happened to be — which on Samsung defaults to `volume_voice_speaker=1` (very quiet) and active noise reduction (which distorts synthesised TTS).

## [1.0.10] — 2026-05-15 — Fix: command-hook glob bug + hardware docs

### Fixed

- **`wrappers/paired-sms-command-hook.py` `latest_session_path()` glob bug** — the function used `SESSIONS_DIR.glob("*.jsonl")` which also matches OpenClaw's `*.trajectory.jsonl` files (much larger, written more frequently). `max(...key=mtime)` would flip the hook between the real session file and the trajectory file. Every file-switch set `last_offset = st_size`, silently dropping any unread content. End-user symptom: `/sms` and `/phone` commands appeared to be ignored — the user message landed in `session.jsonl` while the hook was tracking `trajectory.jsonl`, and by the time the hook returned, its offset was past the message. Bug present since v1.0.0. Fix is one line: exclude trajectory files from the glob.
- Verified end-to-end on 2026-05-15 against a Note 9 install on Debian 13 + OpenClaw 2026.5.12: pre-fix, a `/sms` command in Telegram reached the agent unintercepted and got an "I don't have a tool for that" response; post-fix the same command dispatched correctly via the hook and the SMS arrived at the recipient.

### Documentation

- **Hardware compatibility doc updated** — corrected USB ID for RTL8761B (now lists both `0bda:a760` and `0bda:8771` — both are valid IDs depending on the dongle generation), added empirical verification line (Debian 13 / kernel 6.12.85 / BlueZ 5.82, LE scan: 27 unique advertisers in 5s), added an explicit ⚠ AVOID entry for the **TP-Link UB600 ("BT 6.0 Nano", `37ad:0600`)**: marketed as BT 6.0 but actually reports HCI 5.1, and `hcitool lescan` fails with "Set scan parameters failed: I/O error" on the same kernel/BlueZ where vanilla Realtek dongles work cleanly. Same-port swap test isolated this to the device, not the host. README compatibility table updated to match.
- **Recommendation for new buyers**: vanilla `0bda:`-prefixed Realtek RTL8761B / RTL8761BU dongles are the safe drop-in. Avoid sub-vendor rebadges with marketing claims that exceed BT 5.1.

## [1.0.9] — 2026-05-03 — Fix: display name reverted to canonical

### Fixed

- Display name on the ClawHub registry was auto-derived from the publish staging directory basename during the v1.0.8 publish (became `"Paired Publish V108 225554313"`). The clawhub CLI uses the directory name as the default display name when `--name` is omitted, even on republish. Re-published v1.0.9 with `--name` explicitly set to `Paired — Bluetooth Phone Bridge` to restore the canonical name.

No code changes from v1.0.8. Identical 57-file artifact. Tag added so the GitHub release history matches the ClawHub version timeline.

## [1.0.8] — 2026-05-03 — Fix: SMS compose detection on Samsung Messages 11.5.x

### Fixed

- **`wrappers/paired-sms-send.py` `wait_for_compose()` now detects the compose UI by package focus + uiautomator resource-ids instead of the obsolete `ConversationComposer` activity name.** Samsung Messages 11.5.x renamed the focused activity from `ConversationComposer` to `WithActivity`, which made the legacy substring check return `False` on every poll. Result: every `/sms NUMBER body` invocation aborted with `error=compose_did_not_appear` after the unlock and intent stages had already succeeded — to the user it looked like nothing happened. The new detection checks that `mCurrentFocus` is owned by `com.samsung.android.messaging` AND a uiautomator dump contains both `composer_root_view` and `message_edit_text` resource-ids. Both markers are stable across the 11.5 activity rename.
- The check writes a temp dump to `/sdcard/_paired_compose_check.xml` (distinct from `/sdcard/_paired_ui.xml` used by the send-button locator) so the two phases don't overwrite each other's state.

### Notes

- Verified end-to-end on a locked Note 9 / OneUI 12 / Messages 11.5.50.71: `wake → keyguard locked → auto_unlock OK → intent → compose_visible: true → send_button found → tapped → verified in Sent → screen off → relocked: true`.
- No other code changes. Wrappers, systemd units, and config templates are byte-identical to v1.0.7.

## [1.0.7] — 2026-04-30 — README: "About the security scanner rating" section

### Documentation

- New top-of-README section explains why ClawScan rates the skill `Review` and VirusTotal Code Insight (PaLM) flags it `suspicious`, and what's been done to make it safe to install regardless. Modelled on the equivalent section in the openclaw-magento-skill README. The intent is to meet users at the point where they see the warning and explain the reasoning before they have to ask.
- README badge added: `ClawScan: Review (by design)`.

No code changes from v1.0.6. Identical 57-file artifact.

## [1.0.6] — 2026-04-30 — Display name encoding fix

### Fixed

- Display name on the ClawHub registry was stored as the literal 6-character escape sequence `\u2014` (backslash, u, 2, 0, 1, 4) instead of the actual em-dash character (`—`, U+2014, 3 bytes in UTF-8). Caused by shell-quoting layers during the v1.0.4/v1.0.5 publish from Windows → docker → SSH → kali → openclaw host. Re-published v1.0.6 with the name constructed via `printf '\xe2\x80\x94'` so the byte sequence is correct.

No code changes from v1.0.5. Identical 57-file artifact.

## [1.0.5] — 2026-04-30 — Security: stop scraping /proc/*/environ for API keys

### Security

- **Removed /proc env scraping in `wrappers/paired-respond.py`.** Earlier versions read the OpenClaw process's environment block via `/proc/<pid>/environ` to harvest the `GEMINI_API_KEYS` value at runtime. VirusTotal Code Insight (PaLM) correctly flagged this as the same credential-harvesting technique used by malware, even though the intent was just to reuse the host's already-configured key. The mechanism was wrong shape regardless of intent.
- **New contract:** Gemini keys come from `~/.config/paired/gemini-keys.conf` (mode 0600, refuses to read if more permissive). One key per line or comma-separated. The `PAIRED_GEMINI_KEYS` env var is accepted as an explicit override.
- **Removed `SYSTEMD_UNIT` constant** and the `/etc/systemd/system/openclaw.service` read path. The skill no longer reads other services' unit files.

### Action required for users of `paired-respond`

If you used the SMS auto-responder feature (`Hi Agent, ...` SMS → Gemini-drafted reply):

```bash
mkdir -p ~/.config/paired
echo 'YOUR_GEMINI_API_KEY' > ~/.config/paired/gemini-keys.conf
chmod 600 ~/.config/paired/gemini-keys.conf
```

The skill won't read the key from any other location. If the file is missing or world-readable, `paired-respond` will log an error and skip the LLM call (it will still post a Telegram alert with the question, just without an auto-drafted reply).

## [1.0.4] — 2026-04-30 — Packaging fix: ship the wrappers and systemd units

### Critical packaging fix

v1.0.0 through v1.0.3 inadvertently published only `SKILL.md` and `bin/` to ClawHub. The `wrappers/` and `systemd/` directories were silently dropped at publish time because ClawHub's `listTextFiles()` only includes files with extensions in its text-file allowlist (`md`, `py`, `sh`, `js`, etc), and the wrapper scripts were named `paired-call`, `paired-inbox-hook`, etc. with no extension. Likewise the `.service` units were not in the allowlist.

The OpenClaw safety scanner correctly flagged this as Supply Chain (High/Concern) for v1.0.3 — four of its ten findings (#2, #3, #6, #10) all traced to "the safety wrappers and systemd units described in SKILL.md are not in the published artifact."

**v1.0.4 fixes the packaging:**

- Wrappers renamed: `wrappers/paired-X` → `wrappers/paired-X.py` (14 files)
- Systemd units renamed: `systemd/X.service` → `systemd/X.service.txt` (5 files)
- SKILL.md adds a new "Installation" section showing how to symlink the `.py` files into `~/bin/` (dropping the suffix) and how to copy the `.service.txt` files into `~/.config/systemd/user/` as `.service` (also dropping the suffix)
- Display name updated to **"Paired — Bluetooth Phone Bridge"** (was "Paired — Phone-as-Hardware for OpenClaw")

### Security

- **`bin/bt-call.py` now enforces the trusted-numbers allowlist** (OpenClaw scanner finding #2). The low-level dial primitive previously accepted arbitrary numbers; v1.0.4 refuses to dial unlisted numbers unless `--confirm` is passed. This brings the low-level primitive in line with the wrapper-enforced gating.

### Action required for v1.0.0/v1.0.1/v1.0.2/v1.0.3 users

```bash
clawhub update paired      # pull v1.0.4
```

Follow the new "Installation" section in `SKILL.md` to wire the wrappers into `~/bin/` and the systemd units into `~/.config/systemd/user/`. **Earlier versions did not actually install the wrappers** — they were referenced in SKILL.md but missing from the package. v1.0.4 is the first version where `clawhub install paired` actually delivers the wrapper layer.

## [1.0.3] — 2026-04-30 — Privacy fix

### Security

- **Removed hardcoded ADB device serial** in `skill/wrappers/paired-call-and-speak`. The earlier `ADB_DEVICE = "<serial>"` constant was the skill author's own phone hardware serial — a piece of personally-identifying hardware data that shouldn't have shipped publicly. Replaced with a config-driven loader that reads `adb_device` from `~/.config/paired/paired.conf`, falls back to the `PAIRED_ADB_DEVICE` environment variable, and finally defaults to letting `adb` pick the only attached device.
- **Updated `paired.conf.example`** to document the new `adb_device` key.

### Action required for v1.0.0/v1.0.1/v1.0.2 users

If you used `paired-call-and-speak` with the previous version, the hardcoded
serial would have been ignored on your system unless you happen to have a
device with the matching serial. The fix is purely about removing identifying
data from the published package. To configure your own device:

```
echo 'adb_device = <YOUR_SERIAL>' >> ~/.config/paired/paired.conf
# or:
export PAIRED_ADB_DEVICE=<YOUR_SERIAL>
```

You can find your serial with `adb devices`.

## [1.0.2] — 2026-04-30 — Hardening release

Addresses 10 findings from the OpenClaw safety scanner. None of these were
active vulnerabilities; they were architectural risks and missing safeguards
appropriate for the high-impact capabilities this skill exposes (sending SMS,
placing calls, controlling a paired phone via ADB).

### Security

- **Memory poisoning fix (finding #9):** new `paired-inbox-hook` replaces the
  legacy `paired-sms-command-hook`. The new hook reads commands from a
  dedicated, append-only inbox at `~/.openclaw/paired/inbox/`, with HMAC-SHA256
  signature verification using a key at `~/.config/paired/inbox.key` (mode
  0600). Commands include a timestamp (5-minute clock-skew window) and a
  unique nonce (replay protection). Agent session JSONL logs are no longer
  parsed as a command source.
  - One-time setup: `paired-inbox-hook --keygen`
  - Run: `systemctl --user enable --now paired-inbox-hook.service`
  - Test: `paired-inbox-hook --put '{"command":"phone_verb","verb":"status"}'`
- **Legacy hook deprecated:** `paired-sms-command-hook` now refuses to run
  unless invoked with both `--legacy-jsonl-source` and
  `--i-understand-the-risks`. The systemd unit is no longer auto-enabled.
- **Pairing-agent default change (finding #7):** `bt-agent.py` default mode is
  now `pin` (interactive). Wide-open `--mode auto` without a `--device-filter`
  now requires `--i-mean-it` to opt in to that risk. The previous default
  (broad auto-confirm) was a footgun.
- **SMS fallback opt-in (finding #5):** `paired-call-and-speak` no longer
  automatically sends an SMS when TTS-during-call fails. The fallback is now
  opt-in per invocation via `--with-sms-fallback`. The new inbox-hook
  exposes the same flag as `with_sms_fallback: false` (default) in the
  command JSON.

### Documentation

- **Capability declaration (findings #4, #8, #10):** SKILL.md frontmatter now
  includes `capabilities`, `requires`, and `safety` blocks declaring what the
  skill can do, what it needs, and what scope it operates in. This makes the
  high-impact actions explicit before installation.
- **Telegram dependency declared (finding #10):** Telegram bot integration is
  now listed in `requires.external_services` and the security model is
  documented under a new `## Security model` section in SKILL.md.
- **Trust gating documented (finding #2):** Outgoing SMS and outbound calls
  via the inbox-hook now require either an entry in
  `~/.config/paired/trusted-numbers.conf` OR an explicit `"confirmed": true`
  field in the command JSON. An empty trusted list is the safe default.
- **Reworded "guarantee" language (finding #6):** SMS fallback is now
  described as "best-effort" rather than "guaranteed".
- **Reworded execution-context steering (finding #1):** The earlier
  "do not answer from documentation — execute the tools" line was rewritten
  to be advisory rather than directive. Status queries still favour
  execution; high-impact actions now explicitly call for user confirmation.

### Notes on findings not requiring code changes

- **Finding #3 (supply chain):** the scanner reported that `paired-*`
  wrappers were not in the artifact. They have always been at
  `skill/wrappers/`. v1.0.2 also adds `skill/wrappers/paired-inbox-hook` and
  `skill/systemd/paired-inbox-hook.service` to the bundle.
- **Finding #4 (ADB code execution):** the scanner correctly classifies this
  as `Note` rather than `Concern` — ADB control is the documented purpose of
  this skill. Capability tags now declare it explicitly.

### Action required for v1.0.0/v1.0.1 users

1. `clawhub update paired` to pull v1.0.2
2. `paired-inbox-hook --keygen` to generate the HMAC key
3. `systemctl --user enable --now paired-inbox-hook.service`
4. `systemctl --user disable --now paired-sms-command-hook.service`
   (or stop it manually if already running)
5. Update any external Telegram relay you wrote to drop signed JSON files
   into `~/.openclaw/paired/inbox/` rather than relying on session-log tail.
6. If you used `paired-call-and-speak` and want the previous SMS-fallback
   behaviour, add `--with-sms-fallback` to your invocations.

## [1.0.1] — 2026-04-30 — Security fix

### Security

- **Removed hardcoded sudo password fallback** in `skill/bin/bt-recover.py` and `skill/bin/bt-pan.py`. Earlier versions read `os.environ.get("SUDO_PASS", "<literal>")` with a non-empty default — the literal was a developer credential that should never have shipped. v1.0.1 removes the default entirely; the functions now use `sudo -n` (non-interactive, fails fast if no rule exists) when `SUDO_PASS` is unset, or `sudo -S` only when the user explicitly provides one via env.
- **Updated documentation** in both files to recommend passwordless sudo rules via `/etc/sudoers.d/` for the small set of commands these tools invoke (`rfkill`, `systemctl`, `hciconfig`, `ip`, `dhclient`).
- **No code path requiring the leaked default existed** — `SUDO_PASS` was already documented as the configured way to provide credentials. The default was a leftover from local development.

### Action required for v1.0.0 users

If you installed `paired@1.0.0` and ran `bt-recover` or `bt-pan` without setting `SUDO_PASS`, your scripts attempted to authenticate sudo with the literal default. Update to v1.0.1 (`clawhub update paired`) and set up either a passwordless-sudo rule (recommended) or `SUDO_PASS` in your environment.

## [1.0.0] — 2026-04-29

Initial public release.

### Added

- **Bluetooth phone bridge for OpenClaw agents.** Use the user's own paired phone — over Bluetooth or ADB — instead of renting a number from Twilio, Telnyx, Vapi, or Deepgram. Zero recurring cost, zero third-party dependencies.
- **38 generic Bluetooth tools** covering BlueZ + ofono + ADB, all driving from a configurable phone MAC:
  - `bt-list`, `bt-info`, `bt-pair`, `bt-trust`, `bt-untrust`, `bt-connect`, `bt-disconnect`, `bt-forget`, `bt-recover` — pairing and connection lifecycle
  - `bt-adapters`, `bt-test` — adapter management and 10-check stack health
  - `bt-modems`, `bt-call` — ofono modem state and HFP outgoing calls
  - `bt-contacts` — PBAP phonebook pull (live phone contacts via Bluetooth)
  - `bt-sms-list` — MAP read of SMS history (read-only, RFC-spec)
  - `bt-media`, `bt-volume`, `bt-play` — AVRCP media control and audio routing
  - `bt-send`, `bt-receive`, `bt-browse` — OBEX file transfer (push, pull, FTP)
  - `bt-pan` — Bluetooth PAN tethering (use phone as network gateway)
  - `bt-gatt-tree`, `bt-gatt-read`, `bt-gatt-write` — BLE service/characteristic IO
  - `bt-audio`, `bt-battery` — profile inspection and battery polling
  - `bt-adb-*` — companion ADB-over-USB tools for the few features Bluetooth blocks (SMS send on Samsung, screenshot capture, push/pull)
  - `bt-agent` — passkey/PIN handling daemon
- **13 high-level integration wrappers** for OpenClaw agent use:
  - `paired-call` — JSON-clean dial/answer/hangup wrapper around `bt-call`
  - `paired-call-and-speak` — dial then speak via Tasker TTS intent (with documented Samsung audio-focus block + SMS fail-soft)
  - `paired-call-handler` — the per-call decision engine (trust check + action policy)
  - `paired-call-watch` + `paired-call-watch-tg-hook` — real-time incoming-call daemon, sends Telegram alerts
  - `paired-sms-watch` + `paired-sms-watch-tg-hook` — MAP-MNS push notification daemon, real-time SMS forwarding
  - `paired-sms-send` — autosend SMS via ADB UI automation (Samsung-firmware-aware, optional auto-unlock)
  - `paired-sms-command-hook` — deterministic Telegram `/sms NUMBER text` and `/phone NUMBER` command parser, bypasses the LLM
  - `paired-respond` — optional LLM-drafted SMS reply trigger ("Hi Agent," prefix from trusted senders → Gemini-drafted reply staged to Telegram)
  - `paired-trusted` — manage the trusted-numbers whitelist
  - `paired-media` — auto-fallback BT/AVRCP → ADB media controller
  - `paired-sco-agent` — experimental HFP audio-fd handling for two-way SCO
- **4 systemd user units:** `bt-agent`, `paired-call-watch`, `paired-sms-watch`, `paired-sms-command-hook` — all template-friendly via `User=%i`
- **Configuration templates:** `paired.conf.example` and `trusted-numbers.conf.example`, with sensible defaults
- **Telegram command vocabulary** (all opt-in via `paired.conf[sms_command_hook]`):
  - `/sms NUMBER text` — send SMS via ADB autosend
  - `/phone NUMBER` — dial outbound
  - `/phone NUMBER text` — dial + Tasker TTS speak (with SMS fail-soft for blocked devices)
  - `/phone NUMBER attach <path>` — dial + speak file content
  - `/phone hangup` / `/phone end` — end all active calls
  - `/phone status` — active call state
- **LLM-drafted SMS reply** (showcase feature, configurable trigger phrase, default `"Hi Agent,"`)
- **Trust-gated incoming actions** — non-trusted callers can be silently logged, alerted via Telegram, or auto-rejected per `paired.conf[incoming_*_action]`

### Architectural notes captured

The release ships verbose architectural docs covering hard-won lessons:

- **Samsung Telecom audio-focus block** — `AUDIOFOCUS_GAIN_TRANSIENT_EXCLUSIVE | AUDIOFOCUS_FLAG_LOCK` held for the entire call lifecycle, blocking any third-party app from injecting audio (Tasker TTS included). SMS fail-soft compensates.
- **ofono + PipeWire SCO incompatibility** — both Samsung BCM43142 BT 4.0 and RTL8761B BT 5.1 adapters tested; HFP audio routing remains an architectural limit on Debian 13 / PipeWire 1.4.x. `paired-sco-agent` documented as experimental.
- **Samsung MAP send block** — Bluetooth SMS-send via MAP UpdateInbox not implemented in Samsung firmware; ADB-over-USB autosend is the realistic path. Documented.
- **OBEX-FTP browse** — not advertised by some vendors; tools fall back to OBEX OPP push.
- **PBAP, AVRCP, OBEX OPP, NAP** — all confirmed working, drove design of the wrapper layer.

### Tested hardware

| Phone | Android | Carrier | Working | Blocked |
|---|---|---|---|---|
| Samsung Note 9 | Android 10 / OneUI 12 | UK MNO | Pairing, contacts (PBAP), SMS receive (MAP+MNS), outgoing calls (HFP), media (AVRCP), file transfer (OBEX OPP), PAN tethering, ADB SMS send | Two-way SCO audio, A2DP source, MAP send, in-call TTS |

| Adapter | Type | Working |
|---|---|---|
| BCM43142A0 | Internal BT 4.0 | Pairing, HFP, OBEX, AVRCP, MAP/MNS, PBAP |
| RTL8761B | USB BT 5.1 | Same as above (drop-in via `--adapter hci1`) |

### Known limits (per-phone, not skill bugs)

These are documented exhaustively in `docs/ARCHITECTURE.md` and `docs/HARDWARE-COMPATIBILITY.md`:

- Samsung Note 9 + OneUI 12: no in-call TTS, no MAP send, no two-way SCO. SMS fail-soft compensates for the call-and-speak feature.
- Pixel + AOSP, LineageOS, rooted devices: in-call TTS likely works (untested).
- A2DP source profile: blocked by ofono+PipeWire conflict on Debian 13.

### Security

- **Auto-unlock** is opt-in only. PIN stored at `~/.config/paired/pin` mode 0600. Documented security implications in `paired.conf.example`.
- **Trusted numbers** gate the LLM responder and the call-and-speak command. Empty whitelist = features off.
- **No phone number, MAC, or chat ID is hardcoded.** All identity comes from `paired.conf` and `openclaw.json`.

### Compatibility

Requires:

- Linux with BlueZ ≥ 5.55 and ofono ≥ 1.34 (Debian 11+, Ubuntu 22.04+, Fedora 36+)
- Python ≥ 3.9
- Optional but recommended: ADB tools (for `bt-adb-*` family and SMS autosend)
- OpenClaw ≥ 2026.4.x with the `telegram` channel plugin enabled
