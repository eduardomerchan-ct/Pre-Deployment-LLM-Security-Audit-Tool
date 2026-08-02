# [Low] Duplicate-id error only names the file where the duplicate was found, not the original

**File:** `attacks/schema.py`
**Location:** `load_attack_library()`, the `seen_ids` duplicate check (around lines 121–158)
**Severity:** Low
**Type:** Readability / developer experience
**Found by:** code-reviewer agent, 2026-07-28

## Problem

Duplicate ids are tracked with a bare `set()`:

```python
seen_ids: set[str] = set()
...
if case.id in seen_ids:
    raise ValueError(f"{yaml_path.name}: duplicate attack case id '{case.id}' found in library")
```

The error message names only the file currently being loaded (where the *second* occurrence was found), not the file that defined the id first. With 6 category files and 15–20+ cases, tracking down the other file with the same id means grepping the whole `attacks/library/` directory by hand.

## Why it matters

This is a "fail loudly" check that's correct today but not maximally useful — the whole point of failing loudly is to make the fix fast. Right now the error tells you *that* there's a collision but not *where* the other half of it lives.

## Suggested fix

Track `id -> filename` instead of a bare set of ids:

```python
seen_ids: dict[str, str] = {}
...
if case.id in seen_ids:
    raise ValueError(
        f"{yaml_path.name}: duplicate attack case id '{case.id}' "
        f"(first defined in {seen_ids[case.id]})"
    )
seen_ids[case.id] = yaml_path.name
```

## Acceptance criteria

- [ ] When the same `id` appears in two different `attacks/library/*.yaml` files, the raised error names both files.
- [ ] When the same `id` appears twice within a single file, the error still fires correctly (no regression).
