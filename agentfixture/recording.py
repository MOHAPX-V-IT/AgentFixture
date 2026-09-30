"""Explicit recording: the supplied callback really executes."""

import copy
import inspect
import json
import time
from pathlib import Path

DEFAULT_KEYS = {
    "authorization",
    "password",
    "secret",
    "token",
    "api_key",
    "access_token",
    "refresh_token",
    "cookie",
}


def redact(value, keys):
    if isinstance(value, dict):
        return {
            k: "[REDACTED]" if k.lower() in keys else redact(v, keys)
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [redact(v, keys) for v in value]
    return copy.deepcopy(value)


class Recorder:
    """Records JSON-compatible arguments/results. Exceptions store type, not message."""

    def __init__(self, *, redact_keys=()):
        self.keys = DEFAULT_KEYS | {key.lower() for key in redact_keys}
        self.calls = []

    def _begin(self, name, arguments):
        if not isinstance(name, str) or not name or not isinstance(arguments, dict):
            raise ValueError("Expected a tool name and argument object")
        json.dumps(arguments, allow_nan=False)
        row = {"name": name, "arguments": redact(arguments, self.keys)}
        self.calls.append(row)
        return row, time.perf_counter()

    def _finish(self, row, started, result):
        json.dumps(result, allow_nan=False)
        row["result"] = redact(result, self.keys)
        row["duration_ms"] = round((time.perf_counter() - started) * 1000, 3)

    def call(self, name, arguments, callback):
        if inspect.iscoroutinefunction(callback):
            raise TypeError("Use acall for async tools")
        row, started = self._begin(name, arguments)
        try:
            result = callback(**copy.deepcopy(arguments))
            self._finish(row, started, result)
            return result
        except Exception as exc:
            row["error"] = (
                "timeout" if isinstance(exc, TimeoutError) else type(exc).__name__
            )
            row["duration_ms"] = round((time.perf_counter() - started) * 1000, 3)
            raise

    async def acall(self, name, arguments, callback):
        row, started = self._begin(name, arguments)
        try:
            result = await callback(**copy.deepcopy(arguments))
            self._finish(row, started, result)
            return result
        except Exception as exc:
            row["error"] = (
                "timeout" if isinstance(exc, TimeoutError) else type(exc).__name__
            )
            row["duration_ms"] = round((time.perf_counter() - started) * 1000, 3)
            raise

    def save(self, path, *, expect=None, overwrite=False):
        payload = {
            "version": 1,
            "calls": self.calls,
            "expect": {} if expect is None else expect,
        }
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w" if overwrite else "x", encoding="utf-8") as stream:
            json.dump(payload, stream, indent=2, ensure_ascii=False, allow_nan=False)
