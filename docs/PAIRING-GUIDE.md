# Pairing guide

> Step-by-step pairing for first-time users. If you're an experienced BlueZ user and `bt-pair AA:BB:CC:DD:EE:FF --connect` is enough — skip to [Quick reference](#quick-reference) at the bottom.

## Before you start

Check three things:

1. **You have BlueZ running:** `systemctl status bluetooth` should show `active (running)`
2. **An adapter is detected:** `~/bin/bt-adapters` should list at least one HCI device
3. **`bt-agent.service` is running:** `systemctl --user status bt-agent.service`

If any of those is missing, see the [README installation steps](../README.md#installation) first.

## The pairing flow

### Step 1 — Find your phone's MAC

Put your phone in Bluetooth pairing/discoverable mode (settings vary — typically Settings → Connections → Bluetooth, then leave the screen open).

On the host:

```bash
~/bin/bt-list --scan 10
```

This scans for 10 seconds and prints anything visible. Look for your phone's name. Output looks like:

```
[scan]  AA:BB:CC:DD:EE:FF  My Phone           RSSI=-56  ←─── pick this MAC
[scan]  6C:5A:F1:23:AA:BB  some-bt-speaker    RSSI=-72
[scan]  AC:7A:4D:00:FF:11  ble-keyboard       RSSI=-89
```

If you don't see your phone after 10 seconds:

- Make sure the phone's Bluetooth screen is still open (Android stops broadcasting after ~2 minutes)
- Try `bt-list --scan 30` for a longer scan
- Run `~/bin/bt-recover` then re-scan if the adapter seems stuck

### Step 2 — Pair

```bash
~/bin/bt-pair AA:BB:CC:DD:EE:FF --connect
```

The `--connect` flag means "pair, trust, and connect in one step" — what you usually want.

What happens:

1. The host requests pairing
2. **Both devices show a passkey** (typically a 6-digit number like `123456`)
3. **You confirm "Match" on both ends** — phone shows the passkey with a Yes/No prompt; the host's `bt-agent` auto-accepts (it's running on your behalf)
4. The phone marks the host as a paired device
5. The host trusts the phone (so it auto-reconnects in future)
6. Initial connection is established

If everything works, you'll see:

```
✅ paired      AA:BB:CC:DD:EE:FF
✅ trusted     AA:BB:CC:DD:EE:FF
✅ connected   AA:BB:CC:DD:EE:FF
```

### Step 3 — Verify

```bash
~/bin/bt-list --paired
```

Should show your phone with `CONN=yes  PAIR=yes  TRUST=yes`.

```bash
~/bin/bt-info AA:BB:CC:DD:EE:FF
```

Shows full device detail — supported UUIDs, RSSI, profile list. The UUIDs you want to see at minimum:

| UUID | Service | Used for |
|---|---|---|
| `0000111e-...` | HFP-AG | Outgoing calls |
| `0000110a-...` | A2DP-Source | Phone media to host |
| `0000110c-...` | AVRCP-CT | Media control from host |
| `00001112-...` | HSP-AG | Headset profile |
| `00001116-...` | NAP | PAN tethering |
| `00001105-...` | OBEX-OPP | File push |
| `0000112d-...` | SAP | SIM access (rarely working) |
| `0000112f-...` | PBAP-PSE | Phonebook access |
| `00001132-...` | MAP-MAS | SMS read |
| `00001133-...` | MAP-MNS | SMS push notification |

You don't need all of these. If MAP-MNS (`0000113`*3*) is missing, real-time SMS push won't work — but read-on-demand via MAP-MAS (`1132`) will. That's worth knowing before chasing config issues that aren't config issues.

### Step 4 — Run the 10-check

```bash
~/bin/bt-test
```

Output looks like:

```
✅ adapter present
✅ adapter powered
✅ phone paired
✅ phone trusted
✅ phone connected
✅ ofono modem detected
✅ MAP-MAS profile ready
✅ AVRCP responding
✅ OBEX session opens
⚠ ADB device not authorised  ← run `bt-adb-setup`
```

Anything ✅ is good. Anything ⚠ is fixable — usually with a single command. Anything ❌ means re-read the output more carefully — `bt-test` tells you what to do.

### Step 5 — Update your config

Edit `~/.config/paired/paired.conf`:

