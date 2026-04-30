---
name: paired
description: Bridge an OpenClaw agent to the user's own phone via Bluetooth and ADB-over-USB. Provides SMS receive (MAP/MNS), SMS send (ADB autosend), outgoing calls (HFP), incoming-call alerts, contacts pull (PBAP), media control (AVRCP), file transfer (OBEX), and PAN tethering — all driving the user's actual paired phone. Zero recurring cost, no Twilio/Telnyx/Vapi, no rented numbers. Triggers on phrases like "send SMS", "text someone", "call my phone", "make a call", "what's on my phone", "my contacts", "phone contacts", "play music", "pause", "next track", "send file to phone", "tether", "paired devices", "is my phone connected", "Bluetooth", "BT", "/sms", "/phone", "ofono", "AVRCP", "MAP". Configuration lives in ~/.config/paired/paired.conf (phone MAC, adapter, trusted numbers list). Always read the config before acting; never hardcode phone identifiers.
---

## Execution context

You are running on a Linux host with BlueZ + ofono installed and a phone paired over Bluetooth. The 38 underlying tools live at `~/bin/bt-*` (low-level BlueZ/ofono/ADB primitives) and `~/bin/paired-*` (high-level wrappers exposing JSON-clean interfaces designed for agents to call).

Run commands directly via bash. Do not answer from documentation — execute the tools and report what they actually returned.

**Phone identity comes from `~/.config/paired/paired.conf`**, key `phone_bt_mac`. If a command needs the phone's MAC, read it from the config rather than asking the user. If the config is missing, tell the user to copy `paired.conf.example` and fill in the MAC.

## Most-used commands

### Stack health and discovery

```bash
~/bin/bt-test                              # 10-check stack health (one-shot diagnostic)
~/bin/bt-adapters                          # list HCI adapters
~/bin/bt-list --paired                     # paired devices with CONN/PAIR/TRUST status
~/bin/bt-list --connected                  # only currently-connected
~/bin/bt-list --scan 10                    # 10-second scan for nearby
~/bin/bt-info <MAC>                        # full device detail (UUIDs, RSSI, profiles)
~/bin/bt-recover                           # USB-reset adapter if hung
```

### Pairing and connection

```bash
~/bin/bt-pair <MAC>                        # initiate pairing (passkey via bt-agent)
~/bin/bt-pair <MAC> --connect              # pair + trust + connect in one step
~/bin/bt-connect <MAC>                     # connect to an already-paired device
~/bin/bt-disconnect <MAC>
~/bin/bt-trust <MAC> | ~/bin/bt-untrust <MAC>
~/bin/bt-forget <MAC>                      # remove pairing entirely
```

### Phone — SMS

Receive (read-only via Bluetooth, fully working on most phones):

```bash
~/bin/paired-sms-watch --status            # is the MNS push daemon running?
~/bin/paired-sms-watch --last 10           # last 10 SMS the daemon caught
~/bin/bt-sms-list --map <MAC> --max 10     # explicit MAP read of recent
~/bin/bt-adb-sms-list --limit 10           # ADB read of inbox (works while phone is locked)
~/bin/bt-adb-sms-list --sent --limit 10    # sent folder
```

Send (via ADB-over-USB autosend — Bluetooth MAP send is blocked on most Samsung firmware):

```bash
~/bin/paired-sms-send <NUMBER> "<text>" --json
# Pass --auto-unlock to dismiss the lock screen using the PIN at
# ~/.config/paired/pin (mode 0600 enforced). Pass --relock to re-lock after.
# Without --auto-unlock, the tool returns error=keyguard_locked when phone is locked.
```

Telegram command shortcut: when the user types `/sms NUMBER text` in Telegram, run `~/bin/paired-sms-send NUMBER "text" --json` and report the JSON result. Quote the entire body as one argument.

### Phone — calls (HFP via ofono)

```bash
~/bin/paired-call status --json            # active calls in structured form
~/bin/paired-call dial <NUMBER>            # initiate outbound
~/bin/paired-call answer                   # accept incoming
~/bin/paired-call hangup                   # end all calls
~/bin/paired-call-and-speak <NUMBER> "<msg>" # dial + speak via Tasker TTS (see limits)
~/bin/bt-modems --full                     # ofono modem state, network registration
~/bin/paired-call-watch --last 10          # last 10 incoming calls caught by daemon
~/bin/paired-call-watch --status           # is the call watcher daemon running?
```

Real-time incoming-call alerts run as a systemd user service (`paired-call-watch.service`) — caught calls go to the user's Telegram via `paired-call-watch-tg-hook` with sender + trust-status info.

### Phone — Telegram command vocabulary (deterministic, bypasses LLM)

