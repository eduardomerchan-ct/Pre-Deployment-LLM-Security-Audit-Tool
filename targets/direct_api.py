"""Concrete TargetAdapter that talks to a Claude model via the Anthropic
Messages API directly.

This is the same request/tool-use loop already proven out in
toy_target/app.py's chat() function, reshaped to fit the TargetAdapter
contract (file 1) and to pull its settings from config/target_config.yaml
(file 2) instead of module-level constants. Nothing about the underlying
logic is new here -- see toy_target/app.py for the original.
"""

import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import yaml
from anthropic import Anthropic
from pydantic import BaseModel, ConfigDict, ValidationError
# Pyrefly type fix: import the SDK's own param types so TOOLS/messages are
# checked against what messages.create() actually accepts, instead of the
# checker guessing a too-narrow type from how the plain dicts are used.
from anthropic.types import MessageParam, ToolParam, ToolResultBlockParam
from dotenv import load_dotenv

from .base import TargetAdapter, TargetResponse
from toy_target.app import lookup_order

# Matches toy_target/app.py's convention: load .env once at import time,
# not per-call. (toy_target/app.py also calls load_dotenv() itself when it's
# imported below, so this is technically redundant -- but it's kept here too
# so this module doesn't silently depend on that side effect.)
load_dotenv()

# Tool schema mirrors toy_target/app.py's TOOLS constant exactly. This is
# inlined here (per the build spec) rather than imported, because it's the
# schema the *adapter* sends to the API on every call -- the schema belongs
# with the code that makes the API call, while the handler logic
# (lookup_order, FAKE_ORDERS) stays in toy_target/app.py as the source of
# truth for the toy business data.
# Pyrefly fix: annotated as list[ToolParam] (not a bare list) so this matches
# what messages.create(tools=...) expects. Contents are unchanged.
TOOLS: list[ToolParam] = [
    {
        "name": "lookup_order",
        "description": "Look up the status of a FakeCorp order by order ID.",
        "input_schema": {
            "type": "object",
            "properties": {"order_id": {"type": "string"}},
            "required": ["order_id"],
        },
    }
]


# SECURITY FIX: the input_schema above only tells the *model* what shape to
# send -- it's a hint, not an enforced rule, so a misbehaving or attacked
# model can still ignore it. This pydantic model is the runtime twin of
# that schema: it's what actually checks the arguments once they come
# back, before any handler function runs.
class LookupOrderArgs(BaseModel):
    # SECURITY FIX: by default pydantic silently drops fields it doesn't
    # recognize instead of flagging them. extra="forbid" turns that off --
    # an unexpected field (the model sending more than it was asked for)
    # now fails validation instead of being quietly thrown away. In a
    # security tool, an unrequested field showing up in a tool call is a
    # signal worth seeing, not noise worth hiding.
    model_config = ConfigDict(extra="forbid")

    order_id: str


# Maps each tool name to the pydantic model that validates its arguments.
# Every tool in _tool_handlers needs a matching entry here -- the dispatch
# loop below refuses to call a tool with no registered schema instead of
# silently skipping validation for it.
TOOL_ARG_SCHEMAS: dict[str, type[BaseModel]] = {"lookup_order": LookupOrderArgs}

# Cap on tool-resolution round trips per send() call. Without a cap, a model
# that keeps calling tools forever (buggy, or an attack designed to induce
# that behavior) would hang a test run indefinitely instead of failing loudly.
MAX_TOOL_ROUNDTRIPS = 5


