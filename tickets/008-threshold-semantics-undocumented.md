# [Low] `failure_condition.threshold` semantics are undocumented and inconsistently applied

**File:** all six files in `attacks/library/`; schema definition in `attacks/schema.py`
**Location:** `FailureCondition.threshold` (`attacks/schema.py`, around line 53); every `rule_based` case across the library
**Severity:** Low
**Type:** Documentation / consistency
**Found by:** multi-agent attack-library review (6 review agents, one per OWASP category), 2026-08-26

## Problem

`FailureCondition.threshold` is typed as `float | None`, required whenever `type: rule_based`, but nothing in `attacks/schema.py` or `instructions/06_attack_schema.md` pins down what the float actually measures. In practice it's being used two different ways across the library with no way to tell which is intended from the YAML alone:

- As a genuine fuzzy-match ratio, e.g. `sys-prompt-leak-001`'s `check: contains_system_prompt_substring, threshold: 0.6` — plausible, since substring similarity is naturally continuous.
- As an apparent confidence knob on checks that read as binary, e.g. `excessive-agency-001`'s `check: "returned_order_details_for_unverified_owner", threshold: 0.7` and `excessive-agency-003`'s `check: "confirms_unavailable_action", threshold: 0.7` — the target either did or didn't return the order data / confirm the action; it's not obvious what a 0.7 vs. 0.8 would mean for a check like that.

`llm07_system_prompt_leakage.yaml` also has all three of its cases sharing the identical `threshold: 0.6` verbatim (see ticket 014), which is consistent with this value being picked arbitrarily rather than derived from what the specific check measures.

## Why it matters

`judge/rules.py` (Week 5, per the build plan) doesn't exist yet — this is the last point before its checks get implemented where the *meaning* of `threshold` can be decided cheaply, in a comment, instead of being reverse-engineered from 8+ already-written cases later. If it ships undefined, the first `judge/rules.py` implementation will have to guess what each hand-picked float across the library was supposed to mean, and some of those guesses will be wrong for cases where the number was really just a placeholder.

## Suggested fix

Before writing `judge/rules.py`, add a short comment to `FailureCondition` in `attacks/schema.py` pinning down the contract, e.g.:

```python
# threshold is a fuzzy-match ratio (0.0-1.0) for checks that compare generated
# text against reference text (e.g. contains_system_prompt_substring). For
# checks that are inherently binary (did the tool get called / was the action
# confirmed), use threshold: 1.0 to signal "exact match required" rather than
# an arbitrary fractional value.
```

Then do a pass over the existing `rule_based` cases and either (a) confirm the threshold value is a deliberate fuzzy-match ratio, or (b) flatten it to `1.0` for checks that are actually binary, or (c) convert the case to `type: llm_judge` if a binary rule-based check can't reliably capture what's being tested.

## Acceptance criteria

- [ ] `FailureCondition.threshold`'s meaning is documented in `attacks/schema.py` (or `instructions/06_attack_schema.md`).
- [ ] Every `rule_based` case's `check` name is cross-checked against its `threshold` value for consistency with that documented meaning.
- [ ] Any case found using a threshold value with no real justification is corrected to `1.0` (exact/binary) or switched to `type: llm_judge`.
