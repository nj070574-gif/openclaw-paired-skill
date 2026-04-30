---
name: Bug report
about: Something didn't work as expected
title: "[bug] "
labels: bug
assignees: ''
---

## What happened

<!-- One-paragraph summary of the unexpected behaviour. -->

## What you expected to happen

<!-- What should have happened instead. -->

## Steps to reproduce

1.
2.
3.

## Environment

- **Linux distro and kernel:** <!-- e.g. Debian 13, kernel 6.11 -->
- **BlueZ version:** <!-- output of `bluetoothctl --version` -->
- **ofono version:** <!-- output of `ofonod --version` -->
- **Python version:** <!-- output of `python3 --version` -->
- **OpenClaw version:** <!-- output of `openclaw --version` -->
- **Paired skill version:** <!-- e.g. 1.0.0 -->
- **Phone:** <!-- vendor + model + Android version -->
- **Bluetooth adapter:** <!-- output of `bt-adapters` (one-line summary) -->

## Diagnostic output

Please attach the output of:

```bash
bt-test 2>&1
```

and the relevant log file:

```bash
tail -200 ~/.paired/<the-relevant>.log
# or
journalctl --user -u paired-<service> --since '10 min ago'
```

## Sensitive data

Have you checked the diagnostic output for personal info before pasting? Phone numbers, Bluetooth MACs of identifiable devices, full names in contacts. Redact before submitting.
