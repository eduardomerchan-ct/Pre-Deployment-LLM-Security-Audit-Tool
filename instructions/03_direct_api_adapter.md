# Build Instructions: `targets/direct_api.py`

## Goal

This is the adapter the rest of the tool will actually exercise all summer: `DirectAPIAdapter`, a concrete implementation of `TargetAdapter` (file 1) that talks to a Claude model directly through the Anthropic Messages API, configured via `config/target_config.yaml` (file 2) instead of hardcoded values. Functionally, it's the same request/response/tool-use logic already proven out in `toy_target/app.py`'s `chat()` function — you're not inventing new behavior, you're re-shaping existing, working logic to fit the `TargetAdapter` contract and to pull its settings from config instead of module-level constants.

Once this exists, `engine/runner.py` (Week 3–4) can be written entirely against `TargetAdapter.send()` and never need to know it's talking to Aria specifically — swap the config file and it points somewhere else.

## Prerequisites

- `targets/base.py` (file 1) must exist and be importable — `DirectAPIAdapter` will subclass `TargetAdapter` and return `TargetResponse`.
- `config/target_config.yaml` (file 2) must exist with at least `model`, `system_prompt_path`, `max_tokens`.
- Read through `toy_target/app.py` again before starting, specifically the `chat()` function (lines ~43-69) and the `TOOLS` / `lookup_order` definitions above it. You are re-implementing this exact request/tool-resolution loop, not designing a new one — go re-read it now if it's not fresh in your mind.

## Spec

### `DirectAPIAdapter(TargetAdapter)`

**`__init__(self, config_path: str = "config/target_config.yaml")`**
- Loads and parses the YAML config (reuse the `yaml.safe_load` approach validated in file 2's self-test).
- Reads the system prompt file at `system_prompt_path` (relative to project root) into memory once, at init time — not on every `send()` call.
- Stores `model` and `max_tokens` from config as instance attributes.
- Constructs the Anthropic client (`anthropic.Anthropic(api_key=...)`), reading `ANTHROPIC_API_KEY` from the environment the same way `toy_target/app.py` does (`os.environ["ANTHROPIC_API_KEY"]`, after `load_dotenv()`).
- Defines/stores the `tools` list (the `lookup_order` tool schema) — either loaded from config if you chose to externalize it in file 2, or inlined here matching `toy_target/app.py`'s `TOOLS` constant.

**`send(self, prompt: str, history: list | None = None) -> TargetResponse`**
- Implements the abstract method from `TargetAdapter`.
- Appends `prompt` as a new user turn onto `history` (treating `None` the same as `[]`, per file 1's contract).
- Calls `self._client.messages.create(...)` with `model`, `max_tokens`, `system`, `tools`, and the running `messages` list — matching the call shape in `toy_target/app.py`.
- If the response's `stop_reason` is `"tool_use"`, resolves the tool call(s) (same pattern as `toy_target/app.py`: find `tool_use` blocks, call the corresponding local function, append a `tool_result` message, call the API again) and loops until a non-`tool_use` stop reason is reached.
- Extracts the final assistant-visible text the same way `toy_target/app.py` does: joining `block.text` for `block.type == "text"` blocks.
- Measures wall-clock latency around the full exchange (including any tool-use round trips) using `time.perf_counter()` before and after.
- Returns a `TargetResponse` with `text` set to the extracted reply, `raw` set to whatever you find most useful for debugging (the full final API response object, or the full updated `messages` list — your call, just be consistent), `latency_ms` computed from the timer, and `timestamp` set to `datetime.now(timezone.utc)` (or similar) captured at call start.

### Where `lookup_order` lives

Decide: does `DirectAPIAdapter` own its own copy of `lookup_order` and `FAKE_ORDERS`, or does it import them from `toy_target.app`? Importing from `toy_target.app` avoids duplicating the fake data, but it does couple the "general-purpose" adapter to the toy target's specific tool implementation, which cuts against the "reusable against any endpoint" goal stated in the plan. A clean middle ground: keep `lookup_order`/`FAKE_ORDERS` in `toy_target/app.py` as the source of truth (since they define the toy business logic under test) and have `DirectAPIAdapter` accept an optional `tool_handlers: dict[str, Callable]` in `__init__` that maps tool name → function, defaulting to `{"lookup_order": lookup_order}` imported from `toy_target.app` for now. That keeps the adapter generic in principle while still working out-of-the-box against the toy target today.

## Step-by-step build instructions

1. Imports: `os`, `time`, `yaml`, `datetime` (`datetime`, `timezone`), `anthropic.Anthropic`, `dotenv.load_dotenv`, and `TargetAdapter`/`TargetResponse` from `.base` (relative import within the `targets` package).
2. Call `load_dotenv()` at module level (or inside `__init__` — pick one and be consistent with how `toy_target/app.py` does it).
3. Write `__init__`: load config, read system prompt text, build the Anthropic client, set up `tools` and tool handlers as decided above.
4. Write `send()`: build the message list from `history` + new `prompt`, start the latency timer, enter the request/tool-resolution loop, extract final text, stop the timer, construct and return `TargetResponse`.
5. Keep the tool-resolution loop as a `while True` with an explicit `break`/`return` condition, exactly mirroring the proven structure in `toy_target/app.py`'s `chat()` — don't try to make it cleverer than the original; correctness here matters more than elegance since every test case in Weeks 3+ depends on this loop working.
6. Add a guard against infinite tool-use loops: cap the number of tool-resolution round trips (e.g., 5) and raise a clear error if exceeded, so a misbehaving model can't hang a test run.

## Edge cases to handle

- `history=None` and `history=[]` must behave identically (per file 1's contract) — don't let a `None` accidentally propagate into the Anthropic SDK call, which expects a list.
- API errors (rate limits, transient network failures): wrap the `messages.create()` call in a `try/except` with one retry, matching the plan's "basic try/except + one retry, nothing elaborate" guidance for the execution engine — this adapter is where that retry logic actually belongs, so `engine/runner.py` doesn't need its own.
- A response with `stop_reason == "tool_use"` but zero recognized tool names in its `tool_use` blocks (model invents a tool that doesn't exist) — decide what happens (log and return an error-shaped `TargetResponse`, or raise) rather than letting it silently hang.
- Multiple `tool_use` blocks in a single response (the model can request more than one tool call at once) — the loop must resolve all of them before sending the next message, not just the first.

## Resources

- [Anthropic Python SDK (GitHub)](https://github.com/anthropics/anthropic-sdk-python) — installation, client usage.
- [Anthropic Messages API reference](https://platform.claude.com/docs/en/api/messages) — request/response shape, `stop_reason` values.
- [Anthropic tool use guide](https://platform.claude.com/docs/en/build-with-claude/tool-use) — the request/tool_result loop pattern you're re-implementing.
- `toy_target/app.py` in this repo — your primary reference; the `chat()` function is the exact logic being adapted.

## Definition of done / self-test

Don't fully validate this in isolation — file 5 (`05_verification_smoke_test.md`) covers the real smoke test — but before moving on, confirm:

1. `from targets.direct_api import DirectAPIAdapter` imports without error.
2. `DirectAPIAdapter()` constructs without error (config loads, system prompt file reads, client builds) — this alone will catch most config-path and import mistakes before you spend an API call.
3. Proceed to `05_verification_smoke_test.md` for the full `send("hello")` check. (File 4, the optional Playwright adapter, can be built before or after the smoke test — order doesn't matter between files 3/4/5 as long as file 3 is done first.)
