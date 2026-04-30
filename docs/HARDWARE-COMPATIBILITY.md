# Hardware compatibility

> What's been tested, what works, what's blocked. **Community contributions welcome** — every confirmed phone × adapter combination helps the next person. [Open a hardware compatibility report](https://github.com/nj070574-gif/openclaw-paired-skill/issues/new?template=hardware_report.md).

## Phones tested

### Samsung Note 9 — Android 10 / OneUI 12

The reference device for this skill. Most architectural notes in [docs/ARCHITECTURE.md](ARCHITECTURE.md) come from extensive testing on this phone.

| Feature | Tool | Status | Notes |
|---|---|---|---|
| Pairing | `bt-pair` | ✅ working | Passkey via `bt-agent` |
| Connection lifecycle | `bt-connect` / `bt-disconnect` / `bt-recover` | ✅ working | |
| Contacts pull (PBAP) | `bt-contacts --pull` | ✅ working | Full phonebook to `.vcf` |
| SMS receive (MAP read) | `bt-sms-list --map` | ✅ working | Read-only |
| SMS receive (MNS push) | `paired-sms-watch` | ✅ working | Real-time push, dedup needed (events can double-fire) |
| SMS send via Bluetooth | `bt-sms-send` | ❌ blocked | Samsung firmware doesn't implement MAP UpdateInbox |
| SMS send via ADB | `paired-sms-send` | ✅ working | UI automation, with optional auto-unlock |
| Outgoing call (HFP) | `paired-call dial` | ✅ working | Audio via phone earpiece |
| Incoming call alert | `paired-call-watch` | ✅ working | ofono D-Bus signals |
| In-call TTS via Tasker | `paired-call-and-speak` | ⚠ silent | Audio-focus block — SMS fail-soft compensates |
| Two-way SCO audio | (manual) | ❌ blocked | ofono+PipeWire conflict, see ARCHITECTURE.md |
| A2DP source (phone → host) | (manual) | ❌ blocked | Same conflict |
| A2DP sink (host → phone) | `bt-play` | ✅ working | |
| Media control (AVRCP) | `paired-media play/pause/next` | ✅ working | |
| Media control (ADB fallback) | `paired-media` (auto-fallback) | ✅ working | |
| File transfer push (OBEX OPP) | `bt-send` | ✅ working | |
| File transfer receive (OBEX) | `bt-receive` | ✅ working | |
| OBEX-FTP browse | `bt-browse` | ❌ not advertised | Samsung doesn't advertise OBEX-FTP |
| PAN tethering | `bt-pan up` | ✅ working | Phone-side BT tethering must be enabled |
| BLE service tree | `bt-gatt-tree` | ✅ working | |
| Battery polling | `bt-battery` | ✅ working | |

**Total**: 18 features confirmed working, 4 blocked at firmware level (with documented workarounds where possible).

### Other Samsung devices (untested but expected similar)

The audio-focus block and MAP-send block are believed to apply to **all Samsung devices running OneUI 8+**. Galaxy S, Note, A-series, Tab — same firmware lineage. If you have one of these and want to confirm, a hardware report would be hugely useful.

### Pixel + AOSP / LineageOS / rooted Android (UNTESTED)

The architecture analysis suggests these should work better than Samsung:

- **In-call TTS** — likely works (no Samsung audio-focus lock)
- **MAP-send** — likely works (AOSP implements it correctly)
- **OBEX-FTP browse** — likely works
- Everything else — should match Samsung capability

If you have a Pixel or LineageOS phone, please [open a hardware report](https://github.com/nj070574-gif/openclaw-paired-skill/issues/new?template=hardware_report.md) — confirming any of these would unlock features for the whole community.

### iOS (NOT supported, never will be)

iOS doesn't expose:

- Programmatic SMS send via any Bluetooth profile
- ADB equivalent (libimobiledevice exists but is heavily restricted)
- HFP voice-call origination from a paired host
- AVRCP write (only read)

Bluetooth on iOS is intentionally locked down to the level needed for AirPods + CarPlay. The skill cannot work with iPhones in any meaningful capacity. This is by Apple design, not a bug.

## Bluetooth adapters tested

### BCM43142A0 (internal, USB ID `0a5c:216f`)

- **BT version**: 4.0
- **Vendor**: Broadcom
- **Common in**: HP EliteBook / Pavilion 2014–2018, ThinkPad T440s/X240, Dell Latitude E7440
- **Status**: ✅ all features working
- **Quirks**: occasionally needs a USB reset (`bt-recover`) after long suspend cycles. The 10-check `bt-test` will catch this — adapter shows MAC `00:00:00:00:00:00` when in this state.

### RTL8761B (USB dongle, USB ID `0bda:8771`)

- **BT version**: 5.1
- **Vendor**: Realtek
- **Common in**: cheap aftermarket USB dongles (£8–15 on Amazon)
- **Status**: ✅ all features working — drop-in via `--adapter hci1`
- **Quirks**: the firmware blob `rtl_bt/rtl8761bu_fw.bin` must be present in `/lib/firmware/` (Debian package: `firmware-realtek`). Without it the adapter loads but fails to power on.

### Adapters not yet tested but expected to work

Anything BlueZ supports — full list at [linux-bluetooth.bluez.com](http://www.bluez.org/about/). The skill is BlueZ-D-Bus-driven, not chipset-specific. If your `lsusb` shows the adapter and `bluetoothctl power on` succeeds, it should work.

Adapters with reported issues elsewhere (BlueZ ML / Arch wiki):

- **CSR8510 generic dongles** — the cheap "CSR 4.0" clones often have firmware that lies about supported features. May work for basic pairing only.
- **Intel AX211 / AX210** — known kernel-driver instabilities on some kernels, unrelated to this skill.

## Linux distros tested

| Distro | Kernel | BlueZ | ofono | PipeWire | Status |
|---|---|---|---|---|---|
| Debian 13 | 6.11 | 5.79 | 2.16 | 1.4.2 | ✅ Reference platform |

Distros expected to work (same component versions ± minor):

- **Ubuntu 24.04 LTS** (BlueZ 5.72, ofono 2.16) — should work, untested
- **Fedora 40+** (BlueZ 5.76, ofono 2.16) — should work, untested
- **Arch Linux rolling** — should work, ofono package needs explicit install

Distros expected NOT to work:

- **Debian 11/12** — BlueZ 5.55/5.62 lacks some MAP-MNS fixes, ofono is older. Probably workable for receive features, MNS push may be flaky.
- **Ubuntu 22.04 LTS** — same caveats as Debian 12.
- **Anything pre-PipeWire** (Ubuntu 20.04 with PulseAudio) — the audio routing assumptions in `bt_audio.py` won't hold.

## Reporting your setup

If you got it working — or if you tried and it didn't — please [open a hardware compatibility report](https://github.com/nj070574-gif/openclaw-paired-skill/issues/new?template=hardware_report.md). The template captures:

- Phone vendor + model + Android version + skin
- Bluetooth adapter chip + USB ID
- Linux distro + BlueZ + ofono + PipeWire versions
- Per-feature checklist (which of the 18 features worked / didn't)
- Any non-default config or workarounds you needed

The matrix above only grows with community contributions.
