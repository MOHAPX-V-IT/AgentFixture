![AgentFixture: record, replay, catch regressions](assets/preview.png)

# AgentFixture

**Catch the wrong tool call before your agent reaches production.**

Record real tool interactions, replay them offline, and check exactly what an agent did. Works with ordinary Python functions; no model provider or agent framework required.

[Quick start](#quick-start) · [Usage guide](docs/usage.md) · [Русский](README.ru.md) · [MIT](LICENSE)

- **Record once. Replay offline.** Sync and async callbacks, JSON fixtures and simulated failures.
- **Test behavior.** Forbidden calls, exact arguments, ordering, counts and call budgets.
- **Plug into CI.** Run a scenario directory and export HTML, JSON or JUnit.
- **Use pytest.** Optional recorder, replay and assertion fixtures.

## Quick start

Python 3.11+. Run from the cloned repository; no runtime dependencies required.

```shell
python -m agentfixture init demo.json
python -m agentfixture check demo.json --html reports/demo.html
python -m agentfixture check examples --junit reports/results.xml
```

The last command intentionally fails: `examples/fail.json` demonstrates a forbidden booking.

## Test a tool in a few lines

```python
from agentfixture import Recorder, Replay, assert_trace

recorder = Recorder()
recorder.call("rooms.search", {"capacity": 4}, lambda capacity: ["room-1"])
assert_trace(recorder.calls, {"forbidden_calls": ["bookings.create"]})

replay = Replay(recorder.calls)
assert replay.call("rooms.search", {"capacity": 4}) == ["room-1"]
replay.assert_consumed()
```

Install the CLI and pytest fixtures with `python -m pip install -e ".[pytest]"`.

**Scope:** sequential JSON tool interactions. Recording executes your callback; replay does not. Secret-key redaction is a convenience, not a complete privacy filter. Redacted arguments need matching placeholders during replay. Live model outputs are not made deterministic.

Built by [Aleksei Maryshev / MOHAPX-V-IT](https://mohapx-v-it.github.io/mohapx-v-iti/). Contributions welcome. Early release; APIs may change.
