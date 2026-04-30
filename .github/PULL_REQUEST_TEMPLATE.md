<!--
Thanks for contributing to Paired! A few quick checks before submission.
-->

## Summary

<!-- One-paragraph what + why. Link any related issues. -->

Closes #

## Type of change

- [ ] Bug fix (non-breaking)
- [ ] New feature (non-breaking)
- [ ] Breaking change (existing behaviour changes)
- [ ] Hardware support (new phone, adapter, or kernel combination tested)
- [ ] Documentation only

## Personal data check

The skill goes to lengths to keep the codebase free of PII. **Before submitting, please confirm:**

- [ ] No real phone numbers in code or docs (use `07911123456` for UK examples, E.164 for international)
- [ ] No real Bluetooth MACs (use `AA:BB:CC:DD:EE:FF`)
- [ ] No real names — first or last
- [ ] No `/home/<user>/` paths in code (use `Path.home()` or `${HOME}` in shell)
- [ ] No API keys, bot tokens, or chat IDs hardcoded — read from `openclaw.json[env]` instead
- [ ] No carrier names or hostnames specific to your network

## Tested on

- **Phone:**
- **Bluetooth adapter:**
- **Linux distro + kernel:**
- **OpenClaw version:**

## Verification

- [ ] All Python files compile (`python3 -m py_compile skill/bin/*.py skill/wrappers/*`)
- [ ] No new shell-script lint warnings (`shellcheck` if applicable)
- [ ] CHANGELOG.md updated under `[Unreleased]`
- [ ] Documentation updated if behaviour changed
