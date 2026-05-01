# Paired

**Phone-as-Hardware for OpenClaw agents.**

> Every other phone skill rents you a number. Paired uses the one already in your pocket.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![ClawHub](https://img.shields.io/badge/ClawHub-paired-orange)](https://clawhub.ai/paired)
[![OpenClaw](https://img.shields.io/badge/OpenClaw-2026.4%2B-blue)](https://openclaw.ai)
[![Linux](https://img.shields.io/badge/Linux-BlueZ%20%2B%20ofono-success)](#prerequisites)
[![Scanner: Review](https://img.shields.io/badge/ClawScan-Review%20(by%20design)-yellow)](#about-the-security-scanner-rating)

---

## About the security scanner rating

**ClawScan rates this skill `Review` and VirusTotal Code Insight (PaLM) flags it `suspicious`. This is expected and correct — it is not a sign of malware or malicious intent.**

Paired is, by design, a high-capability tool. Any honest static analysis of what the skill does will produce a high-risk rating. The Code Insight verdict on v1.0.6 lays out the reasoning plainly: *"executing sudo commands ... maintaining persistent systemd services, and full control over a mobile device via ADB ... [these create] a significant attack surface, although no clear evidence of intentional malice was found."* That summary is accurate. Each capability is documented, declared in the SKILL.md frontmatter, and gated by the safeguards described below.

**What the skill genuinely does:**

- Runs sudo for `bt-recover` (BlueZ daemon recovery) and `bt-pan` (NAP/PAN network bridge setup). These specifically need root on Linux.
- Maintains persistent systemd user services for SMS push (MAP-MNS), incoming-call watch (ofono D-Bus), and the HMAC-signed inbox command dispatcher.
- Controls your paired phone via ADB — including, optionally, screen unlock with a stored PIN if you explicitly enable `--auto-unlock`.
- Sends SMS, places calls, reads contacts, and accesses Bluetooth profiles (MAP, PBAP, HFP, AVRCP, OBEX, PAN).

**What's done to make this safe to install:**

- **Trusted-numbers allowlist** gates all outgoing SMS and calls (both via wrappers and the low-level `bt-call.py` primitive since v1.0.4). An empty list blocks everything except explicit `--confirm` invocations.
- **HMAC-signed command inbox** (since v1.0.2) replaces the v1.0.0 design that read commands from agent session logs — commands now require a signature with a key only you control (`~/.config/paired/inbox.key`, mode 0600).
- **Pairing-agent default is interactive** (since v1.0.2). Wide-open auto-pairing requires explicit `--mode auto --i-mean-it`.
- **SMS fallback is opt-in** (since v1.0.2). When TTS-during-call fails, no automatic SMS is sent unless `--with-sms-fallback` is explicitly passed.
- **No credential harvesting** (since v1.0.5). Earlier versions read `/proc/<pid>/environ` to reuse the OpenClaw process's Gemini API key. That mechanism was correctly flagged by VirusTotal Code Insight as a malware-style pattern; v1.0.5 removed it. Keys now come from `~/.config/paired/gemini-keys.conf` (mode 0600 enforced).
- **No hardcoded secrets**, no hardcoded device identifiers (since v1.0.3), no plaintext credentials in the package.
- **PIN auto-unlock is fully opt-in.** The `~/.config/paired/pin` file is enforced mode 0600 and only consulted when `--auto-unlock` is passed. Default config has it off.
- **Capabilities declared explicitly** in the SKILL.md frontmatter under `capabilities`, `requires`, and `safety` blocks — the user (and any reviewing scanner) sees the full list of what the skill can do before installation.

**The scanner is doing its job.** A scanner that rated `paired` as Clean would either be ignoring what it does or rubber-stamping high-impact tools. The `Review` verdict on v1.0.6 is a downgrade from the `Suspicious` rating on v1.0.4, reflecting that all the *fixable* findings (credential harvesting, missing wrappers, untrusted dispatch surface) have been addressed. What remains — sudo, persistent services, ADB control — is the skill itself.

For the per-finding history of what the scanner flagged and how it was addressed across v1.0.0 → v1.0.6, see [CHANGELOG.md](CHANGELOG.md).

---

## What it does

Paired bridges your OpenClaw agent to **your own phone** over Bluetooth and ADB-over-USB. No carrier accounts, no rented numbers, no third-party SaaS. Your phone, your number, your bills.

Out of the box, your agent can:

- **Receive SMS in real time** — push notifications via Bluetooth MAP-MNS, instantly forwarded to Telegram
- **Send SMS** — autosend via ADB UI automation (works on Samsung firmware that blocks Bluetooth send)
- **Make calls** — outgoing dial via HFP and ofono
- **Get incoming-call alerts** — daemon catches every ring and pings you on Telegram with caller ID + trust status
- **Control music** — play / pause / next / volume via AVRCP, with ADB media-controller fallback
- **Pull contacts** — full PBAP phonebook download for caller-ID and search
- **Transfer files** — push and pull via OBEX
- **Tether the network** — use the phone as a NAP gateway
- **Read BLE characteristics** — full GATT read/write/tree
- **Drive everything from Telegram** — `/sms NUMBER text`, `/phone NUMBER`, `/phone NUMBER attach <path>` — all bypass the LLM for deterministic dispatch

It's **38 generic Bluetooth tools + 13 high-level wrappers + 4 systemd user services**, fully configurable, zero personal data shipped.

## Why use this

Every other phone skill on ClawHub or in the OpenClaw ecosystem requires a **paid managed service** (Twilio, Telnyx, Vapi, Deepgram, Kudosity). They give you a *separate* phone number, billed monthly, owned by them.

Paired uses the phone **you already pay for**.

| | Paired | agentcall | claw-voice-call | clawphone | clawdtalk | vapi skills | DeepClaw |
|---|---|---|---|---|---|---|---|
| Phone source | Your own | Provider | Telnyx | Twilio | Telnyx | Vapi | Deepgram |
| Recurring cost | **£0** | Subscription | Per minute + number | Per minute + number | Subscription | Per minute | Per minute |
| API key required | No | Yes | Yes | Yes | Yes | Yes | Yes |
| Phone number | Your existing | New, theirs | New, theirs | New, theirs | New, theirs | New, theirs | New, theirs |
| Receives texts | Yes (your number) | Yes (their number) | Yes | Yes | Yes | Yes | Yes |
| Reads contacts | Yes | No | No | No | No | No | No |
| Reads media state | Yes | No | No | No | No | No | No |
| File transfer | Yes (OBEX) | No | No | No | No | No | No |
| Network tethering | Yes (PAN) | No | No | No | No | No | No |
| Cloud dependency | None | Required | Required | Required | Required | Required | Required |
| Works offline (LAN) | Yes | No | No | No | No | No | No |
| Self-hosted | Yes | Partial | Partial | Yes | No | No | No |

The use cases divide naturally:

- **Twilio-style skills** are for *outbound* business calling — you want a separate, professional number for cold-calls or customer service.
- **Paired** is for *personal-assistant* use — you want your agent to know about texts arriving on your real phone, draft replies for you, alert you to incoming calls, and act on the device you actually carry.

If you've ever thought *"I wish my agent could just see my texts"*, Paired is what you want.

## Hardware compatibility

Tested combinations — see [docs/HARDWARE-COMPATIBILITY.md](docs/HARDWARE-COMPATIBILITY.md) for the full matrix.

| Phone | Android version | What works | What's blocked (phone firmware) |
|---|---|---|---|
| Samsung Note 9 | 10 / OneUI 12 | Pairing, contacts, SMS receive, outgoing calls, media, file push, PAN, ADB SMS send | In-call TTS, two-way SCO, MAP send, A2DP source |
| Pixel + AOSP / LineageOS | (untested) | Likely all of the above | Likely none — community reports welcome |

| Bluetooth adapter | Type | Status |
|---|---|---|
| BCM43142A0 | Internal BT 4.0 | All features working |
| RTL8761B | USB BT 5.1 | All features working (drop-in via `--adapter hci1`) |

Have a working setup we haven't tested? **[Open a hardware compatibility report](https://github.com/nj070574-gif/openclaw-paired-skill/issues/new?template=hardware_report.md)** — every confirmed combination helps the next person.

## Prerequisites

- **Linux** with BlueZ ≥ 5.55, ofono ≥ 1.34. Confirmed working on Debian 13, Ubuntu 24.04, Fedora 40
- **Python ≥ 3.9**
- **ADB tools** (`android-tools-adb` or equivalent) — required for SMS autosend and several utility features
- **OpenClaw ≥ 2026.4.x** with the Telegram channel plugin enabled
- A **Bluetooth-paired phone** (one-time setup; the skill handles re-pairing)
- A **USB cable** for the ADB-dependent features (SMS autosend, media controller fallback). Not needed if you only want receive-side features.

## Installation

### Via ClawHub (recommended)

```bash
clawhub install paired
```

That places the SKILL.md and tools into your OpenClaw workspace at `~/.openclaw/workspace/skills/paired/`, and copies the wrappers into `~/bin/`.

### Manual / from source

```bash
git clone https://github.com/nj070574-gif/openclaw-paired-skill.git
cd openclaw-paired-skill

# Skill content
cp -r skill ~/.openclaw/workspace/skills/paired

# CLI tools
mkdir -p ~/bin
cp skill/bin/* skill/wrappers/* ~/bin/
chmod +x ~/bin/bt-* ~/bin/paired-*
# (the .py files in skill/bin/ are imported as a library by the wrappers, no chmod needed for those)

# Config templates
mkdir -p ~/.config/paired
cp config-templates/paired.conf.example ~/.config/paired/paired.conf
cp config-templates/trusted-numbers.conf.example ~/.config/paired/trusted-numbers.conf

# systemd user services
mkdir -p ~/.config/systemd/user
cp skill/systemd/*.service ~/.config/systemd/user/
systemctl --user daemon-reload
```

## First-run setup

### 1. Pair your phone

```bash
~/bin/bt-list --scan 10               # find your phone in the scan output
~/bin/bt-pair AA:BB:CC:DD:EE:FF --connect
```

Replace `AA:BB:CC:DD:EE:FF` with your phone's actual MAC. The pairing agent (`bt-agent`) handles passkey entry — accept the pairing prompt on your phone screen.

Full pairing walkthrough: [docs/PAIRING-GUIDE.md](docs/PAIRING-GUIDE.md).

### 2. Edit your config

```bash
$EDITOR ~/.config/paired/paired.conf
```

Set at minimum:

```
phone_bt_mac = AA:BB:CC:DD:EE:FF
phone_label  = My Phone
adapter      = hci0
```

### 3. (Optional) Set up trusted numbers

For incoming-call gating and the LLM-trigger feature:

```bash
~/bin/paired-trusted add 07911123456 "main mobile"
~/bin/paired-trusted add +14155552671 "us line"
~/bin/paired-trusted list
```

### 4. (Optional) Enable the systemd services you want

| Service | What it does |
|---|---|
| `paired-sms-watch.service` | Real-time SMS push via MAP-MNS, forwards to Telegram |
| `paired-call-watch.service` | Catches incoming calls, sends Telegram alert with trust status |
| `paired-sms-command-hook.service` | Watches Telegram for `/sms` and `/phone` commands and dispatches them deterministically (no LLM) |
| `bt-agent.service` | Pairing PIN/passkey handler — required for first-time pairing |

```bash
systemctl --user enable --now paired-sms-watch.service
systemctl --user enable --now paired-call-watch.service
systemctl --user enable --now paired-sms-command-hook.service
systemctl --user enable --now bt-agent.service
```

### 5. (Optional) ADB autosend setup

For SMS sending — needs a USB cable to the phone, ADB enabled in developer settings, and the host authorised once on the phone:

```bash
~/bin/bt-adb-setup                    # walks you through the one-time auth dance
```

If you want SMS to work even when the phone is locked, set up auto-unlock:

```bash
echo -n "1234" > ~/.config/paired/pin   # your phone PIN
chmod 0600 ~/.config/paired/pin
# then in paired.conf: auto_unlock = true
```

> **Security note**: storing your phone PIN on this host means anyone with read access to that file can unlock your phone via ADB. Only enable on a host you fully control. The default config has it off.

### 6. Verify

```bash
~/bin/bt-test                         # 10-check stack health
```

If everything's green, your agent is ready to use the skill. Try it from Telegram:

```
You: /sms 07911123456 just testing
Agent: ✅ Sent to 07911123456: "just testing"
```

## Per-feature walkthroughs

### SMS receive — real-time push to Telegram

`paired-sms-watch` registers as a MAP Notification Service client, so the phone pushes new SMS to your host the moment they arrive. The hook script (`paired-sms-watch-tg-hook`) forwards each one to your Telegram chat with sender, body, and timestamp.

Logs: `~/.paired/sms-events.jsonl` (structured) + `~/.paired/sms-hook.log` (human-readable).

### SMS send — ADB autosend with optional auto-unlock

`paired-sms-send NUMBER "text"` opens the Messages app via Intent, types the message via UIAutomator, and taps Send. With `--auto-unlock`, it dismisses the lock screen using the stored PIN; with `--relock`, it re-locks the phone afterwards.

Why ADB and not Bluetooth? Samsung firmware (and most Android vendors) don't implement Bluetooth MAP-Send — see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md#samsung-map-send-block) for the deep dive.

### Outgoing calls — HFP via ofono

`paired-call dial NUMBER` opens an outgoing call through the ofono modem proxy. The audio routes through the phone's earpiece because two-way SCO over BT is blocked by an ofono+PipeWire interaction on current Linux distros — see [the architecture doc](docs/ARCHITECTURE.md#ofono-pipewire-sco) for why.

For *speak-during-call*: `paired-call-and-speak NUMBER "your message"` dials, then fires a Tasker intent on the phone to speak the message via TTS. **On Samsung this is silently blocked** at the audio policy level (see architecture doc); the wrapper has a built-in **SMS fail-soft** that always also sends the same content as SMS, so the recipient is guaranteed to receive the message.

### Incoming-call alerts

`paired-call-watch.service` runs as a daemon, monitors ofono's `VoiceCall` D-Bus signals, and fires a Telegram alert the instant your phone rings. It runs the number through the trust list to mark the alert as 🟢 trusted / 🟡 unknown / 🔴 untrusted in the message.

### Telegram command vocabulary

When `paired-sms-command-hook.service` is running, these commands work in Telegram:

| Command | Action |
|---|---|
| `/sms NUMBER text` | Send SMS via ADB |
| `/phone NUMBER` | Dial outbound |
| `/phone NUMBER text` | Dial + speak via Tasker TTS, with SMS fail-soft |
| `/phone NUMBER attach <path>` | Dial + speak file content via TTS, with SMS fail-soft |
| `/phone hangup` (or `/phone end`) | End all active calls |
| `/phone status` | Show active call state |

These bypass the LLM — they're parsed deterministically and dispatched directly. Faster, more reliable, and zero token cost.

### LLM-drafted SMS replies (showcase feature)

If `paired.conf[llm_trigger]` is set (default `"Hi Agent,"`) and the SMS sender is on the whitelist, `paired-respond` invokes your configured LLM (Gemini, OpenAI, local — whatever OpenClaw is set up with) to draft a reply, then posts a richer Telegram alert containing:

- The original sender + question
- The drafted reply
- A tap-to-copy `/sms` command pre-filled with the answer

You decide whether to send the draft. **No automatic SMS reply.** Empty whitelist disables the feature regardless of the trigger phrase. Logs at `~/.paired/sms-respond.log`.

### Contacts pull — PBAP

```bash
~/bin/bt-contacts AA:BB:CC:DD:EE:FF --max 10
~/bin/bt-contacts AA:BB:CC:DD:EE:FF --pull          # full phonebook → ~/Downloads/bluetooth/<mac>.vcf
~/bin/bt-contacts AA:BB:CC:DD:EE:FF --search "alice"
```

### Media control — AVRCP with ADB fallback

```bash
~/bin/paired-media status --json
~/bin/paired-media play | pause | next | prev | stop
~/bin/paired-media volume 50
```

`paired-media` auto-picks the connected phone, tries BT/AVRCP first, falls back to ADB media-controller if AVRCP isn't responding.

### File transfer — OBEX

```bash
~/bin/bt-send /path/to/file.pdf AA:BB:CC:DD:EE:FF      # push to phone
~/bin/bt-receive                                       # listen for incoming pushes
```

Vendor-dependent feature: OBEX-FTP browse (`bt-browse`) works on some phones, not on Samsung — push-only is the reliable path.

### Network tethering — PAN

```bash
~/bin/bt-pan up AA:BB:CC:DD:EE:FF      # connect as NAP client (turn on BT-tethering on phone first)
~/bin/bt-pan down
~/bin/bt-pan status
```

## Troubleshooting

### `bt-test` is the first stop

```bash
~/bin/bt-test
```

10 checks: adapter present, adapter up, phone paired, phone trusted, phone connected, ofono modem detected, MAP profile available, AVRCP responding, OBEX session opens, ADB device authorised. Each check is one line of output with ✅ / ⚠ / ❌.

### Common failures

| Symptom | Likely cause | Fix |
|---|---|---|
| `bt-list --paired` shows nothing | Adapter not powered | `bluetoothctl power on` (or just `bt-recover` for USB-reset) |
| Pairing fails with "no agent" | `bt-agent.service` not running | `systemctl --user start bt-agent.service` |
| `paired-sms-send` returns `error=keyguard_locked` | Phone is locked, auto-unlock disabled | Unlock phone manually, or set `auto_unlock = true` in config |
| Call connects but recipient hears silence | Samsung audio-focus block | Expected — see [architecture doc](docs/ARCHITECTURE.md#samsung-audio-focus). SMS fail-soft delivers the message |
| MAP push not arriving | MNS daemon not running | `systemctl --user status paired-sms-watch.service` |
| `paired-media` returns "no media sessions" | Phone has nothing playing | This is correct behaviour |
| ADB commands fail with "unauthorised" | One-time host approval not done on phone | Run `bt-adb-setup` and accept the prompt on the phone |

### When in doubt

```bash
journalctl --user -u paired-sms-watch.service --since '10 min ago'
journalctl --user -u paired-call-watch.service --since '10 min ago'
tail -50 ~/.paired/sms-hook.log
tail -50 ~/.paired/call-handler.log
```

## Architecture & known limits

The skill ships with three deep-dive companion docs that document the hardware/firmware constraints we discovered the hard way:

- [**docs/ARCHITECTURE.md**](docs/ARCHITECTURE.md) — the full *why* — ofono+PipeWire SCO conflict, Samsung audio-focus block, MAP-send block, the trade-offs each architectural choice makes
- [**docs/HARDWARE-COMPATIBILITY.md**](docs/HARDWARE-COMPATIBILITY.md) — full matrix of phones × adapters tested
- [**docs/PAIRING-GUIDE.md**](docs/PAIRING-GUIDE.md) — step-by-step pairing including the awkward bits (passkey vs. PIN, trust vs. connect, what to do when the phone says "Connection failed")

## Roadmap

Things on the wishlist (none of these block v1 — file an issue if you want any of them prioritised):

- **HFP-HF AT command client** — bypass ofono+PipeWire entirely, open RFCOMM directly to the phone's HFP-AG, implement AT command set + codec negotiation. Would unblock two-way SCO audio.
- **Pixel + AOSP support testing** — the audio-focus block is Samsung-specific; Pixel devices likely allow in-call TTS. Need a tester.
- **Multi-phone support** — current design assumes one paired phone; the config schema is single-MAC. Refactor to a list of phone profiles.
- **Encrypted SMS log** — currently `sms-events.jsonl` is plaintext mode 0600. Add optional GPG-symmetric encryption.
- **WhatsApp / Signal bridges** — tempting but probably out of scope; the skill is deliberately Bluetooth + ADB only. Better as separate skills that interoperate.

## Contributing

Contributions welcome — bug reports, hardware compatibility reports, feature requests, code, docs.

Before opening a PR, please run the contribution check:

```bash
# Compile-check all Python
python3 -m py_compile skill/bin/*.py
for f in skill/wrappers/*; do head -1 "$f" | grep -q python && python3 -m py_compile "$f"; done

# PII spot-check (the maintainer also runs an automated PII scanner before merging)
grep -rE 'C4:93|07917|/home/[a-z]+/' . | grep -v '\.git/'    # should be empty
```

The PR template includes a personal-data check — please confirm before submission. Real phone numbers in examples should always be Ofcom drama-reserved (`07911123456` for UK, `+14155552671` for US E.164 example range). Real Bluetooth MACs in examples should always be `AA:BB:CC:DD:EE:FF`.

## License

[MIT](LICENSE).

## Credits

Built on top of:

- [BlueZ](http://www.bluez.org/) — the Linux Bluetooth stack
- [ofono](https://01.org/ofono) — open-source mobile telephony framework
- [Android Debug Bridge](https://developer.android.com/tools/adb) — for the parts where Samsung firmware says no to Bluetooth
- [OpenClaw](https://openclaw.ai) — the agent runtime this is a skill for

And inspired by every Twilio-bridge skill that made me ask "...but my phone is *right there*."
