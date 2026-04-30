#!/usr/bin/env python3
"""paired-call-and-speak - Dial a number, then speak a message via Tasker.

Architecture (v2.1 - intent-broadcast path + opt-in SMS fallback):
  1. Dial <number> via paired-call dial
  2. Wait for the call to ring/connect (configurable delay)
  3. Fire ADB intent broadcast: net.dinglisch.android.tasker.PAIRED_TRIGGER
     with par1 = the message to speak.
  4. Tasker on the phone catches the Intent Received event and runs the
     "Agent Speak Now" task, which speaks par1 via Stream 5 (Voice Call)
     so the cellular caller hears it.
  5. (OPT-IN) If --with-sms-fallback is passed AND the speak step failed,
     also send the same message body as an SMS so the recipient still gets
     it. This is OFF by default — v1.0.2 made the fallback explicit per
     OpenClaw scanner finding #5 (Cascading Failures).

Validated working 2026-04-28 incl. cold state with screen off >30s.

Usage:
  paired-call-and-speak <recipient_number> <message_text>
                        [--no-call] [--json] [--with-sms-fallback]
"""
from __future__ import annotations
import argparse
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
_HOME = str(Path.home())

LOG_DIR = Path.home() / "bt-skill-expansion"
LOG_FILE = LOG_DIR / "call-and-speak.log"

CALL_BIN = f"{_HOME}/bin/paired-call"
ADB_BIN = "/usr/bin/adb"
PAIRED_CONF = Path.home() / ".config" / "paired" / "paired.conf"


def _load_adb_device() -> str | None:
    """Read adb_device from ~/.config/paired/paired.conf, or fall back to env
    or the first attached device. Returns None if nothing is configured.

    Removed in v1.0.2: the previous hardcoded ADB_DEVICE constant was the
    skill author's own phone hardware serial. That was wrong — it should be
    user-supplied. Set 'adb_device' in paired.conf, or PAIRED_ADB_DEVICE in
    the environment, or leave both unset to use the first attached device.
    """
    # 1. env var
    env_val = os.environ.get("PAIRED_ADB_DEVICE")
    if env_val:
        return env_val
    # 2. paired.conf
    if PAIRED_CONF.exists():
        try:
            for line in PAIRED_CONF.read_text().splitlines():
                line = line.split("#", 1)[0].strip()
                if not line or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                if k.strip() == "adb_device":
                    val = v.strip().strip('"').strip("'")
                    if val:
                        return val
        except OSError:
            pass
    # 3. nothing configured — caller will pass no -s flag and adb will pick
    #    the only attached device (or fail if multiple)
    return None

TASKER_INTENT = "net.dinglisch.android.tasker.PAIRED_TRIGGER"

RING_WAIT_SECONDS = 5

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [paired-call-and-speak] %(levelname)s: %(message)s",
)
log = logging.getLogger()


