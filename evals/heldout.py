"""Frozen, selected-only evaluation through the unchanged product API.

Prepare reads selection metadata only. Each invoke is an exclusive, single-case
attempt; lookup failure is terminal. Run in a separate process, never the app server.
"""

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import app as web
from find_rpt import harness, reports

BASE = ROOT / "local/iteration-05-development"
EVALUATION = BASE / "heldout"
FREEZE = BASE / "product-freeze.json"
SPLIT = ROOT / "local/split.json"
CORPUS = ROOT / "corpus"
BROKERS = (
    "Bestinver Securities", "CIC Corporate & Institutional Banking",
    "Goldman Sachs", "Jefferies",
)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text())


def save(path, value):
    harness.save(path, value)


def verify_freeze():
    if sha(FREEZE) != FREEZE.with_suffix(".sha256").read_text().strip():
        raise ValueError("Product freeze identity changed.")
    frozen = load(FREEZE)
    for name, digest in frozen["product_files_sha256"].items():
        if sha(ROOT / name) != digest:
            raise ValueError(f"Frozen product file changed: {name}")
    if sha(SPLIT) != frozen["production_split_sha256"]:
        raise ValueError("Original split changed.")
    return frozen


def selected_rows():
    rows = load(SPLIT)["reports"]
    selected = []
    for broker in BROKERS:
        candidates = sorted(
            (r for r in rows if r["split"] == "acceptance" and r["broker"] == broker),
            key=lambda r: r["file"],
        )
        if not candidates:
            raise ValueError(f"No reserved report for {broker}.")
        selected.append(candidates[0])
    return selected


def prepare(identities_path):
    verify_freeze()
    identities = load(identities_path)
    if not isinstance(identities, list) or len(identities) != 4:
        raise ValueError("Supply exactly four report_id/ticker objects.")
    for item in identities:
        fields = {"report_id", "ticker"}
        if item.get("ticker") is None:
            fields.add("query_unavailable_reason")
            if not isinstance(item.get("query_unavailable_reason"), str) or not item["query_unavailable_reason"].strip():
                raise ValueError("A null query needs an explicit availability reason.")
        if set(item) != fields:
            raise ValueError("Selection accepts query identities/reasons only, never review expectations.")
    queries = {item["report_id"]: item for item in identities}
    tickers = {rid: reports.normalize_ticker(item["ticker"]) if item["ticker"] is not None else None
               for rid, item in queries.items()}
    rows = selected_rows()
    if len(tickers) != 4 or set(tickers) != {r["sha256"][:16] for r in rows}:
        raise ValueError("Identities differ from the frozen filename selection rule.")
    EVALUATION.mkdir(parents=True, exist_ok=False)
    selection = {
        "rule": "First filename-sorted reserved report from each named broker; no substitution.",
        "freeze_sha256": sha(FREEZE), "production_split_sha256": sha(SPLIT),
        "identities_file_sha256": sha(identities_path),
        "runner_sha256": sha(Path(__file__)),
        "prepared_at": datetime.now(timezone.utc).isoformat(),
        "cases": [dict(original_row=r, report_id=r["sha256"][:16], ticker=tickers[r["sha256"][:16]],
                       query_unavailable_reason=queries[r["sha256"][:16]].get("query_unavailable_reason"))
                  for r in rows],
    }
    save(EVALUATION / "selection.json", selection)
    (EVALUATION / "selection.sha256").write_text(sha(EVALUATION / "selection.json") + "\n")
    return {"prepared_cases": len(rows), "selection_sha256": sha(EVALUATION / "selection.json")}


@contextmanager
def isolated_view(directory, config, row):
    original = (reports.LOCAL, reports.CORPUS, harness.RUNS, web.RUNS, web.worker.submit)
    original_inventory = reports.inventory, web.inventory
    environment = {key: os.environ.get(key) for key in ["FIND_RPT_TIMEOUT", "FIND_RPT_CLAUDE"]}
    reports.LOCAL, reports.CORPUS = directory, CORPUS
    # Evaluation owns its frozen selection; ordinary discovery has no split dependency.
    reports.inventory = web.inventory = lambda: [dict(row, id=row["sha256"][:16])]
    harness.RUNS = web.RUNS = directory / "runs"
    web.worker.submit = lambda fn, *args: fn(*args)
    os.environ["FIND_RPT_TIMEOUT"] = str(config["timeout_seconds"])
    os.environ["FIND_RPT_CLAUDE"] = config["harness_executable"]
    reports._extract.cache_clear()
    try:
        yield web.app.test_client()
    finally:
        reports.LOCAL, reports.CORPUS, harness.RUNS, web.RUNS, web.worker.submit = original
        reports.inventory, web.inventory = original_inventory
        reports._extract.cache_clear()
        for key, value in environment.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def invoke(report_id):
    frozen = verify_freeze()
    selection_path = EVALUATION / "selection.json"
    if sha(selection_path) != (EVALUATION / "selection.sha256").read_text().strip():
        raise ValueError("Frozen selection changed.")
    selection = load(selection_path)
    if selection["freeze_sha256"] != sha(FREEZE):
        raise ValueError("Selection belongs to a different product freeze.")
    if selection["runner_sha256"] != sha(Path(__file__)):
        raise ValueError("Evaluation runner changed after selection was frozen.")
    case = next((c for c in selection["cases"] if c["report_id"] == report_id), None)
    if case is None:
        raise ValueError("Report is outside the four selected cases.")
    row = case["original_row"]
    if Path(row["file"]).name != row["file"] or row not in selected_rows():
        raise ValueError("Original selection metadata differs.")
    directory = EVALUATION / "cases" / report_id
    directory.mkdir(parents=True, exist_ok=True)
    lock = EVALUATION / "evaluation.lock"
    # A concurrent/crashed attempt fails closed; never delete another process's lock.
    with lock.open("x") as stream:
        stream.write(report_id + "\n")
    try:
        # The marker is permanent, including lookup and preflight failures.
        with (directory / "attempt.json").open("x") as stream:
            json.dump({"report_id": report_id, "started_at": datetime.now(timezone.utc).isoformat(),
                       "maximum_product_invocations": 1, "automatic_retry": False}, stream)
        return run_case(case, directory, frozen)
    finally:
        lock.unlink()