`paired-sms-command-hook.service` parses the latest agent session JSONL and dispatches recognised commands without invoking the LLM:

| Telegram command | Action | Trust check | Underlying call |
|---|---|---|---|
| `/sms <num> <body>` | Send SMS via ADB | none | `paired-sms-send` |
| `/phone <num>` | Dial outbound | none | `paired-call dial` |
| `/phone <num> <msg>` | Dial + speak via Tasker TTS, **+ SMS fail-soft** | trusted only | `paired-call-and-speak` then `paired-sms-send` |
| `/phone <num> attach <path>` | Dial + speak file content | trusted only | as above |
| `/phone hangup` (or `/phone end`) | End all active calls | none | `paired-call hangup` |
| `/phone status` | Active call state | none | `paired-call status` |

Trusted list at `~/.config/paired/trusted-numbers.conf` — managed via `~/bin/paired-trusted add | remove | list`. UK number normalization: `+44`, `0044`, `44`, and `07` formats all match the same entry.

**Why SMS fail-soft on `/phone <num> <msg>`:** TTS during calls is blocked on some phone firmware (notably Samsung — see "Known phone-side limits" below). The hook always also fires an SMS with the same content so the recipient is guaranteed to get the message even if they don't hear it. Telegram reply notes "📨 SMS fail-soft: delivered" so the user knows.

### Phone — contacts (PBAP)

```bash
~/bin/bt-contacts <MAC> --max 10           # list 10 contacts
~/bin/bt-contacts <MAC> --pull             # pull entire phonebook to ~/Downloads/bluetooth/<mac>.vcf
~/bin/bt-contacts <MAC> --search "name"    # search by name
```

### Phone — media (AVRCP via BT, fallback to ADB)

```bash
~/bin/paired-media status --json           # current track + status (auto BT/ADB transport)
~/bin/paired-media play | pause | next | prev | stop
~/bin/paired-media volume 50               # set BT volume 0-100
~/bin/paired-media current                 # what's playing right now
```

Auto-detects connected phone, picks BT/AVRCP first then falls back to ADB media controller.

### File transfer (OBEX)

```bash
~/bin/bt-send <FILE> <MAC>                 # push file to phone
~/bin/bt-receive                           # listen for incoming pushes (saves to ~/Downloads/bluetooth/)
~/bin/bt-browse <MAC>                      # OBEX-FTP browse (vendor-dependent)
```

### Network (PAN)

```bash
~/bin/bt-pan up <MAC>                      # connect as NAP client (phone-side BT-tethering must be ON)
~/bin/bt-pan down                          # disconnect
~/bin/bt-pan status                        # show bnep0 state
```

### GATT / BLE

```bash
~/bin/bt-gatt-tree <MAC>                   # enumerate services + characteristics
~/bin/bt-gatt-read <MAC> <UUID>            # read a characteristic
~/bin/bt-gatt-write <MAC> <UUID> <HEX>     # write a characteristic
```

### Audio

```bash
~/bin/bt-audio <MAC> --info                # available profiles
~/bin/bt-volume <MAC>                      # current volume
~/bin/bt-play <FILE> <MAC>                 # play file through BT speaker
```

## LLM-drafted SMS reply (showcase feature, opt-in)

When an SMS arrives whose body starts with the phrase set in `paired.conf[llm_trigger]` (default: `"Hi Agent,"`) **and** the sender is on the `paired.conf[llm_trigger_whitelist]`, `paired-respond` will:

1. Strip the trigger prefix
2. Call the configured LLM (Gemini / OpenAI / local) with a tight system prompt
3. Post a richer Telegram alert containing sender, original question, drafted reply, and a tap-to-copy `/sms` command

The user decides whether to send the draft by tapping the `/sms` line. **No automatic SMS reply.** Empty whitelist disables the feature. Logs at `~/.paired/sms-respond.log`.

## Common phrasings → tool mapping

- "Stack health?" → `~/bin/bt-test`
- "What's paired?" / "What devices?" → `~/bin/bt-list --paired`
- "Is my phone connected?" → `~/bin/bt-list --connected | grep -i <phone-label>`
- "Pair with X" → `~/bin/bt-pair X --connect`
- "Network signal?" → `~/bin/bt-modems --full`
- "Any new SMS?" / "Watch SMS" → `~/bin/paired-sms-watch --last 5`
- "Is SMS watcher running?" → `~/bin/paired-sms-watch --status`
- `/sms NUMBER text` → `~/bin/paired-sms-send NUMBER "text" --json`
- "Reply to that SMS with X" → user provides text; you call `paired-sms-send LAST_SENDER "X" --json`. Get LAST_SENDER from the most recent `~/.paired/sms-events.jsonl` entry.
- "Call NUMBER" → `~/bin/paired-call dial NUMBER --json`
- "Hang up" → `~/bin/paired-call hangup --json`
- "Pause music" / "play music" / "next song" → `~/bin/paired-media pause/play/next`
- "What's playing?" → `~/bin/paired-media current`

