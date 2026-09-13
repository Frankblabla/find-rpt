"""Run a fixed selection through the real native skill, retaining every first attempt.

Selection is a JSON list of ticker/date/broker objects. Optional report_id and
confirm_selection retain a previously confirmed file choice; they are not answers.
All inputs, raw events and summaries stay in the caller's private output directory.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from find_rpt import cases, reports


def save(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def freeze():
    paths = [ROOT / "app.py", ROOT / "pyproject.toml", ROOT / "uv.lock"]
    for directory in ("find_rpt", "templates", "static", ".claude/skills", ".agents/skills"):
        paths += [p for p in (ROOT / directory).rglob("*")
                  if p.is_file() and "__pycache__" not in p.parts]
    return {str(p.relative_to(ROOT)): digest(p) for p in sorted(paths)}


def prompt_for(row):
    prompt = f'/find-rpt "{row["ticker"]}" {row["date"]} "{row["broker"]}"\n\n'
    if row.get("confirm_selection"):
        prompt += (f'The user previously selected report ID {row["report_id"]}; '
                   'use that same explicitly confirmed file for this regression. '
                   'Preserve ambiguous identity if the source cannot establish the ticker.\n')
    prompt += (
        "Start a new case and complete the project skill workflow: partial first read, "
        "full publication, focused source review, then a final handoff with the latest "
        "saved HTML link and actual email outcome. Use only the selected original report. "
        "Do not read prior cases, evaluation records, reviews or submission examples. "
        "Do not change code or instructions. Disclose unresolved limitations. Do not send email."
    )
    return prompt


def invoke(index, row, args, frozen):
    directory = args.output / f"case-{index:02d}"
    directory.mkdir()
    if freeze() != frozen:
        raise ValueError("Product files changed after the batch freeze.")
    if row.get("report_id"):
        reports.report(row["report_id"])
    session = str(uuid.uuid4())
    prompt = prompt_for(row)
    command = [shutil.which("claude"), "-p", "--model", args.model, "--effort", args.effort,
               "--output-format", "stream-json", "--verbose",
               "--tools", "Read,Write,Edit,Bash,Skill",
               "--allowedTools", "Read", "Write", "Edit", "Skill",
               "Bash(uv run python -m find_rpt.tools *)",
               "--setting-sources", "project", "--settings", '{"disableAllHooks":true}',
               "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}',
               "--no-chrome", "--permission-prompts", "none",
               "--max-budget-usd", str(args.budget), "--session-id", session, prompt]
    started = time.time()
    save(directory / "invocation.json", dict(command=command, session=session, input=row,
         started_at=started, budget_usd=args.budget, timeout_seconds=args.timeout))
    env = dict(os.environ, CLAUDE_CODE_DISABLE_AUTO_MEMORY="1")
    timed_out = False
    with (directory / "events.jsonl").open("w") as stdout, (directory / "stderr.txt").open("w") as stderr:
        process = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL,
                                   stdout=stdout, stderr=stderr, env=env)
        try:
            process.wait(timeout=args.timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            process.terminate()
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
    result = {}
    for line in (directory / "events.jsonl").read_text().splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "result":
            result = event
    delivery = {}
    integrity_error = None
    try:
        case_id = cases.resolve(session=session)
        delivery = cases.deliver(case_id)
        _, state = cases.read_case(case_id)
        if row.get("report_id") and state["report_id"] != row["report_id"]:
            raise ValueError("The attempt selected a different PDF.")
        if delivery.get("artifact_status") == "full":
            _, artifact, _ = cases.version(case_id)
            cases.checked_evidence(case_id, artifact["evidence"])
    except (ValueError, FileNotFoundError) as exc:
        integrity_error = str(exc)
    normal = process.returncode == 0 and result.get("subtype") == "success" and not result.get("is_error")
    full = delivery.get("artifact_status") == "full" and integrity_error is None
    handoff = full and normal and delivery["html_url"] in result.get("result", "")
    summary = dict(index=index, input=row, session=session, exit_code=process.returncode,
                   timed_out=timed_out, subtype=result.get("subtype"),
                   full_html=full, completed=bool(full and normal), final_link_present=bool(handoff),
                   elapsed_seconds=round(time.time() - started, 2),
                   estimated_cost_usd=result.get("total_cost_usd"), turns=result.get("num_turns"),
                   model_usage=result.get("modelUsage"), permission_denials=result.get("permission_denials", []),
                   delivery=delivery, integrity_error=integrity_error, final_reply=result.get("result"),
                   product_unchanged=freeze() == frozen)
    save(directory / "summary.json", summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("selection", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--budget", type=float, default=15, help="USD list-cost cap per report")
    parser.add_argument("--timeout", type=int, default=1800)
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--model", default="opus")
    parser.add_argument("--effort", default="high")
    args = parser.parse_args()
    rows = json.loads(args.selection.read_text())
    if not isinstance(rows, list) or not 1 <= len(rows) <= 30:
        parser.error("Select 1 to 30 report attempts.")
    if args.budget <= 0 or args.timeout <= 0 or not 1 <= args.workers <= 4:
        parser.error("Use positive budget/timeout and 1 to 4 workers.")
    for row in rows:
        if not all(row.get(k) for k in ("ticker", "date", "broker")):
            parser.error("Each report requires ticker, date and broker.")
        if row.get("confirm_selection") and not row.get("report_id"):
            parser.error("A confirmed selection requires report_id.")
    args.output = args.output.resolve()
    if not args.output.is_relative_to(reports.LOCAL.resolve()):
        parser.error("Store private evaluation outputs inside ignored local/.")
    if not shutil.which("claude"):
        parser.error("Claude Code is not installed.")
    args.output.mkdir(parents=True, exist_ok=False)
    frozen = freeze()
    save(args.output / "freeze.json", dict(product_files=frozen, selection=rows,
         budget_per_report_usd=args.budget, maximum_list_cost_usd=args.budget * len(rows),
         workers=args.workers, timeout_seconds=args.timeout, automatic_batch_retry=False))
    results = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(invoke, i, row, args, frozen): i for i, row in enumerate(rows, 1)}
        for future in as_completed(futures):
            index = futures[future]
            try:
                result = future.result()
            except Exception as exc:
                result = dict(index=index, input=rows[index-1], full_html=False, completed=False,
                              final_link_present=False, runner_error=str(exc))
                save(args.output / f"case-{index:02d}" / "summary.json", result)
            results.append(result)
            ordered = sorted(results, key=lambda r: r["index"])
            save(args.output / "summary.json", dict(planned=len(rows), finished=len(results),
                 full_html=sum(r["full_html"] for r in results),
                 completed=sum(r["completed"] for r in results),
                 final_links=sum(r["final_link_present"] for r in results),
                 estimated_cost_usd=sum(r.get("estimated_cost_usd") or 0 for r in results),
                 cost_unavailable=sum(r.get("estimated_cost_usd") is None for r in results),
                 product_unchanged=freeze() == frozen, cases=ordered))
            print(json.dumps(dict(index=index, broker=result["input"]["broker"],
                  full_html=result["full_html"], completed=result["completed"],
                  final_link_present=result["final_link_present"],
                  cost=result.get("estimated_cost_usd"))), flush=True)


if __name__ == "__main__":
    main()
