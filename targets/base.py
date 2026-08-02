"""Shared contract for anything the audit engine sends prompts to.

Every attack case eventually boils down to "send a prompt to the target and
see what comes back." `TargetAdapter` is that contract: any target (the toy
API chatbot, a real web chat UI, some other team's endpoint) implements
`send()` the same way, and every response comes back as a `TargetResponse`.
Later modules (the runner, the mutation loop) are written against this
interface, not against any one concrete target — so what's actually behind
`send()` can change without breaking anything downstream.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class TargetResponse:
    """Plain data container returned by every adapter's send().

    frozen=True makes instances immutable after creation — once a response
    comes back from a target, nothing downstream (judges, loggers, report
    generators) should be able to accidentally mutate it. Attempting to
    reassign a field raises an error instead of silently corrupting data.
    """

    # Final assistant-visible reply text, with tool-use round-trips already
    # resolved. This is what attack judges will actually inspect.
    text: str

    # The unprocessed underlying response object (or list of turns) —
    # kept around for debugging and for anything a judge needs that isn't
    # captured in `text`.
    raw: Any

    # Wall-clock time the call took, in milliseconds.
    latency_ms: float

    # UTC time the call was made. Every run log entry needs this.
    timestamp: datetime


class TargetAdapter(ABC):
    """Abstract base class every concrete target adapter must implement.

    Subclassing ABC and marking send() with @abstractmethod means Python
    refuses to instantiate TargetAdapter directly, and refuses to
    instantiate any subclass that doesn't override send(). This is how the
    contract is enforced at runtime, not just by convention.

    Only one abstract method on purpose: send() is all engine/runner.py
    will ever call. Anything adapter-specific (API keys, config loading,
    tool definitions) belongs in each concrete subclass's __init__, not
    here.
    """

    @abstractmethod
    def send(self, prompt: str, history: list | None = None) -> TargetResponse:
        """Send `prompt` to the target and return a TargetResponse.

        prompt: the next user turn to send.
        history: prior conversation turns, in whatever shape the concrete
            adapter needs internally (e.g. a list of role/content dicts).
            history=None and history=[] must be treated identically by
            conforming subclasses — both mean "start a fresh conversation."
            Implementers: don't let these two cases diverge.

        No body beyond this docstring — @abstractmethod is what makes this
        truly abstract. If it had so much as a `pass` here, TargetAdapter
        would still refuse to instantiate on its own, but adding a body at
        all invites subclasses to accidentally rely on a default that
        doesn't actually do anything.
        """
