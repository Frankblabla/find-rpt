"""Model-free commands used by the native /find-rpt conversation."""

import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen
import uuid

from find_rpt import cases, reports
from find_rpt.render import base_url


def serve():
    def ready():
        try:
            with urlopen(base_url() + "/api/case-viewer", timeout=1) as response:
                return json.load(response).get("case_viewer") == 1
        except (URLError, TimeoutError):
            return False

    if ready():
        return dict(url=base_url(), already_running=True)
    reports.LOCAL.mkdir(parents=True, exist_ok=True)
    with (reports.LOCAL / "case-viewer.log").open("a") as log:
        process = subprocess.Popen(
            [sys.executable, str(reports.ROOT / "app.py")],
            cwd=reports.ROOT,
            stdout=log,
            stderr=log,
            start_new_session=True,
        )
    for _ in range(20):
        if ready():
            return dict(url=base_url(), pid=process.pid)
        if process.poll() is not None:
            break
        time.sleep(0.2)
    raise ValueError(
        "Viewer could not start. Inspect local/case-viewer.log; an older app may occupy the port. No process was killed."
    )


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    commands = p.add_subparsers(dest="command", required=True)
    for name in ["lookup", "start"]:
        c = commands.add_parser(name)
        for field in ["ticker", "date", "broker"]:
            c.add_argument(field)
        c.add_argument("--report-id")
        if name == "start":
            c.add_argument("--confirm-selection", action="store_true")
            c.add_argument("--session")
    for name in [
        "context",
        "read",
        "publish",
        "checkpoint",
        "deliver",
        "answer",
        "render",
        "amend",
        "draft",
        "attach",
    ]:
        c = commands.add_parser(name)
        c.add_argument("--case")
        c.add_argument("--session")
        if name in {"publish", "checkpoint", "render", "amend", "draft"}:
            c.add_argument("--base-version", type=int, required=True)
        if name in {"publish", "checkpoint", "answer"}:
            c.add_argument("--file", type=Path, required=True)
        if name in {"amend", "draft"}:
            c.add_argument("--answer", type=int, required=True)
        if name == "render":
            c.add_argument(
                "--years", nargs="*", help="Exact periods; empty resets the filter"
            )
            c.add_argument("--detail", choices=["compact", "full"])
        if name == "read":
            c.add_argument("--report-id")
            selector = c.add_mutually_exclusive_group(required=True)
            selector.add_argument("--refs", nargs="+")
            selector.add_argument("--query")
            selector.add_argument("--page", type=int)
    commands.add_parser("serve")
    return p


def run(a):
    if a.command == "lookup":
        return reports.lookup(a.ticker, a.date, a.broker, report_id=a.report_id)
    if a.command == "start":
        return cases.start(
            a.ticker, a.date, a.broker, a.report_id, a.confirm_selection, a.session
        )
    if a.command == "serve":
        return serve()
    if a.command == "read" and a.report_id and not a.case:
        return cases.read_sources(
            report_id=a.report_id, refs=a.refs, query=a.query, page=a.page
        )
    case_id = cases.resolve(a.case, a.session)
    if a.command == "attach":
        if not a.session:
            raise ValueError("Attach requires --session.")
        cases.attach(case_id, a.session)
        return cases.context(case_id)
    if a.command == "context":
        return cases.context(case_id)
    if a.command == "read":
        return cases.read_sources(
            case_id=case_id, refs=a.refs, query=a.query, page=a.page
        )
    if a.command == "publish":
        return cases.publish(case_id, a.file, a.base_version)
    if a.command == "checkpoint":
        return cases.checkpoint(case_id, a.file, a.base_version)
    if a.command == "deliver":
        return cases.deliver(case_id)
    if a.command == "answer":
        return cases.save_answer(case_id, a.file)
    if a.command == "render":
        return cases.rerender(case_id, a.base_version, a.years, a.detail)
    return cases.revise(case_id, a.answer, a.base_version, draft=a.command == "draft")


def main():
    args = parser().parse_args()
    event = dict(id=uuid.uuid4().hex, time=cases.now(), arguments=vars(args))
    if getattr(args, "file", None) and args.file.is_file():
        event["input_text"] = args.file.read_text()
    try:
        result = run(args)
        event.update(
            status="complete",
            result=result
            if args.command not in {"read", "context", "lookup", "start"}
            else "See native session output",
        )
        print(json.dumps(result, indent=2, ensure_ascii=False))
        code = 0
    except (ValueError, FileNotFoundError) as exc:
        event.update(status="failed", error=str(exc))
        failure = {"error": str(exc)}
        if getattr(args, "case", None) or getattr(args, "session", None):
            try:
                failure["delivery"] = cases.deliver(
                    cases.resolve(
                        getattr(args, "case", None), getattr(args, "session", None)
                    )
                )
            except (ValueError, FileNotFoundError):
                pass
        event["result"] = failure
        print(json.dumps(failure, ensure_ascii=False))
        code = 2
    finally:
        folder = reports.LOCAL / "case-tool-events"
        folder.mkdir(parents=True, exist_ok=True)
        (folder / (event["id"] + ".json")).write_text(
            json.dumps(event, indent=2, ensure_ascii=False, default=str) + "\n"
        )
    return code


if __name__ == "__main__":
    raise SystemExit(main())
