# [Medium] `load_attack_library` doesn't catch malformed YAML syntax

**File:** `attacks/schema.py`
**Location:** `load_attack_library()`, the `yaml.safe_load(yaml_path.read_text())` call (around line 127)
**Severity:** Medium
**Type:** Bug / error handling gap
**Found by:** code-reviewer agent, 2026-07-28

## Problem

`load_attack_library` wraps every other failure mode in a clear, file-named error:

- an empty or non-list YAML file raises `ValueError(f"{yaml_path.name}: expected a top-level YAML list...")`
- a case that fails pydantic validation raises `ValueError(f"{yaml_path.name}, case {case_label}: {e}")`
- a duplicate id raises `ValueError(f"{yaml_path.name}: duplicate attack case id...")`

But the line that actually parses the YAML text —

```python
raw_content = yaml.safe_load(yaml_path.read_text())
```

— is not wrapped in a `try/except`. If a hand-written case file has a *syntax* error (bad indentation, an unbalanced quote, a stray tab), PyYAML raises its own exception (typically `yaml.scanner.ScannerError` or `yaml.parser.ParserError`). That exception references an internal buffer name like `"<unicode string>"` plus a line/column position — it never names the actual `.yaml` file that's broken.

## Why it matters

This project's whole `load_attack_library` design philosophy is "fail loudly and name the exact file" so a mistake is fast to find across 15–20+ hand-authored case files. A raw PyYAML traceback breaks that promise for the most common authoring mistake there is: a YAML syntax typo.

## Suggested fix

```python
try:
    raw_content = yaml.safe_load(yaml_path.read_text())
except yaml.YAMLError as e:
    raise ValueError(f"{yaml_path.name}: invalid YAML — {e}") from e
```

## Acceptance criteria

- [ ] A `.yaml` file in `attacks/library/` with a deliberate syntax error (e.g. bad indentation) causes `load_attack_library()` to raise a `ValueError` whose message starts with that file's name.
- [ ] Well-formed files still load exactly as before (no behavior change for the happy path).
