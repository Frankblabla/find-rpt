"""Isolated synthetic email evaluation using the real product API and model.

Prepare freezes ordinary report-like source data. Invoke is explicit, one-shot,
and uses a separate corpus/manifest/run directory in this process only.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

import pymupdf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import app as web
from find_rpt import harness, reports

DIRECTORY = ROOT / "local/iteration-04-development/synthetic-email"
SOURCE = """SYNTHETIC TEST FIXTURE - NOT INVESTMENT RESEARCH
Northbridge Instruments plc - Forecast update
Bloomberg: NBI LN
12 September 2026
Synthetic Research

New equipment orders lift our earnings forecast.
We raise FY2027 EPS from EUR 2.00 to EUR 2.40.
Additional operating earnings from new equipment orders drive this EPS increase.

Forecasts - EUR per share
Metric                         Fiscal year     Previous     Current
EPS                            FY2027          2.00         2.40
Dividend per share             FY2027          1.00         0.60

Alex Morgan - Equity Research Analyst
alex.morgan@example.test
Telephone: +44 20 7946 0958

SYNTHETIC TEST FIXTURE - fictitious issuer and contact details
"""


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def prepare():
    DIRECTORY.mkdir(parents=True, exist_ok=False)
    corpus = DIRECTORY / "corpus"
    corpus.mkdir()
    path = corpus / "20260912_Synthetic Research_fixture.pdf"
    with pymupdf.open() as doc:
        page = doc.new_page(width=660, height=750)
        page.insert_text((40, 50), SOURCE, fontname="cour", fontsize=10)
        doc.set_metadata({"title": "SYNTHETIC TEST FIXTURE - Northbridge Instruments"})
        doc.save(path)
        page.get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5)).save(DIRECTORY / "source.png")
    (DIRECTORY / "source.txt").write_text(SOURCE)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    save(DIRECTORY / "split.json", {"synthetic": True, "reports": [{
        "file": path.name, "date": "20260912", "broker": "Synthetic Research",
        "sha256": digest, "split": "development",
    }]})
    save(DIRECTORY / "fixture.json", {
        "synthetic": True, "report_id": digest[:16], "sha256": digest,
        "ticker": "NBI LN", "pdf": str(path),
        "scope": "Isolated test fixture, not a real issuer or research-accuracy claim.",
    })
    print("Frozen synthetic PDF:", path)


def invoke():
    fixture = json.loads((DIRECTORY / "fixture.json").read_text())
    assert hashlib.sha256(Path(fixture["pdf"]).read_bytes()).hexdigest() == fixture["sha256"]
    # Exclusive marker prevents a repeat even if the model or validation fails.
    with (DIRECTORY / "invocation.json").open("x") as f:
        json.dump({"synthetic": True, "model": "opus", "effort": "high",
                   "maximum_invocations": 1, "automatic_retry": False}, f)
    reports.CORPUS = DIRECTORY / "corpus"
    reports.LOCAL = DIRECTORY
    harness.RUNS = web.RUNS = DIRECTORY / "runs"
    web.worker.submit = lambda fn, *args: fn(*args)
    os.environ["FIND_RPT_TIMEOUT"] = "420"
    client = web.app.test_client()
    response = client.post("/api/runs", json={
        "report_id": fixture["report_id"], "ticker": fixture["ticker"],
        "model": "opus", "effort": "high",
    })
    save(DIRECTORY / "api-response.json", {"http_status": response.status_code, "body": response.json})
    if response.status_code != 202:
        raise RuntimeError(response.json)
    rid = response.json["id"]
    state = client.get(f"/api/runs/{rid}").json
    save(DIRECTORY / "run-reference.json", {"synthetic": True, "run_id": rid, "status": state["status"]})
    if state["status"] != "complete":
        raise RuntimeError(state.get("error", "Synthetic product run failed"))
    result = state["result"]
    b, e = result["brief"], result["evidence"]
    dividend = [r for r in e["estimates"] if "dividend" in r["metric"].lower()]
    eps = [r for r in e["estimates"] if "eps" in r["metric"].lower()]
    draft = b["email_draft"]
    checks = {
        "synthetic_real_model_call": True,
        "main_words_within_220": result["main_word_count"] <= 220,
        "dividend_decrease_unexplained": any(r["old"] == 1 and r["new"] == 0.6 and r["reason"] == "not_stated" for r in dividend),
        "earnings_increase_has_cause": any(r["old"] == 2 and r["new"] == 2.4 and r["reason"] == "stated" and r["reason_fact_ids"] for r in eps),
        "draft_created": draft is not None,
        "no_send_route": not any("send" in r.rule or "email" in r.rule for r in web.app.url_map.iter_rules()),
    }
    if draft:
        questions = [line for line in draft["body"].splitlines() if line[:1].isdigit()]
        checks.update(
            exact_recipient=draft["to"] == "alex.morgan@example.test",
            fixed_sender=draft["body"].endswith("Thank you,\n[Your name]"),
            only_dividend_question=len(questions) == 1 and any(
                f"{r['metric']} ({r['fiscal_year']})" in questions[0] for r in dividend
            ),
            no_send_endpoint=client.post("/api/email/send", json=draft).status_code == 404,
        )
        refs = draft["sources"]
        source_url = f"/source/{fixture['report_id']}?refs={','.join(refs)}"
        source = client.get(source_url)
        selected = reports.source_lines(fixture["report_id"], refs)
        text = "\n".join(line["text"] for line in selected)
        checks["source_route_works"] = source.status_code == 200
        checks["source_highlights_dividend_and_recipient"] = all(
            value in text for value in ["Dividend per share", "FY2027", "1.00", "0.60", "Alex Morgan", "alex.morgan@example.test"]
        )
        save(DIRECTORY / "draft.json", {"synthetic": True, **draft})
        (DIRECTORY / "draft.txt").write_text(
            "SYNTHETIC TEST FIXTURE - REAL MODEL OUTPUT - DRAFT ONLY\n\n"
            f"To: {draft['to']}\nSubject: {draft['subject']}\n\n{draft['body']}\n"
        )
        save(DIRECTORY / "source-links.json", {
            "synthetic": True, "route_scope": "Isolated test-client API only",
            "draft_source_url": source_url, "highlighted_lines": selected,
        })
        with pymupdf.open(fixture["pdf"]) as doc:
            for line in selected:
                doc[line["page"] - 1].draw_rect(line["bbox"], color=(0, 0.35, 0.8), width=1)
            doc[0].get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5)).save(DIRECTORY / "draft-evidence.png")
    save(DIRECTORY / "checks.json", checks)
    print(json.dumps({"synthetic": True, "run_id": rid, "main_words": result["main_word_count"], "checks": checks}, indent=2))
    if not all(checks.values()):
        raise RuntimeError("Synthetic acceptance check failed; original output retained.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["prepare", "invoke"])
    args = parser.parse_args()
    prepare() if args.action == "prepare" else invoke()
