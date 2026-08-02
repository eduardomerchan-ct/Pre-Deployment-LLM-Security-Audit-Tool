# Build Instructions: `targets/base.py`

## Goal

Every attack case the audit tool runs eventually boils down to "send this prompt to the target and see what comes back." Right now that logic lives only inside `toy_target/app.py`, hardcoded to one specific chatbot. `targets/base.py` breaks that dependency: it defines a contract — `TargetAdapter` — that any target (the toy API chatbot, a real web chat UI, some other team's endpoint) can implement the same way. Every later module in this project (`engine/runner.py` in Weeks 3–4, the mutation loop in Week 8) will be written against this contract, not against `toy_target/app.py` directly. Get this interface right and nothing downstream has to care what's actually behind it.

This file defines two things: an abstract base class (`TargetAdapter`) and a plain data container (`TargetResponse`) that every adapter's `send()` method must return.

## Prerequisites

None — this is the first file in the adapter layer and has no dependencies on other Week 2 files. Everything else in `targets/` depends on this file existing first.

Check whether `targets/__init__.py` exists yet (it likely doesn't — `targets/` currently only contains the empty folder). If it's missing, create an empty `targets/__init__.py` so `targets` is importable as a package.

## Spec

### `TargetResponse` (dataclass)

A frozen, plain-data container — no behavior, just fields. Every adapter's `send()` returns exactly one of these.

| Field | Type | Meaning |
|---|---|---|
| `text` | `str` | The final assistant-visible reply text, with any tool-use round-trips already resolved. This is what attack judges (Week 5–6) will actually inspect. |
| `raw` | `Any` | The unprocessed underlying response object (or list of turns, if that's more useful) — kept for debugging and for anything the rule-based judge might need that isn't in `text`. |
| `latency_ms` | `float` | Wall-clock time the call took, in milliseconds. Useful later for spotting anomalies (e.g., a suspiciously fast refusal vs. a slow "thinking it over" compliance). |
| `timestamp` | `datetime` | When the call was made (UTC). Every run log entry needs this. |

Decide whether to make this a `@dataclass(frozen=True)`. Frozen is recommended — nothing downstream should mutate a response after the fact, and immutability catches bugs early.

### `TargetAdapter` (abstract base class)

Built on Python's `abc` module (`ABC`, `abstractmethod`).

One abstract method:

```
send(self, prompt: str, history: list | None = None) -> TargetResponse
```

- `prompt`: the next user turn to send.
- `history`: prior conversation turns in whatever shape the concrete adapter needs internally (a list of role/content dicts is the natural choice, matching the Anthropic Messages API shape already used in `toy_target/app.py`). `None` or `[]` means "start a fresh conversation."
- Returns: a `TargetResponse`.

That's the entire public contract. Resist the urge to add more abstract methods right now — `send()` is all `engine/runner.py` will ever call. Anything adapter-specific (API keys, config loading, tool definitions) belongs in each concrete subclass's `__init__`, not in the abstract interface.

## Step-by-step build instructions

1. Create `targets/__init__.py` (empty file) if it doesn't already exist, so `targets` is a proper package.
2. In `targets/base.py`, import what you need: `abc.ABC`, `abc.abstractmethod`, `dataclasses.dataclass`, `datetime.datetime`, and `typing.Any`.
3. Define `TargetResponse` as a dataclass with the four fields above, in the order given. Add type hints on every field — this is a data contract, precision matters.
4. Define `TargetAdapter(ABC)` with a single `@abstractmethod` named `send`, matching the signature above exactly (parameter names matter — subclasses will use keyword calls in tests later).
5. Do not implement `send()` in the base class, not even with a `pass` body that returns `None` — `@abstractmethod` should be the only thing there, so Python refuses to instantiate `TargetAdapter` directly and forces every subclass to actually implement it.
6. Add a short module-level docstring explaining that this is the shared contract for anything the audit engine can send prompts to.

## Edge cases to handle

- `history=None` must be treated identically to `history=[]` by conforming subclasses — document this expectation in the abstract method's docstring so implementers don't diverge (you'll be the one implementing `DirectAPIAdapter` next, so this is a note to yourself).
- Don't put any Anthropic-specific, YAML-specific, or Playwright-specific imports in this file. If `base.py` imports anything beyond the Python standard library, that's a signal something belongs in a subclass instead.

## Resources

- [Python `abc` module docs](https://docs.python.org/3/library/abc.html) — `ABC` and `@abstractmethod`.
- [Python `dataclasses` module docs](https://docs.python.org/3/library/dataclasses.html) — including the `frozen=True` option.
- [PEP 604 – Allow writing union types as `X | Y`](https://peps.python.org/pep-0604/) — relevant for the `list | None` type hint (already used elsewhere in this codebase, e.g. `toy_target/app.py`'s `chat()` signature).

## Definition of done / self-test

You can't fully "run" this file yet (no concrete adapter exists), but you can sanity-check the contract itself:

1. In a Python REPL, `from targets.base import TargetAdapter, TargetResponse`.
2. Try `TargetAdapter()` directly — it should raise `TypeError: Can't instantiate abstract class TargetAdapter with abstract method send`. If it doesn't raise, `send` isn't properly marked abstract.
3. Construct a `TargetResponse` by hand with dummy values (`TargetResponse(text="hi", raw=None, latency_ms=12.3, timestamp=datetime.now())`) and confirm it builds without error and the fields come back as expected via attribute access.
4. Move on to `02_target_config_yaml.md` once both checks pass.
