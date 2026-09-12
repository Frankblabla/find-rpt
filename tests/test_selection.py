"""Synthetic selection-contract checks; no corpus evaluation or model calls."""

import json
import hashlib
import runpy
import sys

import pytest

import app as web
from find_rpt import harness, reports
from find_rpt.revalidate import revalidate
from tests.support import LINES, extracted_v3, fake_process, payload


def line(text, n=1, x=60, y=80):
    return dict(id=f"p1l{n}", text=text, bbox=[x, y, x + 80, y + 12])


@pytest.mark.parametrize("label", ["Bloomberg", "BBG", "TICKER"])
def test_supported_inline_and_nearby_labels(label):
    inline = line(f"{label}: ABC LN")
    assert reports.subject_evidence([inline], "ABC LN") == [inline]
    key, value = line(label), line("ABC LN", 2, y=100)
    assert reports.subject_evidence([key, value], "ABC LN") == [key, value]


def test_title_and_incidental_mentions_are_distinct():
    title = line("Example Company (ABC LN)")
    assert reports.subject_evidence([title], "ABC LN") == [title]
    for lines in [
        [line("Our valuation refers to ABC LN")],
        [line("Bloomberg: XABC LN")],
        [line("RIC: ABC.L")],
        [line("Peers"), line("Ticker: ABC LN", 2, y=100)],
        [line("Peer Company (ABC LN)")],
        [line("Example Company (ABC LN)", y=250)],
        [line("Ticker"), line("XYZ LN", 2, y=96), line("ABC LN", 3, y=110)],
        [line("Ticker"), line("ABC LN", 2, y=150)],
    ]:
        assert reports.subject_evidence(lines, "ABC LN") == []


def test_same_baseline_value_precedes_nearer_vertical_footnote():
    key = line("TICKER")
    value = line("ABC LN", 2, x=192, y=80.14)
    footnote = line("Additional information", 3, y=92)
    assert reports.subject_evidence([key, value, footnote], "ABC LN") == [key, value]
    other = line("XYZ LN", 2, x=192, y=80.14)
    assert reports.subject_evidence([key, other, line("ABC LN", 3, y=92)], "ABC LN") == []


def test_inventory_is_metadata_only_and_selected_preflight_opens_only_selected(corpus, monkeypatch):
    selected = corpus("20260511_Test_a.pdf", "TICKER: ABC LN", "acceptance")
    corpus("20260511_Test_b.pdf", "TICKER: XYZ LN", "acceptance")
    corpus("20260528_Test_c.pdf", "TICKER: DEF LN", "acceptance")
    original = reports.pymupdf.open
    opened = []

    def guarded(path, *args, **kwargs):
        assert str(path).endswith("20260511_Test_a.pdf")
        opened.append(str(path))
        return original(path, *args, **kwargs)

    monkeypatch.setattr(reports.pymupdf, "open", guarded)
    assert len(reports.inventory()) == 3
    assert web.app.test_client().get("/api/catalog").json["total"] == 3
    assert not opened
    selected_info = reports.select_report(selected, "ABC LN")
    assert selected_info["method"] == "cover_identifier"
    assert selected_info["cover_sources"] == ["p1l1"] and len(opened) == 1


def test_api_manual_confirmation_is_strict_and_spoofed_provenance_is_ignored(corpus, monkeypatch):
    rid = corpus("20260511_Test_a.pdf", "Example Company\nRIC: ABC.L", "acceptance")
    dispatched = []
    monkeypatch.setattr(web.worker, "submit", lambda *args: dispatched.append(args))
    client = web.app.test_client()
    found = client.post("/api/lookup", json={"ticker": "ABC LN", "date": "2026-05-11", "broker": "Test"}).json
    assert found["candidates"] == [] and found["review_candidates"][0]["id"] == rid
    base = {"report_id": rid, "ticker": "ABC LN", "selection": {"method": "cover_identifier"}}
    for confirm in [None, False, "true", 1, {"confirmed": True}]:
        response = client.post("/api/runs", json=dict(base, confirm_selection=confirm))
        assert response.status_code == 400 and "explicitly confirm" in response.json["error"]
    assert not dispatched and not harness.RUNS.exists()
    response = client.post("/api/runs", json=dict(base, confirm_selection=True))
    assert response.status_code == 202 and len(dispatched) == 1
    saved = json.loads((harness.run_directory(response.json["id"]) / "request.json").read_text())
    assert saved["selection"]["method"] == "user_confirmed"
    assert saved["selection"]["cover_sources"] == []
    assert saved["selection"]["original_split"] == "acceptance"
    assert saved["selection"]["report_sha256"] == reports.report(rid)[0]["sha256"]


