#!/usr/bin/env python3
"""bt-call — Make a call through a paired phone (HFP via ofono).

Examples:
  bt-call 07911123456                          # use first available modem
  bt-call 07911123456 --modem AA:BB:CC:DD:EE:FF
  bt-call --hangup                             # hang up everything
  bt-call --status                             # show current calls
"""
from __future__ import annotations
import argparse, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import bt_telephony as bt


def _resolve_modem(mac_arg: str | None) -> dict | None:
    modems = bt.list_modems()
    if not modems:
        return None
    if mac_arg:
        return bt.modem_for_mac(mac_arg)
    return modems[0]


def main() -> int:
    ap = argparse.ArgumentParser(description="Make / answer / hang up calls")
    ap.add_argument("number", nargs="?", help="Phone number to dial")
    ap.add_argument("--modem", help="Specific paired phone MAC (default: first modem)")
    ap.add_argument("--answer", action="store_true", help="Answer incoming call")
    ap.add_argument("--hangup", action="store_true", help="Hang up all calls")
    ap.add_argument("--status", action="store_true", help="Show current calls")
    ap.add_argument("--hide-id", action="store_true", help="Hide caller ID")
    args = ap.parse_args()

    modem = _resolve_modem(args.modem)
    if modem is None:
        sys.stderr.write("No ofono modem available. Pair a phone with HFP first:\n")
        sys.stderr.write("  bt-pair <phone-mac> --connect\n")
        return 2

    path = modem["path"]

    if args.status:
        calls = bt.list_calls(path)
        if not calls:
            print(f"{path}: no active calls")
            return 0
        for c in calls:
            print(f"  {c.get('LineIdentification', '?')} state={c.get('State', '?')}")
        return 0

    if args.hangup:
        n = bt.hangup_all(path)
        print(f"hung up {n} call(s)")
        return 0

    if args.answer:
        cp = bt.answer_first(path)
        if cp:
            print(f"answered {cp}")
            return 0
        print("no incoming call to answer")
        return 1

    if not args.number:
        sys.stderr.write("error: number required (or use --hangup / --answer / --status)\n")
        return 2

    print(f"dialing {args.number} via {path}...")
    try:
        cp = bt.dial(path, args.number, hide_caller_id=args.hide_id)
    except Exception as e:
        sys.stderr.write(f"DIAL FAILED: {e}\n")
        return 1
    print(f"call started: {cp}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
