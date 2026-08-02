# [Medium] `read_text()` doesn't pin an explicit encoding

**File:** `attacks/schema.py`
**Location:** `load_attack_library()`, `yaml_path.read_text()` (around line 127)
**Severity:** Medium
**Type:** Bug / portability
**Found by:** code-reviewer agent, 2026-07-28

## Problem

```python
raw_content = yaml.safe_load(yaml_path.read_text())
```

`Path.read_text()` with no `encoding` argument uses `locale.getpreferredencoding(False)` — on Windows that's commonly `cp1252`, not UTF-8. This project runs on Windows (per the dev environment).

## Why it matters

Attack-case `content` strings are exactly the kind of text likely to contain characters outside plain ASCII: curly quotes or em dashes pasted in from another tool, or deliberately multilingual/unicode jailbreak payloads as part of the attack itself. On this machine, `cp1252` decoding either throws `UnicodeDecodeError` on some byte sequences or silently mangles characters that *do* decode, both of which are bad: one blocks loading the whole library over one file, the other quietly corrupts a case's prompt text with no error at all.

This also makes the tool non-portable — the same YAML file could load fine on a Windows machine and differently (or fail) on Linux/Mac CI, since the default encoding is platform-dependent.

## Suggested fix

```python
raw_content = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
```

(Combine with the fix in ticket 001 — both touch the same line.)

## Acceptance criteria

- [ ] `read_text()` in `load_attack_library` passes `encoding="utf-8"` explicitly.
- [ ] A case file containing a non-ASCII character (e.g. a curly quote `’` or an em dash `—` in a `content` field) loads correctly and the string round-trips unchanged.
