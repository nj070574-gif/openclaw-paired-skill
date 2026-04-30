---
name: Hardware compatibility report
about: Tell us what works (and doesn't) on your phone + adapter
title: "[hw] <vendor> <model> + <adapter>"
labels: hardware-compat
assignees: ''
---

## Setup

- **Phone vendor + model:**
- **Android version + skin:** <!-- e.g. Android 14, OneUI 6 -->
- **Carrier (region):** <!-- e.g. UK MNO -->
- **Bluetooth adapter chip + USB ID:** <!-- output of `bt-adapters` -->
- **Linux distro + BlueZ + ofono versions:**

## Compatibility matrix — fill in what you've tested

Mark each ✅ working / ⚠ partial / ❌ blocked / 🟡 untested.

| Feature | Tool used | Status | Notes |
|---|---|---|---|
| Pairing | `bt-pair` | | |
| Connection lifecycle | `bt-connect` / `bt-disconnect` | | |
| Contacts pull (PBAP) | `bt-contacts --pull` | | |
| SMS receive (MAP) | `bt-sms-list --map` | | |
| SMS receive (MNS push) | `paired-sms-watch` | | |
| SMS send via Bluetooth | `bt-sms-send` | | |
| SMS send via ADB | `paired-sms-send` | | |
| Outgoing call (HFP) | `paired-call dial` | | |
| Incoming call alert | `paired-call-watch` | | |
| In-call TTS | `paired-call-and-speak` | | |
| Two-way SCO audio | (manual) | | |
| Media control (AVRCP) | `paired-media play/pause/next` | | |
| File transfer push (OBEX) | `bt-send` | | |
| File transfer receive (OBEX) | `bt-receive` | | |
| PAN tethering | `bt-pan up` | | |
| BLE service tree | `bt-gatt-tree` | | |
| Battery polling | `bt-battery` | | |

## Surprises and workarounds

<!-- Anything that needed a non-default config, an extra package, or a workaround. -->