def run_case(case, directory, frozen):
    row, config = case["original_row"], frozen["config"]
    start = time.monotonic()
    summary = {
        "report_id": case["report_id"], "ticker": case["ticker"], "broker": row["broker"],
        "status": "running", "active_stage": "integrity", "lookup_attempted": False, "product_requests": 0,
        "model_invocations": 0, "estimated_cost_usd": 0,
        "freeze_sha256": sha(FREEZE), "selection_sha256": sha(EVALUATION / "selection.json"),
        "runner_sha256": sha(Path(__file__)), "original_report_sha256": row["sha256"],
        "original_split": row["split"], "requested_config": config,
    }
    save(directory / "summary.json", summary)
    try:
        if sha(CORPUS / row["file"]) != row["sha256"]:
            raise ValueError("Original selected PDF hash differs.")
        if case["ticker"] is None:
            summary.update(status="query_unavailable", active_stage="query_availability",
                           query_unavailable_reason=case["query_unavailable_reason"])
        else:
            # Only this process's inventory view changes; the original split stays acceptance.
            save(directory / "split.json", {
                "evaluation_only": True, "original_split_sha256": sha(SPLIT),
                "reports": [dict(row, original_split=row["split"])],
            })
            with isolated_view(directory, config, row) as client:
                date = f"{row['date'][:4]}-{row['date'][4:6]}-{row['date'][6:]}"
                summary.update(active_stage="lookup", lookup_attempted=True)
                lookup = client.post("/api/lookup", json={"ticker": case["ticker"], "date": date, "broker": row["broker"]})
                save(directory / "lookup.json", {"http_status": lookup.status_code, "body": lookup.json})
                if (lookup.status_code != 200 or lookup.json.get("status") != "match"
                        or [r["id"] for r in lookup.json.get("candidates", [])] != [case["report_id"]]):
                    summary.update(status="lookup_failed", error="Normal product lookup did not return the selected subject.")
                else:
                    summary.update(active_stage="product_api", product_requests=1)
                    response = client.post("/api/runs", json={
                        "report_id": case["report_id"], "ticker": case["ticker"],
                        "model": config["model"], "effort": config["effort"],
                    })
                    save(directory / "api-response.json", {"http_status": response.status_code, "body": response.json})
                    if response.status_code != 202:
                        summary.update(status="preflight_failed", error="Product API rejected the case.")
                    else:
                        rid = response.json["id"]
                        state = load(directory / "runs" / rid / "status.json")
                        summary.update(run_id=rid, **{key: state.get(key) for key in [
                            "status", "active_stage", "error", "elapsed_seconds", "main_word_count",
                            "estimated_cost_usd", "effective_models", "effective_effort", "usage", "stages",
                        ]})
                        stage = state.get("stages", {}).get("extraction", {})
                        summary["model_invocations"] = 1 if "returncode" in stage else (None if stage else 0)
                        summary["invocation_note"] = "A returned CLI process confirms one invocation; unavailable execution remains null, never assumed successful."
        verify_freeze()
        summary["preservation"] = {
            "product_freeze_matches": True, "original_split_sha256": sha(SPLIT),
            "original_report_sha256": sha(CORPUS / row["file"]),
        }
        if summary["preservation"]["original_report_sha256"] != row["sha256"]:
            raise ValueError("Original selected PDF changed during evaluation.")
    except Exception as exc:
        summary.update(status="failed", error=str(exc))
    finally:
        summary["total_elapsed_seconds"] = round(time.monotonic() - start, 3)
        save(directory / "summary.json", summary)
    return {key: summary.get(key) for key in [
        "report_id", "ticker", "status", "active_stage", "lookup_attempted", "run_id", "model_invocations",
        "query_unavailable_reason",
        "elapsed_seconds", "total_elapsed_seconds", "main_word_count", "estimated_cost_usd", "error",
    ]}


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["prepare", "invoke"])
    parser.add_argument("value", help="Identity JSON path for prepare; selected report ID for invoke")
    args = parser.parse_args()
    result = prepare(Path(args.value)) if args.action == "prepare" else invoke(args.value)
    print(json.dumps(result, indent=2))