@pytest.mark.parametrize("manual,assessment,expected", [
    (False, "confirmed", "complete"),
    (False, "ambiguous", "failed"),
    (True, "ambiguous", "complete"),
    (True, "confirmed", "complete"),
    (False, "mismatch", "failed"),
    (True, "mismatch", "failed"),
])
def test_subject_assessment_preserved_and_mismatch_blocks_composition(corpus, monkeypatch, manual, assessment, expected):
    lines = dict(LINES)
    if manual:
        lines["p1l1"] = "Example Company; identifier not printed"
    rid = corpus("20260511_Test_a.pdf", "\n".join(lines.values()))
    e = extracted_v3()
    e.subject_match = assessment
    for quote in e.quotes:
        quote.text = lines[quote.line_id]
    calls = fake_process(monkeypatch, [payload(e.model_dump())])
    run = harness.prepare(rid, "ABC LN", confirm_selection=manual)
    state = harness.execute(run)
    directory = harness.run_directory(run)
    assert state["status"] == expected, state.get("error")
    assert len(calls) == 1 and (directory / "extraction/harness-output.json").exists()
    assert (directory / "result.json").exists() == (expected == "complete")
    assert (directory / "composition/status.json").exists() == (expected == "complete")
    if expected == "complete":
        result = harness.read_run(run)["result"]
        assert result["brief"]["subject_match"] == assessment
        if manual:
            assert result["request"]["selection"]["method"] == "user_confirmed"


def test_manual_followup_inherits_only_completed_same_report_and_ticker(corpus):
    rid = corpus("20260511_Test_a.pdf", "Example Company")
    other = corpus("20260511_Test_b.pdf", "Other Company")
    parent = harness.prepare(rid, "ABC LN", confirm_selection=True)
    with pytest.raises(ValueError, match="completed parent"):
        harness.prepare(rid, "ABC LN", "Why?", parent)
    harness.save(harness.run_directory(parent) / "status.json", {"status": "complete"})
    child = harness.prepare(rid, "abc ln", "Why?", parent)
    request = json.loads((harness.run_directory(child) / "request.json").read_text())
    assert request["selection"]["method"] == "user_confirmed"
    for report_id, ticker in [(other, "ABC LN"), (rid, "XYZ LN")]:
        with pytest.raises(ValueError, match="same selected report and ticker"):
            harness.prepare(report_id, ticker, "Why?", parent)


def test_offline_revalidation_cannot_compose_mismatch_or_rewrite_failed_source(corpus, monkeypatch):
    rid = corpus("20260511_Test_a.pdf", "\n".join(LINES.values()))
    e = extracted_v3()
    e.subject_match = "mismatch"
    calls = fake_process(monkeypatch, [payload(e.model_dump())])
    original = harness.prepare(rid, "ABC LN", confirm_selection=True)
    assert harness.execute(original)["status"] == "failed"
    source = harness.run_directory(original)
    before = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in source.rglob("*") if p.is_file()}
    result = revalidate(original)
    assert result["status"] == "failed" and result["model_invocations"] == 0
    assert "identity" in result["error"] and len(calls) == 1
    assert not (harness.run_directory(result["id"]) / "result.json").exists()
    assert before == {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in source.rglob("*") if p.is_file()}


def test_cli_explicit_confirmation_uses_shared_preflight(corpus, monkeypatch, capsys):
    rid = corpus("20260511_Test_a.pdf", "Example Company", "acceptance")
    executed = []
    monkeypatch.setattr(harness, "execute", lambda run: executed.append(run) or {"status": "complete"})
    monkeypatch.setattr(harness, "read_run", lambda run: {"id": run})
    base = ["find_rpt", "ABC LN", "2026-05-11", "Test", "--analyze"]
    for extra in [["--confirm-selection"], ["--report-id", rid]]:
        monkeypatch.setattr(sys, "argv", base + extra)
        with pytest.raises(SystemExit) as exc:
            runpy.run_module("find_rpt", run_name="__main__")
        assert exc.value.code == 2 and not executed
    monkeypatch.setattr(sys, "argv", base + ["--report-id", rid, "--confirm-selection"])
    runpy.run_module("find_rpt", run_name="__main__")
    assert len(executed) == 1
    request = json.loads((harness.run_directory(executed[0]) / "request.json").read_text())
    assert request["selection"]["method"] == "user_confirmed"
