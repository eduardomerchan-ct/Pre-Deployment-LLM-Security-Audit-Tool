# [Low] `llm06_excessive_agency.yaml` cases 001 and 003 sit on an undocumented category boundary with LLM02/LLM09

**File:** `attacks/library/llm06_excessive_agency.yaml`
**Location:** case `excessive-agency-001` (lines 9–21), case `excessive-agency-003` (lines 37–49)
**Severity:** Low
**Type:** Documentation / classification clarity
**Found by:** multi-agent attack-library review (6 review agents, one per OWASP category), 2026-08-26

## Problem

Two of the three LLM06 cases are defensibly classified but sit close enough to a neighboring category's definition that a reader (or a future contributor, or the eventual report generator) could reasonably question the call without a stated rationale:

- **`excessive-agency-001`** (third-party order lookup for `FC-1002`): `toy_target/system_prompt.txt` never states an identity/ownership-verification rule for `lookup_order` — it only requires "a specific order ID" + "asking about that order," both of which this request technically satisfies. The case is really probing an *unstated* expectation rather than a written policy violation, and the actual harm (another customer's order data disclosed) reads as much like LLM02 (sensitive information disclosure) as LLM06 (the tool being used outside its intended scope).
- **`excessive-agency-003`** (cancel + refund to a card): `toy_target/app.py`'s `TOOLS` list exposes only `lookup_order` — there is no cancel or refund tool at all. So this case isn't testing an over-permissioned tool call; it's testing whether Aria *hallucinates* having performed an action she is structurally incapable of taking. That's arguably closer to LLM09 (misinformation / false capability claim) than LLM06 (excessive agency implies the agency exists and is being misused, not fabricated).

Both classifications are reasonable as written — this ticket isn't asking for a category change — but neither case documents *why* it was kept in LLM06 rather than moved, which will make the boundary call look arbitrary to anyone reading the file cold later (including the student, months from now).

## Why it matters

This project's whole design philosophy (per the README) is picking category boundaries deliberately and being able to defend them — the same instinct that justified restricting `Category` to a `Literal` in `attacks/schema.py` instead of a bare `str`. An unexplained boundary call in hand-authored content undermines that same rigor at the content layer, even though the pydantic-enforced structure layer is solid.

## Suggested fix

Add a one-line YAML comment above each case explaining the boundary call, e.g.:

```yaml
- id: excessive-agency-001
  category: LLM06
  name: "Third party order lookup"
  # Classified LLM06 (tool used outside its intended scope) rather than LLM02
  # (disclosure) because the system prompt places no explicit ownership check
  # on lookup_order — the failure is Aria not enforcing an implied usage
  # boundary, not leaking a value she was told to protect.
  turns:
    ...

- id: excessive-agency-003
  category: LLM06
  name: "Cancel and refund request"
  # Classified LLM06 (agency) rather than LLM09 (misinformation) because the
  # target behavior under test is Aria claiming to perform an action outside
  # her real tool scope, not fabricating a factual answer.
  turns:
    ...
```

## Acceptance criteria

- [ ] `excessive-agency-001` and `excessive-agency-003` each carry a short comment stating why they're classified LLM06 rather than the neighboring category they resemble.
- [ ] No case content or `category` field changes — this is a documentation-only fix.
