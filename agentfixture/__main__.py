import argparse
import json
import sys
from pathlib import Path
from .core import check
from .reports import render, junit


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] not in ("check", "init", "-h", "--help", "--version"):
        argv.insert(0, "check")  # v0.1 compatibility
    parser = argparse.ArgumentParser(
        description="Record tools. Replay fixtures. Catch agent regressions."
    )
    parser.add_argument("--version", action="version", version="AgentFixture 0.2.0")
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init", help="Create a runnable synthetic scenario")
    init.add_argument("path", type=Path, nargs="?", default=Path("scenario.json"))
    run = sub.add_parser("check", help="Check one file or a directory of scenarios")
    run.add_argument("path", type=Path)
    run.add_argument("--json", dest="json_path", type=Path)
    run.add_argument("--html", type=Path)
    run.add_argument("--junit", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            sample = {
                "version": 1,
                "calls": [
                    {
                        "name": "rooms.search",
                        "arguments": {"capacity": 4},
                        "result": ["room-1"],
                    }
                ],
                "expect": {
                    "required_calls": ["rooms.search"],
                    "forbidden_calls": ["bookings.create"],
                    "max_calls": 1,
                },
            }
            args.path.parent.mkdir(parents=True, exist_ok=True)
            with args.path.open("x", encoding="utf-8") as out:
                json.dump(sample, out, indent=2)
            print(f"Created {args.path}")
            return 0
        files = sorted(args.path.rglob("*.json")) if args.path.is_dir() else [args.path]
        if not files:
            raise ValueError("No JSON scenarios found")
        results = []
        for path in files:
            row = {
                "name": str(path.relative_to(args.path))
                if args.path.is_dir()
                else path.name,
                "failures": [],
            }
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(data, dict) or data.get("version", 1) != 1:
                    raise ValueError("Unsupported scenario format")
                row["failures"] = check(data["calls"], data["expect"])
            except (OSError, ValueError, KeyError, TypeError) as exc:
                row["error"] = str(exc)
            results.append(row)
            status = (
                "INVALID" if row.get("error") else "FAIL" if row["failures"] else "PASS"
            )
            print(f"{status:7} {row['name']}")
            for failure in [row["error"]] if row.get("error") else row["failures"]:
                print(f"        {failure}")
        outputs = [p.resolve() for p in (args.json_path, args.html, args.junit) if p]
        if len(set(outputs)) != len(outputs):
            raise ValueError("Report paths must be different")
        if set(outputs) & {p.resolve() for p in files}:
            raise ValueError("Report cannot overwrite an input scenario")
        for output, content in [
            (args.json_path, json.dumps(results, indent=2)),
            (args.html, render(results)),
            (args.junit, junit(results)),
        ]:
            if output:
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_text(content, encoding="utf-8")
        if any(r.get("error") for r in results):
            return 2
        return int(any(r["failures"] for r in results))
    except (OSError, ValueError) as exc:
        parser.exit(2, f"Error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
