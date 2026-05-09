from __future__ import annotations
import threading
import time
from typing import Dict

_lock = threading.Lock()
_counters: Dict[str, int] = {
    "docs_ingested": 0,
    "chunks_indexed": 0,
    "queries": 0,
    "embed_api_calls": 0,
    "retries": 0,
}
_start_time = time.time()


def increment(counter: str, by: int = 1) -> None:
    with _lock:
        _counters[counter] = _counters.get(counter, 0) + by


def get_metrics() -> dict:
    with _lock:
        return {**_counters, "uptime_seconds": int(time.time() - _start_time)}


def reset() -> None:
    """Reset all counters — intended for testing."""
    with _lock:
        for key in list(_counters):
            _counters[key] = 0
