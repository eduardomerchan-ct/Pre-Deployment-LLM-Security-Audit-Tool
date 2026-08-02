# [Low] A nonexistent `library_dir` silently returns `[]` instead of erroring

**File:** `attacks/schema.py`
**Location:** `load_attack_library()`, the `sorted(library_dir.glob("*.yaml"))` loop (around lines 116–125)
**Severity:** Low
**Type:** Edge case / developer experience
**Found by:** code-reviewer agent, 2026-07-28

## Problem

```python
library_dir = Path(library_dir)
all_cases: list[AttackCase] = []
seen_ids: set[str] = set()
for yaml_path in sorted(library_dir.glob("*.yaml")):
    ...
```

`Path.glob()` on a directory that doesn't exist doesn't raise — it just yields nothing. So `load_attack_library("attacks/librray")` (a typo'd path) behaves identically to a real, correctly-loaded, empty library: it returns `[]` with no error at all.

This is spec-intended behavior for the *real* empty-library case (see `06_attack_schema.md`'s edge cases: "Empty `attacks/library/`... should return `[]` cleanly, not raise") — the gap is only that a typo'd/missing directory is indistinguishable from a legitimately empty one.

## Why it matters

Every other failure mode in this file fails loudly and specifically (bad YAML shape, validation errors, duplicate ids). A silently-empty result from a typo'd path is the one case that fails *quietly* — and it's a real Week 3–4 risk: if `engine/runner.py` later calls `load_attack_library()` with a wrong path (e.g. relative to the wrong cwd), the runner will just report "0 attack cases, all passed" instead of a clear "directory not found," which could look like a passing security audit that never actually ran.

## Suggested fix

Distinguish "exists and is empty" from "doesn't exist":

```python
library_dir = Path(library_dir)
if not library_dir.is_dir():
    raise ValueError(f"attack library directory not found: {library_dir}")
```

Add this check right after resolving `library_dir` to a `Path`, before the glob loop.

## Acceptance criteria

- [ ] `load_attack_library("some/nonexistent/path")` raises a clear `ValueError` naming the missing path.
- [ ] `load_attack_library()` against a real, empty `attacks/library/` directory still returns `[]` without raising (no regression on the spec's documented empty-library behavior).
