"""Deterministic assertions and strict, sequential tool replay."""

import copy
import json
from collections import Counter


class FixtureMismatch(AssertionError):
    pass


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False)


def validate_calls(calls):
    if not isinstance(calls, list):
        raise ValueError("calls must be an array")
    for i, call in enumerate(calls):
        if (
            not isinstance(call, dict)
            or not isinstance(call.get("name"), str)
            or not call["name"]
        ):
            raise ValueError(f"calls[{i}].name must be a nonempty string")
        if "arguments" in call and not isinstance(call["arguments"], dict):
            raise ValueError(f"calls[{i}].arguments must be an object")
        canonical(call)


class Replay:
    def __init__(self, fixtures):
        validate_calls(fixtures)
        self.fixtures = copy.deepcopy(fixtures)
        self.calls = []
        self.position = 0

    @classmethod
    def load(cls, path):
        from pathlib import Path

        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(data["calls"] if isinstance(data, dict) else data)

    def call(self, name, arguments):
        if self.position >= len(self.fixtures):
            raise FixtureMismatch(f"Unexpected call: {name}")
        expected = self.fixtures[self.position]
        if name != expected["name"] or canonical(arguments) != canonical(
            expected.get("arguments", {})
        ):
            raise FixtureMismatch(
                f"Call {self.position + 1}: expected {expected['name']} {canonical(expected.get('arguments', {}))}; got {name} {canonical(arguments)}"
            )
        self.position += 1
        self.calls.append({"name": name, "arguments": copy.deepcopy(arguments)})
        if expected.get("error") == "timeout":
            raise TimeoutError("Simulated tool timeout")
        if "error" in expected:
            raise RuntimeError(str(expected["error"]))
        return copy.deepcopy(expected.get("result"))

    async def acall(self, name, arguments):
        return self.call(name, arguments)

    def assert_consumed(self):
        if self.position != len(self.fixtures):
            raise FixtureMismatch(
                f"{len(self.fixtures) - self.position} fixture(s) not consumed"
            )


def check(calls, expectations):
    validate_calls(calls)
    allowed = {
        "forbidden_calls",
        "required_calls",
        "counts",
        "order",
        "arguments",
        "max_calls",
    }
    if not isinstance(expectations, dict) or set(expectations) - allowed:
        raise ValueError("expect must be an object containing supported rules only")
    for field in ("forbidden_calls", "required_calls", "order"):
        if field in expectations and (
            not isinstance(expectations[field], list)
            or any(not isinstance(x, str) or not x for x in expectations[field])
        ):
            raise ValueError(f"{field} must be an array of tool names")
    counts_rule = expectations.get("counts", {})
    if not isinstance(counts_rule, dict):
        raise ValueError("counts must be an object")
    for name, number in counts_rule.items():
        if not isinstance(name, str) or type(number) is not int or number < 0:
            raise ValueError("counts values must be nonnegative integers")
    argument_rules = expectations.get("arguments", {})
    if not isinstance(argument_rules, dict) or any(
        not isinstance(x, dict) for x in argument_rules.values()
    ):
        raise ValueError("arguments must map tool names to exact argument objects")
    maximum = expectations.get("max_calls")
    if maximum is not None and (type(maximum) is not int or maximum < 0):
        raise ValueError("max_calls must be a nonnegative integer")
    names = [call["name"] for call in calls]
    counts = Counter(names)
    failures = []
    for name in expectations.get("forbidden_calls", []):
        if counts[name]:
            failures.append(f"Forbidden tool called: {name}")
    for name in expectations.get("required_calls", []):
        if not counts[name]:
            failures.append(f"Required tool not called: {name}")
    for name, expected in counts_rule.items():
        if counts[name] != expected:
            failures.append(f"{name}: expected {expected} call(s), got {counts[name]}")
    if "order" in expectations and names != expectations["order"]:
        failures.append(f"Wrong call order: {names}")
    if maximum is not None and len(calls) > maximum:
        failures.append(f"Tool call budget exceeded: {len(calls)} > {maximum}")
    for name, args in argument_rules.items():
        matched = [call for call in calls if call["name"] == name]
        if not matched:
            failures.append(f"No call available to check arguments: {name}")
        for call in matched:
            if canonical(call.get("arguments", {})) != canonical(args):
                failures.append(f"{name}: arguments differ from {canonical(args)}")
    return failures


def assert_trace(calls, expectations):
    failures = check(calls, expectations)
    if failures:
        raise FixtureMismatch("\n".join(failures))
