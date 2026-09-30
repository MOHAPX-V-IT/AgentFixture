import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from agentfixture import Recorder, Replay, check
from agentfixture.__main__ import main


class RecordingTests(unittest.TestCase):
    def test_round_trip_and_no_mutation(self):
        recorder = Recorder()
        args = {"id": 7}
        self.assertEqual(
            recorder.call("lookup", args, lambda id: {"id": id}), {"id": 7}
        )
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "case.json"
            recorder.save(path, expect={"counts": {"lookup": 1}})
            self.assertEqual(Replay.load(path).call("lookup", args), {"id": 7})
            self.assertEqual(
                main(["check", str(path), "--junit", str(Path(temp) / "result.xml")]), 0
            )
            with self.assertRaises(FileExistsError):
                recorder.save(path)

    def test_redacts_nested_keys_and_exception_text(self):
        recorder = Recorder(redact_keys=["email"])
        result = recorder.call(
            "login",
            {"token": "secret"},
            lambda token: {"nested": [{"email": "private"}]},
        )
        self.assertEqual(result["nested"][0]["email"], "private")
        self.assertNotIn("secret", json.dumps(recorder.calls))
        self.assertNotIn("private", json.dumps(recorder.calls))

        def broken():
            raise ValueError("SENSITIVE")

        with self.assertRaises(ValueError):
            recorder.call("broken", {}, broken)
        self.assertNotIn("SENSITIVE", json.dumps(recorder.calls))

    def test_async(self):
        async def run():
            recorder = Recorder()

            async def lookup(id):
                return id + 1

            self.assertEqual(await recorder.acall("lookup", {"id": 1}, lookup), 2)
            self.assertEqual(await Replay(recorder.calls).acall("lookup", {"id": 1}), 2)

        asyncio.run(run())

    def test_malformed_and_rules(self):
        for calls, rules in [
            (None, {}),
            ([], {"counts": []}),
            ([], {"forbidden_calls": "book"}),
            ([], {"max_calls": True}),
        ]:
            with self.assertRaises(ValueError):
                check(calls, rules)
        self.assertTrue(
            check(
                [{"name": "book", "arguments": {"id": 2}}],
                {"arguments": {"book": {"id": 1}}},
            )
        )

    def test_cli_invalid_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "case.json"
            main(["init", str(path)])
            with self.assertRaises(SystemExit):
                main(["init", str(path)])
            path.write_text("{}")
            self.assertEqual(main(["check", str(path)]), 2)

    def test_report_paths_validated_before_any_write(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "scenario.json"
            main(["init", str(path)])
            original = path.read_bytes()
            report = Path(temp) / "report.json"
            with self.assertRaises(SystemExit):
                main(["check", str(path), "--json", str(report), "--html", str(path)])
            self.assertEqual(path.read_bytes(), original)
            self.assertFalse(report.exists())
            with self.assertRaises(SystemExit):
                main(["check", str(path), "--json", str(report), "--html", str(report)])
