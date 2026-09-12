"""Reproduce the same lookup and harness path without the browser."""

import argparse
import json

from find_rpt.harness import execute, prepare, read_run
from find_rpt.reports import lookup

parser = argparse.ArgumentParser(
    description="Find a report; optionally execute the real Claude Code skill."
)
parser.add_argument("ticker")
parser.add_argument("date", help="Filename date in YYYY-MM-DD format")
parser.add_argument("broker")
parser.add_argument("--analyze", action="store_true")
parser.add_argument("--report-id", help="Explicit file choice for ambiguous lookup or manual review")
parser.add_argument("--confirm-selection", action="store_true", help="Confirm a reviewed file whose cover ticker is unverified; requires --report-id")
parser.add_argument("--question", default="")
parser.add_argument("--model", choices=["opus", "sonnet", "haiku"])
parser.add_argument("--effort", choices=["low", "medium", "high"])
parser.add_argument("--parent-id", help="Saved run ID for follow-up context")
args = parser.parse_args()
try:
    if args.confirm_selection and not args.report_id:
        raise ValueError("Manual confirmation requires an explicit --report-id.")
    found = lookup(args.ticker, args.date, args.broker, report_id=args.report_id)
    if not args.analyze:
        print(json.dumps(found, indent=2))
    else:
        choices = [
            c
            for c in found["candidates"] + (found["review_candidates"] if args.report_id and (args.confirm_selection or args.parent_id) else [])
            if not args.report_id or c["id"] == args.report_id
        ]
        if len(choices) != 1:
            raise ValueError(
                "Analysis needs one selected file. Run lookup first; use --report-id for ambiguity, or add --confirm-selection after reviewing an unverified file."
            )
        run_id = prepare(
            choices[0]["id"],
            choices[0]["ticker"],
            args.question,
            args.parent_id,
            model=args.model,
            effort=args.effort,
            confirm_selection=args.confirm_selection,
        )
        print(
            f"Running Claude Code skill. Local evidence: local/runs/{run_id}",
            flush=True,
        )
        state = execute(run_id)
        print(json.dumps(read_run(run_id), indent=2))
        if state["status"] != "complete":
            raise SystemExit(1)
except (ValueError, FileNotFoundError) as exc:
    parser.exit(2, f"{exc}\n")
