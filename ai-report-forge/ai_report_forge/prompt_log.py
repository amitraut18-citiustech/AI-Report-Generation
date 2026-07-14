"""In-memory log of what was actually sent to each LLM.

Powers the app's "Prompt Log" transparency page: for every ask it shows the
original question next to the scrubbed/anonymized payload that left for the
model. Bounded and process-local — this is a PoC demo surface, not an audit
trail (entries vanish on restart).

Keys are camelCase so the .NET client can deserialize them directly.
"""

from collections import deque
from datetime import datetime, timezone
from threading import Lock

_MAX_ENTRIES = 50

_entries: deque[dict] = deque(maxlen=_MAX_ENTRIES)
_lock = Lock()


def record(entry: dict) -> None:
    entry = {"timestamp": datetime.now(timezone.utc).isoformat(), **entry}
    with _lock:
        _entries.appendleft(entry)


def entries() -> list[dict]:
    """Newest first."""
    with _lock:
        return list(_entries)


def clear() -> None:
    with _lock:
        _entries.clear()
