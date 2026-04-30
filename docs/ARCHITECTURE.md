# Architecture

> The deep-dive companion to [README.md](../README.md). This is the *why* — the design choices, the constraints, the things we tried that didn't work, and the trade-offs each working feature makes.
>
> Read this before opening an issue about "feature X doesn't work" — most of those have a section here explaining the firmware or kernel reason and the workaround we settled on.

## Two transports, one skill

Paired uses **two parallel paths to the phone**, by necessity:

```
                   ┌─────────────────────────┐
                   │  OpenClaw agent (LLM)   │
                   └────────────┬────────────┘
                                │
                  ┌─────────────┴──────────────┐
                  │                            │
        ┌─────────▼─────────┐        ┌─────────▼─────────┐
        │  paired-* wrappers│        │  paired-* wrappers│
        │  (high-level)     │        │  (high-level)     │
        └─────────┬─────────┘        └─────────┬─────────┘
                  │                            │
        ┌─────────▼─────────┐        ┌─────────▼─────────┐
        │  bt-* CLI tools   │        │  bt-adb-* tools   │
        │  + bt_*.py libs   │        │  + bt_adb.py lib  │
        └─────────┬─────────┘        └─────────┬─────────┘
                  │                            │
        ┌─────────▼─────────┐        ┌─────────▼─────────┐
        │  BlueZ + ofono    │        │  ADB-over-USB     │
        │  D-Bus            │        │                   │
        └─────────┬─────────┘        └─────────┬─────────┘
                  │                            │
                  └────────────┬───────────────┘
                               │
                       ┌───────▼───────┐
                       │   The phone   │
                       └───────────────┘
```

**Bluetooth path** — used for everything the phone vendor lets us do over Bluetooth: pairing, contacts (PBAP), SMS receive (MAP/MNS), outgoing calls (HFP), media control (AVRCP), file transfer (OBEX), tethering (PAN), BLE GATT. Cable-free, runs continuously, low power.

**ADB path** — used only where the vendor blocks the Bluetooth equivalent. On Samsung, that's primarily SMS-send (MAP-send is unimplemented in firmware) and a few ADB-only conveniences (screenshot, media-controller fallback, lock-screen unlock). Requires a USB cable but works around firmware restrictions.

The wrappers (`paired-*`) hide which transport is being used. `paired-sms-send` will use ADB even though it sounds like a Bluetooth thing — because that's the only path that works. `paired-media` tries AVRCP first, falls back to ADB media-controller automatically.

## The bt_lib / bt_adb / bt_obex / bt_telephony / bt_audio / bt_media split

The Python library files in `skill/bin/` are imported by the CLI tools — they're not entry points. They're split by D-Bus surface area:

| Library | Responsibility | Wraps |
|---|---|---|
| `bt_lib.py` | Adapter discovery, address normalization, recovery, common helpers | `org.bluez.Adapter1` |
| `bt_adb.py` | ADB push/pull/shell/uiautomator with timeouts and clean errors | `adb` CLI |
| `bt_obex.py` | OBEX session lifecycle (push/pull/browse) | `org.bluez.obex.*` |
| `bt_obex_msg.py` | MAP-specific OBEX (message folder list, get message body) | `org.bluez.obex.MessageAccess1`, `Message1` |
| `bt_telephony.py` | ofono modem + voice-call + SMS API wrappers | `org.ofono.*` |
| `bt_audio.py` | PipeWire BT object resolution + profile inspection | `wpctl` + PipeWire D-Bus |
| `bt_media.py` | AVRCP transport control via BlueZ MediaPlayer1 | `org.bluez.MediaPlayer1` |

Each CLI wraps one of these, exposes a focused command interface, and emits structured output with `--json`. The high-level `paired-*` scripts wrap the CLIs (not the libraries directly) so they can be called as subprocesses by anything — Python, Bash, Telegram hooks.

## Known limits — the things that don't work, and why

### Samsung audio-focus block (in-call TTS)

**Symptom**: `paired-call-and-speak` connects the call, the Tasker TTS intent fires, but the recipient hears nothing.

**Cause**: Samsung's `Telecom` system service holds an `AUDIOFOCUS_GAIN_TRANSIENT_EXCLUSIVE | AUDIOFOCUS_FLAG_LOCK` (req=2, flags=0x4) for the entire ring + call lifecycle. This is a hardened audio-focus claim that prevents any non-system app from injecting audio into the call audio path.

**Evidence**: in `~/.paired/call-and-speak.log` you'll see Tasker successfully bind the TTS engine, request audio focus with `usage=USAGE_VOICE_COMMUNICATION` and `stream=AUDIO_STREAM_VOICE_CALL`, then `MediaFocusControl` revokes focus within 1ms — no `[Synthesize]` lines during `MODE_IN_CALL`.