def run_call_dial(number, timeout=25):
    try:
        proc = subprocess.run(
            [CALL_BIN, "dial", number, "--json"],
            capture_output=True, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return False, "dial timeout"
    except OSError as e:
        return False, "dial exec failed: " + str(e)

    if proc.returncode != 0:
        return False, "dial rc=" + str(proc.returncode) + " stderr=" + (proc.stderr or "")[:120]
    try:
        result = json.loads(proc.stdout) if proc.stdout.strip() else {"ok": False}
        if result.get("ok"):
            return True, "dial ok: " + str(result.get("action", "dial"))
        return False, "dial returned not-ok: " + str(result.get("error", "unknown"))
    except json.JSONDecodeError:
        return True, "dial completed (no json out)"


def fire_speak_intent(message, par2=""):
    safe_msg = message.replace("'", "'\\''")
    safe_par2 = par2.replace("'", "'\\''")
    adb_device = _load_adb_device()
    cmd = [ADB_BIN]
    if adb_device:
        cmd += ["-s", adb_device]
    cmd += [
        "shell",
        "am broadcast -a " + TASKER_INTENT +
        " --es par1 '" + safe_msg + "'" +
        " --es par2 '" + safe_par2 + "'",
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    except subprocess.TimeoutExpired:
        return False, "intent broadcast timeout"
    except OSError as e:
        return False, "adb exec failed: " + str(e)

    out = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode != 0:
        return False, "adb rc=" + str(proc.returncode) + " out=" + out[:200]
    if "Broadcast completed: result=0" in out:
        return True, "broadcast delivered"
    return True, "broadcast sent (rc=0, out=" + out[:120] + ")"


def main():
    p = argparse.ArgumentParser(
        description="Dial a number and speak a message to the caller via Tasker."
    )
    p.add_argument("number", help="Number to dial")
    p.add_argument("message", help="Text Agent should speak to the caller")
    p.add_argument("--no-call", action="store_true",
                   help="Skip the dial step")
    p.add_argument("--json", action="store_true",
                   help="Emit JSON status")
    p.add_argument("--with-sms-fallback", action="store_true",
                   help="Opt-in: if TTS fails, send the same body as an SMS "
                        "(best-effort, not a guarantee). Off by default.")
    p.add_argument("--ring-wait", type=int, default=RING_WAIT_SECONDS,
                   help="Seconds between dial and speak trigger")
    p.add_argument("--hangup-after", type=int, default=0,
                   help="Seconds after speak to hangup (0 = caller-controls)")
    args = p.parse_args()

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    fh = logging.FileHandler(LOG_FILE)
    fh.setFormatter(logging.Formatter(
        "%(asctime)s [paired-call-and-speak] %(levelname)s: %(message)s"))
    log.addHandler(fh)

    started = datetime.now(timezone.utc).isoformat()
    log.info("Triggered: number=" + args.number + " no_call=" + str(args.no_call))

    record = {
        "started_at": started,
        "number": args.number,
        "message": args.message,
        "no_call": args.no_call,
        "dial": None,
        "speak": None,
        "ok": False,
    }

    if not args.no_call:
        dial_ok, dial_info = run_call_dial(args.number)
        record["dial"] = {"ok": dial_ok, "info": dial_info}
        log.info("Dial: ok=" + str(dial_ok) + " info=" + dial_info)
        if not dial_ok:
            log.error("Dial failed - aborting before speak trigger")
            print(json.dumps(record))
            return 1
        log.info("Waiting " + str(args.ring_wait) + "s for ring/connect...")
        time.sleep(args.ring_wait)
    else:
        record["dial"] = {"ok": True, "info": "skipped"}
        log.info("--no-call set; skipping dial step")

    par2 = "hangup" if args.hangup_after > 0 else ""
    speak_ok, speak_info = fire_speak_intent(args.message, par2)
    record["speak"] = {"ok": speak_ok, "info": speak_info}
    log.info("Speak trigger: ok=" + str(speak_ok) + " info=" + speak_info)

    record["ok"] = (record["dial"] or {}).get("ok", False) and speak_ok

    if args.hangup_after > 0 and not args.no_call:
        log.info("Waiting " + str(args.hangup_after) + "s before hangup...")
        time.sleep(args.hangup_after)
        try:
            subprocess.run([CALL_BIN, "hangup", "--json"],
                           capture_output=True, timeout=10)
            log.info("Auto-hangup fired")
            record["hangup"] = "ok"
        except Exception as e:
            log.warning("Auto-hangup failed: " + str(e))
            record["hangup"] = "failed: " + str(e)

    if args.json:
        print(json.dumps(record))
    else:
        if record["ok"]:
            print("OK - dial=" + str(record["dial"]["ok"]) + " speak=" + str(record["speak"]["ok"]))
        else:
            print("FAIL - dial=" + str(record.get("dial")) + " speak=" + str(record.get("speak")))

    # SMS fallback — ONLY if user opted in AND speak failed.
    if args.with_sms_fallback and not speak_ok:
        log.info("Speak failed and --with-sms-fallback set; trying SMS")
        sms_bin = f"{_HOME}/bin/paired-sms-send"
        try:
            sms_body = args.message[:300] + ("..." if len(args.message) > 300 else "")
            sproc = subprocess.run(
                [sms_bin, "--auto-unlock", "--relock", args.number, sms_body],
                capture_output=True, text=True, timeout=90,
            )
            record["sms_fallback"] = {
                "attempted": True,
                "ok": sproc.returncode == 0,
                "info": (sproc.stdout or sproc.stderr or "")[:200],
            }
            log.info("SMS fallback rc=" + str(sproc.returncode))
        except Exception as e:
            record["sms_fallback"] = {"attempted": True, "ok": False,
                                      "info": "exec failed: " + str(e)}
    elif not args.with_sms_fallback and not speak_ok:
        log.info("Speak failed; --with-sms-fallback NOT set; not sending SMS")
        record["sms_fallback"] = {"attempted": False,
                                  "reason": "opt-in flag not provided"}

    return 0 if record["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
