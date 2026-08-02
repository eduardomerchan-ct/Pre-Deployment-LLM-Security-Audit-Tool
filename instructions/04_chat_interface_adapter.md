# Build Instructions: `targets/chat_interface.py` (optional / stretch)

## Status: optional

The original build plan flags this adapter as a stretch goal, only worth building "if time allows in week 9 polish," and says it's fine to document the design without fully building it. You've chosen to write it now anyway, ahead of schedule — that's a reasonable call since the design is fresh in your mind while you're already deep in the adapter layer, but don't let it block moving on to Week 3 if it turns out to be a time sink. If you get the structure in place and a real target UI to test against isn't available yet, that's an acceptable stopping point.

## Goal

`DirectAPIAdapter` only works when you have direct API access to the target. Real-world LLM security audits often only have a web chat UI to work with — no API key, no direct model access, just a browser. `ChatInterfaceAdapter` proves the architecture generalizes to that case: it drives an actual web page (typing into an input box, clicking submit, reading the rendered response) but still returns the exact same `TargetResponse` shape as `DirectAPIAdapter`. Anything built against `TargetAdapter.send()` — the execution engine, the mutation loop — should work identically whether it's pointed at this adapter or the API one, without knowing the difference.

## Prerequisites

- `targets/base.py` (file 1) must exist.
- `pip install playwright` and `playwright install` (downloads browser binaries) must be run — this isn't in the project's `requirements.txt` yet, since it's a stretch dependency; add it there if you commit to building this.
- You'll need *some* web chat UI to point this at for real testing. If none is available, you can still build and structurally validate this adapter (it will construct and its selectors will be well-defined), but the end-to-end self-test will have to wait until a target exists — that's expected and fine, note it as a known limitation rather than blocking on it.

## Spec

### `ChatInterfaceAdapter(TargetAdapter)`

**`__init__(self, url: str, input_selector: str, submit_selector: str, response_selector: str, headless: bool = True)`**
- Stores the target page URL and the three CSS/XPath selectors needed to interact with the chat UI: where to type, what to click to submit, and where to read the response from.
- Consider accepting these via a second section of `config/target_config.yaml` (e.g. a nested `chat_interface:` block) rather than only as constructor arguments, so this adapter is config-driven like `DirectAPIAdapter` rather than requiring code edits per target. If you go this route, document the expected YAML shape in a comment at the top of this file.
- Launches (or lazily prepares to launch) a Playwright browser instance. Decide whether the browser launches once in `__init__` and stays open across multiple `send()` calls (faster, but you must manage lifecycle/cleanup) or launches fresh per `send()` call (simpler, slower, no state to manage). For a first version, launching once and reusing the page across calls is the more realistic simulation of a real conversation anyway, since the page's own JS state may track conversation history.

**`send(self, prompt: str, history: list | None = None) -> TargetResponse`**
- If this is the first call (or `history` is empty) and the page isn't already loaded, navigate to `url`.
- Locate the input element via `input_selector`, type `prompt` into it.
- Locate and click the submit element via `submit_selector` (or submit via Enter key if that's how the target UI works — make this configurable if you hit a real target that needs it).
- Wait for a new response to appear at `response_selector` — this is the trickiest part, see "Edge cases" below.
- Extract the response text from the DOM.
- Measure latency the same way as `DirectAPIAdapter` (wall-clock around the whole interaction).
- Return a `TargetResponse` with `text` set to the extracted string, `raw` set to whatever's useful (e.g. the full page HTML snippet at `response_selector`, or a Playwright locator snapshot), `latency_ms`, and `timestamp`.

### On `history`

Unlike `DirectAPIAdapter`, this adapter doesn't necessarily need to *do* anything with the `history` parameter — a real chat UI usually maintains its own conversation state server-side or in the DOM as you keep sending messages into the same page session. Document this explicitly: `history` may be effectively ignored by this adapter as long as the same adapter instance is reused across a multi-turn test case (so the browser session itself carries the context). This is a legitimate design difference from `DirectAPIAdapter` worth calling out in a docstring, not a bug.

## Step-by-step build instructions

1. Imports: `time`, `datetime`, Playwright's sync API (`from playwright.sync_api import sync_playwright`), and `TargetAdapter`/`TargetResponse` from `.base`.
2. Write `__init__`: store config/selectors, decide on and implement the browser-lifecycle approach chosen above.
3. Write a small private helper, e.g. `_ensure_page_loaded()`, that navigates to `url` only if a page isn't already open — keeps `send()` itself readable.
4. Write `send()`: locate input → fill with `prompt` → submit → wait for response → extract text → time the whole thing → build and return `TargetResponse`.
5. Add a `close()` method (not part of the `TargetAdapter` contract, but a practical addition) that shuts down the Playwright browser cleanly, and consider supporting the adapter as a context manager (`__enter__`/`__exit__`) so callers can `with ChatInterfaceAdapter(...) as adapter:` and be sure the browser closes even on error.

## Edge cases to handle

- **Knowing when the response is "done."** Web chat UIs often stream responses token-by-token. A naive "read `response_selector`'s text immediately after submit" will grab a partial reply. Use Playwright's built-in waiting (e.g. `page.wait_for_selector`, polling the element's text content until it stabilizes across two checks a short interval apart, or waiting for a specific "done streaming" DOM signal if the target UI exposes one) rather than a fixed `sleep()`.
- **Element not found / timeout.** If `input_selector`, `submit_selector`, or `response_selector` don't match anything (wrong selector, page structure changed, page didn't load), Playwright will raise a timeout error — let it propagate with a clear message rather than swallowing it, since a silent failure here would look like "the target refused" to a judge later, which is a misleading false result.
- **Multiple response elements matching the selector.** If `response_selector` matches every message bubble in the conversation (not just the latest), you need to select specifically the newest one — e.g. `page.locator(response_selector).last`.
- **Headless vs. headed mode.** Keep `headless=True` as the default for automated runs, but make sure `headless=False` works too — you'll want to watch the browser interact with a real target at least once while debugging selectors.

## Resources

- [Playwright Python docs](https://playwright.dev/python/) — start with "Getting Started" and the "Locators" guide.
- [Playwright sync API reference](https://playwright.dev/python/docs/api/class-playwright) specifically `Page.fill`, `Page.click`, `Page.wait_for_selector`, `Locator.last`.
- [Playwright auto-waiting guide](https://playwright.dev/python/docs/actionability) — relevant background for why you generally shouldn't need manual `sleep()` calls for element interactions (though waiting for streamed text to *stabilize* is a different problem you'll still need to solve yourself).

## Definition of done / self-test

This adapter's real self-test depends on having a live web chat target, which may not exist yet — that's fine, treat it as conceptually complete once:

1. `from targets.chat_interface import ChatInterfaceAdapter` imports without error.
2. The class constructs without error given a plausible `url`/selectors, even against a placeholder/test HTML page (you could hand-write a tiny local HTML file with an `<input>`, a `<button>`, and a `<div>` that echoes the input back, and point `url` at it via `file://` — a cheap way to validate the interaction loop without needing a real chatbot).
3. If you do build the local HTML test page above, confirm a full `send("hello")` call returns a `TargetResponse` with the expected echoed text and sane `latency_ms`/`timestamp` — this validates the *mechanics* even without a real LLM behind it.
4. Note in a code comment or your own notes which real target (if any) this has actually been validated against, so it's clear later whether this adapter is "built" or "built and proven."