**Why this exists**: Samsung treats voice calls as a hardware feature with strict audio-routing. It's not an Android limitation — AOSP and most non-Samsung skins allow this. Pixel + stock Android, LineageOS, and rooted devices are reported to allow in-call TTS (untested in this skill).

**Workaround**: `paired-call-and-speak` and the `/phone NUMBER text` command both have **SMS fail-soft** built in. If the speak command runs but the recipient won't hear it (we don't know per-call whether they will or won't — it depends on their device), the same content is also fired as an SMS. The Telegram reply notes "📨 SMS fail-soft: delivered" so the user knows something was delivered.

If you have a non-Samsung phone, the speak path likely works — please [open a hardware report](https://github.com/nj070574-gif/openclaw-paired-skill/issues/new?template=hardware_report.md).

### ofono + PipeWire SCO conflict

**Symptom**: Outgoing calls connect via ofono, but the audio routes through the phone earpiece — not through the host's speaker/microphone. Two-way audio is not available.

**Cause**: ofono 2.16 + PipeWire 1.4.x + libspa-bluetooth 1.4.x do not cooperate for HFP audio routing on current Linux distros. ofono claims the HFP audio fd, but PipeWire doesn't pick it up as a usable SCO sink/source.

**Things we tried that didn't work**:

- **Native HandsfreeAudioAgent** — registers cleanly, but ofono hands a file descriptor that's not actually connected to the SCO link
- **PipeWire native HFP backend** — the `audio-gateway` profile won't auto-activate when ofono claims the modem
- **BlueZ Device1.ConnectProfile direct** — returns `br-connection-profile-unavailable` because ofono has the HFP profile claimed
- **Setting profile via wpctl** — `wpctl set-profile <id> audio-gateway` succeeds the call but PipeWire silently reverts to `off` within seconds

**Tested adapters**:

| Adapter | Chipset | BT version | Result |
|---|---|---|---|
| Internal | BCM43142A0 | 4.0 | Same SCO routing failure |
| USB dongle | RTL8761B | 5.1 | Same SCO routing failure |

The conflict is in the userspace audio stack, not the radio.

**Workaround**: Calls work, audio routes through the phone. If you actually need two-way SCO on the host (rare — the phone earpiece is usually fine), the path forward is **Phase A on the roadmap**: build an HFP-HF AT command client that bypasses ofono entirely, opens RFCOMM directly to the phone's HFP-AG, and implements the AT command set + CVSD/mSBC codec negotiation in userspace. That's a significant rewrite (~1500 lines of careful protocol code) and out of scope for v1.

The experimental `paired-sco-agent` is a partial attempt at this — fd lifecycle aware streaming, CVSD-only — shipped as a research artefact, not a working solution.

### A2DP source profile blocked

**Symptom**: You can route audio *into* the phone (host as A2DP sink, phone plays from host) — but not *from* the phone (host as A2DP source, host plays phone music through the laptop speakers).

**Cause**: Same ofono+PipeWire HFP-backend conflict, different manifestation. When ofono has the device, PipeWire blocks the A2DP source profile activation.

**Workaround**: Use `paired-media` for AVRCP control of phone-side playback, or AirPlay-equivalent paths if you need the audio on a different device.

### Samsung MAP-send block

**Symptom**: `bt-sms-send` (Bluetooth path) returns access-denied or silent failure on Samsung.

**Cause**: Samsung firmware does not implement the MAP `UpdateInbox` operation (used by `MessageAccess1.PushMessage`). The MAP-MNS *receive* path is fully supported — Samsung pushes notifications correctly — but inbound MAP write operations are blocked at the framework level.

**Workaround**: `paired-sms-send` uses ADB-over-USB UI automation instead. Steps it performs:

1. Optionally dismiss the lock screen via `input keyevent KEYCODE_MENU` and PIN entry (if `--auto-unlock`)
2. Open the Messages app via `am start` with an `sms:` Intent pre-populated
3. Find the Send button via UIAutomator dump and tap it
4. Optionally re-lock the phone (if `--relock`)

This works on every Samsung model tested, returns a clean JSON result, and is the reason the wrapper has the bare `paired-sms-send` name rather than a `bt-` prefix — the transport is no longer Bluetooth-only.

### OBEX-FTP browse not advertised

**Symptom**: `bt-browse <MAC>` returns `service not advertised` on some phones (notably Samsung).

**Cause**: Vendor SDP records vary. Some phones advertise OBEX-FTP (full filesystem browse), some only OBEX-OPP (push-only).

**Workaround**: Use `bt-send FILE <MAC>` for push, `bt-receive` to listen for pulls. If you specifically need browse, OBEX-FTP works on stock AOSP builds and most non-Samsung Androids — vendor-dependent.

## Trust and security model

### Trust list

`~/.config/paired/trusted-numbers.conf` is the single source of truth for which numbers can:

- Trigger the LLM SMS responder (`paired-respond`)
- Trigger Tasker speak via `/phone NUMBER text` (the speak feature is trust-gated; SMS fail-soft is not)
- Be marked 🟢 in incoming-call alerts

UK numbers are normalised: `07XXX...`, `+44 7XXX...`, `0044 7XXX...`, `447XXX...` all match the same entry. International numbers are stored in E.164 form and matched literally.

The `paired-trusted` CLI manages the file:

```bash
paired-trusted add NUMBER [label]
paired-trusted remove NUMBER
paired-trusted list
```

### Auto-unlock — opt-in PIN storage

`paired-sms-send --auto-unlock` reads a PIN from `~/.config/paired/pin` (mode 0600 enforced; the script refuses to read it if mode is wider). The PIN is sent over USB to the phone via `input text` to dismiss the lock screen.

**Threat model**: anyone with read access to `~/.config/paired/pin` can unlock your phone via ADB while connected over USB. This is a meaningful privilege escalation if your host has multiple users or runs untrusted code.

**Decision**: opt-in, off by default. The skill works without it — it just refuses to send SMS while the phone is locked, returning a clean `error=keyguard_locked` JSON result. The user's call.

### LLM trigger phrase

The `paired.conf[llm_trigger]` phrase is a deliberate **explicit-opt-in gate** for the LLM responder. Why? Because an LLM that auto-drafts replies to anyone who texts you is a great way to leak personal info or accidentally agree to things. The trigger phrase ensures only senders who know the password (and are on the whitelist) can engage the LLM.

Default: `"Hi Agent,"`. Set to empty string to disable the responder entirely.

## Real-time push design — MAP-MNS

`paired-sms-watch` is the most operationally sophisticated part of the skill. It:

1. Registers an OBEX MAP Notification Service (MNS) endpoint on the host
2. Tells the phone via MAP `SetNotificationRegistration` to push events to that endpoint
3. Receives MAP-Event-Report objects when SMS/MMS arrive
4. Parses the body, dedupes against `~/.paired/sms-events.jsonl` (some phones double-fire)
5. Calls the configured hook script (`paired-sms-watch-tg-hook` by default) with `BTSMS_*` env vars
6. The hook forwards to Telegram

The dedup is necessary because Samsung Note 9 fires the same event up to 3× depending on how the phone was holding the BT connection. The dedup window is 5 seconds and key is `(sender, first 50 chars of body)`.

If the phone's BT connection drops, MNS goes silent until reconnect. The watcher detects this via D-Bus signal and restarts the registration automatically — no manual intervention needed.

Logs: `~/.paired/sms-events.jsonl` (newline-delimited JSON, one event per line) + `~/.paired/sms-hook.log` (human-readable hook execution log).

## systemd architecture

Four user-level services, all `WantedBy=default.target` so they start at user-session boot:

| Unit | Type | Restart | Notes |
|---|---|---|---|
| `bt-agent.service` | system service (NOT user) | `on-failure` | Pairing PIN/passkey handler. System-level so it can talk to the system bluetoothd. |
| `paired-sms-watch.service` | user service | `on-failure` | MAP-MNS push receiver. `RestartSec=10`, `StartLimitBurst=6`. |
| `paired-call-watch.service` | user service | `on-failure` | ofono D-Bus signal monitor for incoming calls. |
| `paired-sms-command-hook.service` | user service | `on-failure` | Telegram session.jsonl tailer for `/sms` and `/phone` commands. |

User-level services use `User=%i` for templating — works for any username without modification. `bt-agent` is the exception: pairing requires system-bus access so it ships as a system service installed once during setup.

## Why so many tools?

Counting them up:

- **37 Python files in `skill/bin/`** — split into 7 importable libraries and 30 CLI commands
- **13 wrappers in `skill/wrappers/`** — high-level integration scripts
- **4 systemd units**

Why not consolidate? Two reasons:

1. **D-Bus surface granularity**. BlueZ + ofono together expose ~40 D-Bus interfaces. Each of those interfaces becomes one or two CLI commands. Trying to wrap all of them in one giant CLI would mean a `paired do --thing X --subthing Y --opt Z` argument tree that's painful to use and impossible to compose.
2. **Composability**. The CLIs are the agent's primitives — small, focused, JSON-clean. The wrappers compose them. The Telegram hooks compose the wrappers. Each layer adds value (trust gating, auto-unlock, fail-soft, dedup). Mashing it into one binary would lose the layering and make every change a change to a 5,000-line file.

The flip side: 38 + 13 = 51 commands sounds intimidating. The README leads with the **most-used 8** in "First-run setup" and "Per-feature walkthroughs". The agent only needs to know about the `paired-*` wrappers; the lower-level `bt-*` tools are available for power users and debugging.
