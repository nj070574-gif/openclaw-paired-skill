# Changelog

All notable changes to the Paired skill are documented in this file. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
