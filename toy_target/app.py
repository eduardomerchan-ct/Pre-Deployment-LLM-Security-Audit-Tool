"""Toy customer-support chatbot — the authorized target for this audit tool.

Not a production app. Exists to give the attack library something real to
attack: a system prompt worth leaking, a policy worth bypassing, and a tool
worth misusing.
"""
import os
from pathlib import Path

from anthropic import Anthropic
# Pyrefly type fix: import the SDK's own param types so TOOLS/messages are
# checked against what messages.create() actually accepts, instead of the
# checker guessing a too-narrow type from how the plain dicts are used.
from anthropic.types import MessageParam, ToolParam, ToolResultBlockParam
from dotenv import load_dotenv

load_dotenv()

MODEL = "claude-sonnet-5"
MAX_TOKENS = 1024
SYSTEM_PROMPT = (Path(__file__).parent / "system_prompt.txt").read_text().strip()

# FIX: this used to be "_client = Anthropic(api_key=...)" sitting right here,
# which ran the instant this file was imported -- even by code that only
# wanted lookup_order() below and never asked for a live API connection.
# Now it's just an empty placeholder (None = "not built yet").
_client = None


def _get_client():
    # FIX: this function is the actual fix. 
    
    # import time; it only executes the first time chat() actually needs it.
    global _client
    if _client is None:
        # Only reached the very first time we actually need to talk to the
        # API. After this runs once, _client is no longer None, so every
        # later call just reuses the same connection instead of rebuilding it.
        _client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


FAKE_ORDERS = {
    "FC-1001": {"status": "shipped", "eta": "2026-07-18", "item": "Wireless mouse"},
    "FC-1002": {"status": "processing", "eta": "2026-07-22", "item": "27in monitor"},
}

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


def lookup_order(order_id: str) -> dict:
    return FAKE_ORDERS.get(order_id, {"error": f"No order found with ID {order_id}"})


def chat(user_message: str, history: list | None = None) -> tuple[str, list]:
    """Send one user turn, resolving any tool calls, and return (reply_text, new_history)."""
    # Pyrefly fix: annotated as list[MessageParam] so appends below (both
    # plain-text and tool_result content) match what the SDK expects,
    # instead of the checker locking in "str content" from this line alone.
    messages: list[MessageParam] = list(history) if history else []
    messages.append({"role": "user", "content": user_message})

    while True:
        # FIX: was "_client.messages.create(...)". Calling _get_client()
        # here is the one line that actually triggers the lazy build above
        # (first time only) -- this is "the moment it's actually needed."
        response = _get_client().messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            reply_text = "".join(b.text for b in response.content if b.type == "text")
            return reply_text, messages

        # Pyrefly fix: same untyped-dict issue as TOOLS/messages above --
        # annotating this closes the gap that only appeared once
        # `messages` itself became strictly typed.
        tool_results: list[ToolResultBlockParam] = []
        for block in response.content:
            if block.type == "tool_use" and block.name == "lookup_order":
                # SECURITY FIX: block.input comes from the model, so order_id
                # could be missing or the wrong type -- nothing guarantees
                # it's actually a string just because we asked for one.
                order_id = block.input.get("order_id")
                # isinstance() actually checks the value while the code runs
                # (the old cast() only told the type checker to trust us,
                # with zero real check). If it's not a string, we stop here
                # instead of ever calling lookup_order() with bad data.
                if not isinstance(order_id, str):
                    result = {
                        "error": f"invalid order_id: expected string, got {type(order_id).__name__}"
                    }
                else:
                    result = lookup_order(order_id=order_id)
                tool_results.append(
                    {"type": "tool_result", "tool_use_id": block.id, "content": str(result)}
                )
        messages.append({"role": "user", "content": tool_results})


if __name__ == "__main__":
    print("Aria (FakeCorp support) — type 'quit' to exit.\n")
    history: list = []
    while True:
        user_input = input("you> ").strip()
        if user_input.lower() in {"quit", "exit"}:
            break
        reply, history = chat(user_input, history)
        print(f"aria> {reply}\n")
