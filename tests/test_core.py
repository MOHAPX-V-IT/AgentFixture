import unittest
from agentfixture.core import Replay, FixtureMismatch, check


class Tests(unittest.TestCase):
    def test_missing_dates_forbids_booking(self):
        self.assertEqual(check([], {"forbidden_calls": ["book"]}), [])
        self.assertTrue(check([{"name": "book"}], {"forbidden_calls": ["book"]}))

    def test_duplicate_and_order(self):
        self.assertEqual(
            len(
                check(
                    [{"name": "book"}, {"name": "book"}],
                    {"counts": {"book": 1}, "order": ["search", "book"]},
                )
            ),
            2,
        )

    def test_replay_arguments_and_copy(self):
        replay = Replay(
            [{"name": "search", "arguments": {"id": 1}, "result": {"items": []}}]
        )
        with self.assertRaises(FixtureMismatch):
            replay.call("search", {"id": True})
        with self.assertRaises(FixtureMismatch):
            replay.assert_consumed()
        result = replay.call("search", {"id": 1})
        result["items"].append(4)
        self.assertEqual(replay.fixtures[0]["result"]["items"], [])
        replay.assert_consumed()
        with self.assertRaises(FixtureMismatch):
            replay.call("search", {"id": 1})

    def test_failures(self):
        for error, exception in [
            ("timeout", TimeoutError),
            ("unavailable", RuntimeError),
        ]:
            replay = Replay([{"name": "search", "arguments": {}, "error": error}])
            with self.assertRaises(exception):
                replay.call("search", {})
            replay.assert_consumed()

    def test_unknown_rule_is_not_silently_ignored(self):
        with self.assertRaises(ValueError):
            check([], {"forbiden_calls": ["book"]})
