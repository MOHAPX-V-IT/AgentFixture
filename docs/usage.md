# AgentFixture guide

## Install

Python 3.11+. From a local checkout: `python -m pip install -e ".[pytest]"`.
Use `python -m agentfixture` without installing when running in the repository root. No API keys are required for fixture replay or trace checks.

## Scenario format

```json
{
  "version": 1,
  "calls": [
    {"name": "rooms.search", "arguments": {"capacity": 4}, "result": ["room-1"]}
  ],
  "expect": {
    "required_calls": ["rooms.search"],
    "forbidden_calls": ["bookings.create"],
    "counts": {"rooms.search": 1},
    "order": ["rooms.search"],
    "arguments": {"rooms.search": {"capacity": 4}},
    "max_calls": 2
  }
}
```

`order` describes the complete sequence. `arguments` requires exact structural equality for every matching call and fails when no matching call exists. JSON booleans are distinct from numbers. Unknown rule names are rejected. Empty `expect` is permitted and imposes no behavior rules.

## Record tools

```python
from agentfixture import Recorder

recorder = Recorder(redact_keys=["email"])
response = recorder.call("search", {"query": "meeting room"}, lambda query: {"rooms": ["A"]})
recorder.save("recording.json", expect={"counts": {"search": 1}})
```

The callback is invoked using keyword arguments and **really executes**. Recording is explicit; it does not intercept SDKs or network traffic. `await recorder.acall(name, arguments, callback)` supports async callbacks. Calls are stored in invocation order. Parallel completion order and cancellation are not modeled by sequential replay.

Arguments and results must be JSON serializable. Validate callback result contracts yourself before side effects: a non-JSON result fails recording after execution. Saved exceptions contain the exception class name only; timeout is represented by `"error": "timeout"`. Error messages are omitted because they can contain secrets.

Default case-insensitive redaction keys: `authorization`, `password`, `secret`, `token`, `api_key`, `access_token`, `refresh_token`, `cookie`. Keys are matched recursively and exactly. Free-text secrets, alternate key names and personal data are not automatically identified. Review recordings before committing them. Returned live values are not altered.

`save()` refuses to overwrite by default. Pass `overwrite=True` deliberately to replace a recording.

## Replay

```python
from agentfixture import Replay

replay = Replay.load("recording.json")
result = replay.call("search", {"query": "meeting room"})
replay.assert_consumed()
```

Names, arguments and ordering must match. Redacted arguments match the saved `[REDACTED]` placeholder, not the original secret. Do not use this placeholder matching to test authentication behavior. Use synthetic credentials for those tests.

`acall()` is available for async test code. Timeouts raise `TimeoutError`; other recorded errors raise `RuntimeError` with the saved error type. Replay does not reproduce actual elapsed time, real network state, concurrent schedules or live model nondeterminism.

## pytest

Installing the `pytest` extra registers these fixtures: `agent_recorder`, `agent_replay` (the Replay class) and `assert_agent_trace`.

```python
def test_no_booking_without_dates(agent_recorder, assert_agent_trace):
    agent_recorder.call("rooms.search", {}, lambda: ["A"])
    assert_agent_trace(agent_recorder.calls, {"forbidden_calls": ["bookings.create"]})
```

No plugin is required to use `assert_trace()` in an ordinary test function.

## CLI and CI

```shell
agentfixture check examples --json reports/results.json --html reports/results.html --junit reports/results.xml
```

Directory mode recursively reads every JSON file. Keep report output outside the scenario directory. Exit codes: `0` all assertions pass; `1` assertion failures; `2` malformed inputs or I/O failure. `examples/fail.json` deliberately fails. Reports contain names and failure details, so redact test inputs appropriately. HTML reports do not load remote assets.

## Development

`python -m pip install -e ".[dev]"` then `python -m pytest`. See [CONTRIBUTING](../CONTRIBUTING.md).
