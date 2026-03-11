from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TraceEntry:
    """A single traced operation call within a ``run()`` execution."""

    operation: str
    args: dict[str, Any] = field(default_factory=dict)
    result: Any = None
    error: str | None = None
    permission: str = ""
    duration_ms: float = 0.0


_current_trace: ContextVar[list[TraceEntry] | None] = ContextVar(
    "_current_trace", default=None
)


def record_entry(entry: TraceEntry) -> None:
    """Append *entry* to the active trace. No-op when tracing is inactive."""
    trace = _current_trace.get()
    if trace is not None:
        trace.append(entry)


def get_trace() -> list[TraceEntry] | None:
    """Return the current trace list, or ``None`` if tracing is inactive."""
    return _current_trace.get()