class DirectAPIAdapter(TargetAdapter):
    """Sends prompts straight to a Claude model through the Messages API.

    Configured entirely from config/target_config.yaml -- swap that file to
    point this adapter at a different model or system prompt without
    touching any code.
    """

    def __init__(
        self,
        config_path: str = "config/target_config.yaml",
        tool_handlers: dict[str, Callable] | None = None,
    ):
        # Anchor against this file's own location -- not the process's
        # current working directory -- so construction resolves correctly
        # no matter where the caller was run from, matching the guarantee
        # config/target_config.yaml makes (and the same __file__-anchoring
        # toy_target/app.py already uses). config_path itself is left
        # unmodified when already absolute, so an explicit absolute path
        # (e.g. from a test) still works.
        project_root = Path(__file__).resolve().parent.parent
        resolved_config_path = (
            project_root / config_path if not Path(config_path).is_absolute() else Path(config_path)
        )
        with open(resolved_config_path, "r") as f:
            config = yaml.safe_load(f)

        # system_prompt_path is documented (in target_config.yaml) as
        # relative to the project root. Read once here, not per send()
        # call, since the file never changes mid-run.
        self._system_prompt = (project_root / config["system_prompt_path"]).read_text().strip()

        self.model = config["model"]
        self.max_tokens = config["max_tokens"]

        self._client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

        self._tools = TOOLS
        # tool_handlers is injected rather than hardcoded so this adapter
        # stays generic in principle -- a future target with different tools
        # could pass in its own name -> function map -- while still working
        # out-of-the-box against the toy target today via the default.
        # `is not None` (not truthiness) so an explicit tool_handlers={}
        # stays empty instead of silently falling back to the default --
        # needed for tests that exercise the unknown-tool path.
        self._tool_handlers = (
            tool_handlers if tool_handlers is not None else {"lookup_order": lookup_order}
        )

    def send(self, prompt: str, history: list | None = None) -> TargetResponse:
        """Send one user turn, resolving any tool calls, and return a TargetResponse."""
        timestamp = datetime.now(timezone.utc)
        start = time.perf_counter()

        # history=None and history=[] must behave identically (TargetAdapter
        # contract). Normalize before use so a bare None never reaches the
        # Anthropic SDK, which expects messages to be an actual list. Copying
        # (list(...)) also avoids mutating a history list the caller passed in.
        # Pyrefly fix: annotated as list[MessageParam] so appends below (both
        # plain-text and tool_result content) match what the SDK expects,
        # instead of the checker locking in "str content" from this line alone.
        messages: list[MessageParam] = list(history) if history else []
        messages.append({"role": "user", "content": prompt})

        roundtrips = 0
        while True:
            # Checked before calling the API (not after) so the cap actually
            # prevents the (MAX_TOOL_ROUNDTRIPS + 1)th call from ever being
            # made, instead of just detecting it one call too late.
            if roundtrips >= MAX_TOOL_ROUNDTRIPS:
                raise RuntimeError(
                    f"Exceeded {MAX_TOOL_ROUNDTRIPS} tool-resolution round trips "
                    "in a single send() call -- target is likely stuck in a "
                    "tool-use loop."
                )

            response = self._call_with_retry(messages)
            messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason != "tool_use":
                reply_text = "".join(
                    block.text for block in response.content if block.type == "text"
                )
                break

            roundtrips += 1

            # A single response can contain more than one tool_use block
            # (the model can ask for several tool calls at once). Resolve
            # all of them and send back one combined tool_result message
            # before making the next API call -- the API expects a
            # tool_result for every tool_use block, not just the first.
            # Pyrefly fix: same untyped-dict issue as TOOLS/messages above --
            # annotating this closes the gap that only appeared once
            # `messages` itself became strictly typed.
            tool_results: list[ToolResultBlockParam] = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                handler = self._tool_handlers.get(block.name)
                schema = TOOL_ARG_SCHEMAS.get(block.name)
                if handler is None:
                    # The model asked for a tool we don't have a handler
                    # for (it invented a name, or this adapter was
                    # constructed without a handler for a tool the system
                    # prompt still advertises). Don't raise and kill the
                    # whole send() over one bad call -- synthesize an
                    # error-shaped tool_result instead, same as a real API
                    # would report an unknown function, so the model sees
                    # the failure and gets a chance to recover or explain.
                    result = {"error": f"Unknown tool: {block.name}"}
                elif schema is None:
                    # SECURITY FIX: fail closed. A handler with no matching
                    # schema would otherwise skip validation entirely --
                    # refuse the call instead of trusting unchecked input.
                    result = {"error": f"No argument schema registered for tool: {block.name}"}
                else:
                    try:
                        # SECURITY FIX (the real fix): block.input is
                        # whatever the model sent -- wrong type, missing
                        # field, extra field, all possible. model_validate()
                        # actually checks it against the schema above and
                        # raises ValidationError if anything doesn't match,
                        # *before* the handler function ever runs.
                        args = schema.model_validate(block.input)
                        result = handler(**args.model_dump())
                    except ValidationError as e:
                        result = {"error": f"Tool '{block.name}' rejected its arguments: {e}"}
                    except Exception as e:
                        # SECURITY FIX: safety net for anything that still
                        # gets through (e.g. the handler itself raising) --
                        # turns a crash into an error result instead of
                        # killing the whole send() call.
                        result = {"error": f"Tool '{block.name}' raised {type(e).__name__}: {e}"}
                tool_results.append(
                    {"type": "tool_result", "tool_use_id": block.id, "content": str(result)}
                )
            messages.append({"role": "user", "content": tool_results})

        latency_ms = (time.perf_counter() - start) * 1000

        return TargetResponse(
            text=reply_text,
            # raw is the full updated messages list, not just the last API
            # response object -- this keeps every tool-use round trip
            # (including intermediate tool calls/results) visible for
            # debugging, since those don't otherwise appear in `text`.
            raw=messages,
            latency_ms=latency_ms,
            timestamp=timestamp,
        )

    def _call_with_retry(self, messages: list):
        """Call messages.create(), retrying exactly once on failure.

        Basic try/except + one retry, nothing elaborate (no backoff, no
        retry loop) -- matches this project's stated convention for API
        error handling. This is the only place that convention is applied;
        engine/runner.py (built later) calls send() and does not retry on
        its own, so this is the single point of retry logic for API calls.
        """
        try:
            return self._client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=self._system_prompt,
                tools=self._tools,
                messages=messages,
            )
        except Exception:
            # One retry, no special handling of the first failure -- if
            # this second attempt also fails, let the exception propagate.
            return self._client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=self._system_prompt,
                tools=self._tools,
                messages=messages,
            )