## Known phone-side limits (clean errors, not bugs)

These are **phone-firmware constraints, not skill bugs**. The tools return clean errors and the docs explain workarounds.

### Samsung firmware (Note 8/9/10/20, S-series tested through OneUI 12)

- **SMS-send via Bluetooth (HFP / MAP) is blocked.** Samsung firmware does not implement `MAP UpdateInbox` and ofono SMS-send returns access-denied. Workaround: use `paired-sms-send` (ADB-over-USB autosend) — fully working.
- **In-call TTS is blocked at the audio policy level.** Samsung Telecom holds `AUDIOFOCUS_GAIN_TRANSIENT_EXCLUSIVE | AUDIOFOCUS_FLAG_LOCK` for the entire ring+call lifecycle. No third-party app (Tasker included) can inject audio into the call audio path. The `paired-call-and-speak` tool runs but the recipient hears silence — **SMS fail-soft compensates** (the message body is also sent as SMS, recipient guaranteed to receive). On non-Samsung devices (Pixel/AOSP, LineageOS, rooted) this is expected to work normally.
- **OBEX-FTP browse not advertised.** Use `bt-send` to push files instead.

### ofono + PipeWire (Debian 13, Ubuntu 24.04)

- **Two-way SCO audio in calls is blocked.** ofono 2.16 + PipeWire 1.4.x + libspa-bluetooth 1.4.x do not cooperate for HFP audio routing on current Debian. Outgoing calls work — the audio just routes through the phone earpiece, not the host's speaker/mic. Tested on both BCM43142 BT 4.0 and RTL8761B BT 5.1 adapters. `paired-sco-agent` is shipped as experimental — see `docs/ARCHITECTURE.md`.
- **A2DP source profile (phone music → host speaker)** is blocked by the same conflict. Receive (host as sink) works; source does not.

### General

- The "Hi Agent," LLM trigger is **opt-in** via `paired.conf` and bound to a **whitelist**. Default config has the whitelist empty, which keeps the feature off until the user explicitly trusts a number.
- Auto-unlock is **opt-in only**. Storing a phone PIN on the host is a security trade — see `paired.conf.example` for the warning.

## Architecture notes

- ofono owns HFP. PipeWire bluez monitor loaded but A2DP-source profile blocked by ofono/PipeWire HFP backend conflict — known trade-off, documented in `docs/ARCHITECTURE.md`.
- `bt-agent.service` runs as a system service to handle pairing PIN/passkey requests.
- The `paired-*` wrappers are the agent-facing interface; the underlying `bt-*` tools are CLI primitives that wrap BlueZ D-Bus and ofono D-Bus directly. Wrappers add JSON output, trust gating, fail-soft behaviour, and Telegram integration.

## Hardware compatibility

See `docs/HARDWARE-COMPATIBILITY.md` for the full matrix. Tested combinations:

| Phone | Android | What works | What's blocked |
|---|---|---|---|
| Samsung Note 9 | 10 / OneUI 12 | Pairing, contacts, SMS receive, outgoing calls, media, file push, PAN, ADB SMS send | In-call TTS, two-way SCO, MAP send, A2DP source |

| Adapter | Type | Status |
|---|---|---|
| BCM43142A0 | Internal BT 4.0 | All features tested working |
| RTL8761B | USB BT 5.1 | All features tested working |

## Setup checklist (for first-time users)

1. **Pair your phone:**
   ```bash
   ~/bin/bt-list --scan 10                # find your phone in the scan output
   ~/bin/bt-pair <MAC> --connect          # pair, trust, connect
   ```

2. **Write your config:**
   ```bash
   cp config-templates/paired.conf.example ~/.config/paired/paired.conf
   $EDITOR ~/.config/paired/paired.conf   # set phone_bt_mac, adapter, etc.
   ```

3. **Set up the trusted-numbers list (optional, recommended):**
   ```bash
   cp config-templates/trusted-numbers.conf.example ~/.config/paired/trusted-numbers.conf
   ~/bin/paired-trusted add 07911123456 "main mobile"
   ~/bin/paired-trusted list
   ```

4. **Enable the systemd user services you want:**
   ```bash
   systemctl --user enable --now paired-sms-watch.service       # real-time SMS push
   systemctl --user enable --now paired-call-watch.service      # incoming call alerts
   systemctl --user enable --now paired-sms-command-hook.service # /sms /phone Telegram commands
   ```

5. **Verify:**
   ```bash
   ~/bin/bt-test                          # 10-check stack health
   ```

If everything's green, the agent is ready to use the skill.
