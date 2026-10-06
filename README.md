# Paired: Phone Agent

**Give your AI agent a body. Use the phone in your pocket.**

> *Your assistant can already answer questions. Now it can answer calls, send texts, read your notifications, and speak in your own voice — all through the phone you already own.*

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![ClawHub](https://img.shields.io/badge/ClawHub-paired-orange)](https://clawhub.ai/paired)
[![OpenClaw](https://img.shields.io/badge/OpenClaw-2026.4%2B-blue)](https://openclaw.ai)
[![Linux](https://img.shields.io/badge/Linux-BlueZ%20%2B%20ofono-success)](#prerequisites)
[![Voice](https://img.shields.io/badge/Voice-VoxCPM2%20%2B%20XTTS-purple)](skill/docs/VOICE-SETUP.md)
[![Scanner: Review](https://img.shields.io/badge/ClawScan-Review%20(by%20design)-yellow)](#about-the-security-scanner-rating)

---

## What this is

**Paired: Phone Agent** is an OpenClaw skill that bridges your AI agent to the phone you already own. Bluetooth and ADB do the plumbing. The result is an agent that can:

- **Send and receive real SMS** through your carrier, from your number
- **Place and answer real phone calls** over Bluetooth HFP
- **Read your notifications** in real time
- **Search your contacts**, control your media, transfer files
- **Speak in your own cloned voice** at 48kHz studio quality *(v2.0.0)*
- **Pronounce your name correctly** via word-level audio splicing *(v2.0.0)*
- **Generate voice notes** in 30 languages, all in your voice *(v2.0.0)*

No Twilio, no Vapi, no ElevenLabs, no rented number, no monthly subscriptions, no cloud TTS bills. **Your phone. Your number. Your voice. Your hardware.**

---

## Why install this

Every other phone-skill in the ecosystem rents you infrastructure: a number through Twilio, a calling backend through Vapi, a voice through ElevenLabs. You end up with three subscriptions and a stack of API keys to do what the £100 phone on your desk already does.

Paired uses the phone you already own. The skill talks to it over Bluetooth (audio, calls, contacts, media) and ADB (SMS send, notifications, screen control). Voice cloning runs in a local Docker container on your GPU — VoxCPM2 primary, XTTS v2 fallback, piper as a no-GPU safety net.

**Privacy is structural, not promised.** Your voice reference WAV stays in `~/.config/paired/voice/`. No file leaves your machine. Pull the GPU and the voice clone is gone with it.

📖 **Read the full pitch:** [marketing/README-marketing.md](skill/marketing/README-marketing.md)

---

## What you get

| Command | What it does |
|---------|--------------|
| `/sms send "..."` | Sends a real SMS from your number |
| `/sms read` | Pulls unread texts into the agent context |
| `/call dial ...` | Places a real phone call |
| `/call answer` | Picks up an incoming call |
| `/say "..."` | Speaks through the phone — generic neural voice (piper) |
| `/voice "..."` | Speaks **in your cloned voice** (VoxCPM2, 48kHz) ⭐ NEW v2.0.0 |
| `/contacts find ...` | Searches phone contacts via PBAP |
| `/media play / pause / next` | AVRCP media control |
| `/file send ...` | OBEX file transfer to phone |
| `/tether on/off` | PAN/NAP network bridge |

Inbound events (SMS, calls, notifications) bridge to OpenClaw automatically.

---

## About the security scanner rating — these are features, not vulnerabilities

**ClawScan rates this skill `Review` and VirusTotal Code Insight flags it `suspicious`. That is expected, correct, and by design — it marks _capability_, not malware, a bug, or a vulnerability.** A phone agent that can text, call, read your notifications and speak in your voice *should* light up a static scanner; a version that didn't would be misrepresenting what it does. **Every finding maps to an intentional, documented feature** — listed below, each with the safeguard that gates it.

| Capability (the feature) | What it's for | Control around it |
|---|---|---|
| **Send SMS / place calls** | The agent texts and calls on your behalf | Trusted-numbers allowlist **or** explicit `--confirm`; an empty allowlist blocks all outgoing SMS/calls |
| **Silent SMS send** | Headless send where the Intent UI isn't usable | **Off** unless `PAIRED_ALLOW_SILENT_SMS=1`; otherwise refuses and points to the UI path |
| **Auto-unlock the phone** | Unlock a locked device to send/read | **Off** unless `--auto-unlock` per invocation; PIN read from a mode-0600 file only |
| **ADB device control** | Read notifications, send SMS, drive the screen | Owner-operated, own-device-only; shell-level access is inherent to the feature |
| **Persistent listeners** (systemd) | Real-time SMS push, call alerts, command hook | You enable each service; the command hook acts only on HMAC-signed inbox messages |
| **Relay to Telegram** | Phone events on *your own* Telegram | Your own bot token + chat only; POSTs to the Telegram API, fetches **no** remote code |
| **Voice cloning** | Speak in *your own* voice | Clone your own voice only; disclose AI audio to recipients — **not** for impersonation |
| **Bluetooth auto-pair** | One-shot "pair this device" | Default is **interactive**; `--mode auto` is an explicit opt-in |
| **sudo** (`bt-recover`, `bt-pan` only) | BlueZ daemon reset + PAN bridge need root | Used for exactly those two operations, nothing else |

The Code Insight verdict on an earlier version put the *capability* accurately: *"executing sudo commands ... maintaining persistent systemd services, and full control over a mobile device via ADB ... [these create] a significant attack surface, although no clear evidence of intentional malice was found."* Correct on every count — and every one of those is a feature you install this skill **to get**.

**What the skill genuinely does:**

- Runs sudo for `bt-recover` (BlueZ daemon recovery) and `bt-pan` (NAP/PAN network bridge setup). These specifically need root on Linux.
- Maintains persistent systemd user services for SMS push (MAP-MNS), incoming-call watch (ofono D-Bus), and the HMAC-signed inbox command dispatcher.
- Controls your paired phone via ADB — including, optionally, screen unlock with a stored PIN if you explicitly enable `--auto-unlock`.
- In v2.0.0, runs a Dockerised voice-cloning service (VoxCPM2) and an optional XTTS fallback service, both bound to localhost.

**The safeguards (all in this repo, all auditable):**

- **Trusted-numbers allowlist** for outgoing calls and SMS sends. The agent cannot dial or text an arbitrary number; it can only act on the contacts you explicitly listed in `~/.config/paired/trusted-numbers.conf`.
- **HMAC-signed inbox commands.** The SMS command dispatcher refuses any inbound text that is not HMAC-signed with a secret only present on your machine. A stranger sending an SMS cannot trigger any agent action.
- **Mode 0600 on every secret file** — PIN, API keys, HMAC key. Enforced at startup.
- **Voice cloning is opt-in.** The skill ships no audio. If you never run `paired-voice-setup.py reference`, the cloning subsystem stays inert and the skill behaves exactly like v1.
- **No telemetry. No analytics. No phone-home.** Audit `skill/bin/` and `skill/voice/` — there is no outbound HTTP except to the HuggingFace model download (one-time) and the explicitly-configured Telegram bot if you use SMS-to-Telegram bridging.

If any of the above feels too much for your threat model: don't install. The scanner is right that this skill can do a lot. We just disagree that "a lot" means "malicious."

---

## Consent, privacy & legal

This skill controls a real phone and can speak in a cloned voice. With that power come obligations that are **yours** as the operator:

- **Own-device only.** Install only on a host and phone you own, with a Telegram bot you control. Never point it at anyone else's device, number, or accounts.
- **Consent of the other party.** Reading, forwarding or acting on SMS, calls, and contacts — and any call recording — may require the other person's consent and is legally restricted in many places (two-party-consent jurisdictions, GDPR, etc.). Get consent and know your local law.
- **Cloned voice: your own, and disclosed.** Clone only your own voice; never clone someone else's without explicit consent. When your agent sends a voice note or speaks in your cloned voice, tell the recipient it is AI-generated. Using a clone to make someone believe they are hearing the real person live is deceptive and may be unlawful. **Paired is not an impersonation tool.**
- **Device & mic access.** ADB gives shell-level control of the phone; voice setup captures your microphone (`arecord`). Keep the host, the phone, and every secret file (`pin`, `inbox.key`, `gemini-keys.conf`, voice reference) private and mode 0600, off shared machines.

---

## What is new in v2.0.0

| Change | Path | Notes |
|--------|------|-------|
| **Voice cloning subsystem** | `skill/voice/`, `skill/engines/` | VoxCPM2 + XTTS, 4-level fallback ladder |
| **Word-level splicing** | `skill/voice/paired-voice-synth.py` | Pre-record any word; spliced into output verbatim |
| **Long-form chunking** | same | Sentence-boundary split before cloning, gap-free concat |
| **30-language synthesis** | via VoxCPM2 | English, Hindi, French, German, Italian, Malay, Tamil, Japanese, etc. |
| **Guided 5-minute setup** | `skill/setup/paired-voice-setup.py` | 6-phrase reference recording + per-word clip flow |
| **Third-party attribution** | `skill/THIRD_PARTY.md` | Full credit to VoxCPM2, coqui-tts, piper, espeak-ng |

v2.0.0 is **additive**. Every v1.x config works unchanged. If you do not configure voice cloning, the skill falls back to piper exactly as v1.10 did.

📋 **Full changelog:** [skill/CHANGELOG-v2.0.0.md](skill/CHANGELOG-v2.0.0.md)

---

## Prerequisites

- **Linux host** (Debian/Ubuntu tested) with `bluez`, `bluez-tools`, `ofono`, `alsa-utils`, `ffmpeg`
- **Android phone**, Bluetooth paired and ADB-over-Wi-Fi enabled
- **OpenClaw** 2026.4 or later
- **Optional, for voice cloning:** Docker, NVIDIA GPU with 6GB+ VRAM, `nvidia-container-toolkit`
- **Optional, for SMS auto-reply:** Gemini API key

---

## Hardware compatibility

Tested working: Samsung Note 9 / OneUI 12. Multiple Bluetooth adapter chipsets known good — see [docs/HARDWARE-COMPATIBILITY.md](docs/HARDWARE-COMPATIBILITY.md).

Have a working setup we haven't tested? **[Open a hardware compatibility report](https://github.com/nj070574-gif/openclaw-paired-skill/issues/new?template=hardware_report.md)** — every confirmed combination helps the next person.

---

## Install

```bash
clawhub install paired
```

Then read:

1. [docs/PAIRING-GUIDE.md](docs/PAIRING-GUIDE.md) — pair your phone, configure the conf file
2. [skill/docs/VOICE-SETUP.md](skill/docs/VOICE-SETUP.md) — clone your voice (5 minutes)
3. [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — how the pieces fit together

Or build from source:

```bash
git clone https://github.com/nj070574-gif/openclaw-paired-skill.git
```

---

## License

MIT. See [LICENSE](LICENSE).

This skill bundles its own original code only. Third-party engines (VoxCPM2, coqui-tts, piper, espeak-ng, BlueZ, ADB, ffmpeg) are downloaded by the user at build/install time; none of their source code is included in this repository. Each remains under its own license — full attribution in [skill/THIRD_PARTY.md](skill/THIRD_PARTY.md).