```
phone_bt_mac = AA:BB:CC:DD:EE:FF    # the MAC from Step 1
phone_label  = My Phone
adapter      = hci0
```

Now the rest of the skill knows which device to talk to.

## Common pairing issues

### "Authentication failed" / "Connection failed"

Most common causes:

1. **You took too long to confirm the passkey on the phone.** Some Androids time out after ~30 seconds. Try again — `bt-pair` is idempotent.
2. **An old pairing exists from a previous attempt.** Run `bt-forget <MAC>` on the host, also forget the host on the phone (Bluetooth settings → host name → forget), then re-pair fresh.
3. **`bt-agent.service` not running.** Without an agent, no one's there to auto-accept the passkey on the host side. `systemctl --user start bt-agent.service`.

### "Already paired but not connecting"

```bash
~/bin/bt-disconnect <MAC>
~/bin/bt-connect <MAC>
```

If that fails, the typical fix is "re-pair from scratch":

```bash
~/bin/bt-forget <MAC>
# also forget host on phone Bluetooth settings
~/bin/bt-pair <MAC> --connect
```

### Phone connects, then immediately disconnects

This is usually one of:

1. **The phone's BT cache is corrupted.** Reboot the phone.
2. **A BlueZ pairing-key mismatch** between host's `/var/lib/bluetooth/<adapter-mac>/<phone-mac>/info` and what the phone has stored. Easy fix: forget on both sides, re-pair.
3. **Adapter is hanging.** `bt-recover` does a USB reset of the adapter (Linux-side only, doesn't touch the phone).

### "PIN code required" instead of passkey display

Older BT 2.x devices use legacy PIN pairing (4-digit). Run:

```bash
~/bin/bt-pair <MAC> --pin
```

This puts `bt-agent` in pin-prompt mode. Default PIN for legacy devices is usually `0000` or `1234`.

### Pairing succeeds but `ofono` doesn't see the modem

```bash
~/bin/bt-modems
```

If empty, ofono didn't pick up the HFP profile.

```bash
~/bin/bt-disconnect <MAC>
sudo systemctl restart ofono
~/bin/bt-connect <MAC>
~/bin/bt-modems     # should now show /hfp/org/bluez/...
```

If still empty: check that the phone advertises HFP-AG (UUID `0000111e-...`) in `bt-info`. If it doesn't, the phone vendor stripped HFP — uncommon but happens on cheap Chinese ROMs.

## Special phone-side setup

### Samsung — keep BT visible

Samsung disables Bluetooth visibility ~2 minutes after you leave the BT settings screen. To re-pair, go back to the settings screen first.

### Samsung — enable Phone audio + Contacts

After first pairing, Samsung asks "Allow access to contacts and call history?" — say Yes. Without this, PBAP and HFP won't work even though pairing succeeded.

### Samsung — turn on Notifications

For MAP-MNS to fire SMS pushes: Settings → Bluetooth → tap the gear icon next to the host name → toggle on **Notification access**. This is a separate per-device permission that Samsung adds on top of standard MAP.

### Pixel + AOSP

Pixel phones grant all profile permissions by default — no extra steps. Pairing is more reliable too, in our experience.

### Phones with Knox / work profiles

Knox-managed devices may block PBAP and MAP at the profile level regardless of user consent. There's no way around this from the host side — talk to your IT admin.

## Quick reference

For the experienced reader, the whole flow is:

```bash
~/bin/bt-list --scan 10                       # find phone MAC
~/bin/bt-pair AA:BB:CC:DD:EE:FF --connect     # pair + trust + connect
~/bin/bt-test                                 # 10-check verify
$EDITOR ~/.config/paired/paired.conf          # set phone_bt_mac, save
systemctl --user enable --now \
  paired-sms-watch.service \
  paired-call-watch.service \
  paired-sms-command-hook.service             # turn on the daemons
```

Done.

## Re-pairing from scratch

If anything has drifted and you want a clean slate:

```bash
# Forget on host
~/bin/bt-forget <MAC>

# Forget on phone (manual: Bluetooth settings → host name → Forget)

# Optionally also reset adapter
~/bin/bt-recover

# Re-pair
~/bin/bt-pair <MAC> --connect
```

This is safe to do repeatedly — none of the skill's data depends on a particular pairing remaining intact. Logs in `~/.paired/` are not affected by re-pairing.
