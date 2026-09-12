"""Synthetic API-to-evidence checks; these are never real model regressions."""

import json
import pytest

import app as web
from find_rpt import harness
from find_rpt.evidence import Fact, Quote
from tests.support import LINES, extracted_v3, fake_process, payload


def unclear_fixture(known_recipient):
    e = extracted_v3()
    lines = dict(
        LINES,
        p1l7="FY27 Dividend per share EUR Old 0.50 New 0.60",
        p1l8="B Analyst telephone +44 20 1234 5678",
        p1l9="FY26 Unadjusted EPS EUR 0.90",
    )
    if not known_recipient:
        lines["p1l6"] = "Covering analyst contact details are not disclosed."
        lines["p1l8"] = "No additional contact details."
        e.analyst.name = e.analyst.address = None
        e.analyst.name_sources = e.analyst.address_sources = []
    e.quotes = [Quote(line_id=k, text=v) for k, v in lines.items()]
    r = e.estimates[0].model_copy(deep=True)
    r.id, r.metric, r.fiscal_year = "r3", "Dividend per share", "FY27"
    r.old, r.new = 0.5, 0.6
    r.consensus_after = r.reported_revision_pct = None
    for field in type(r.support).model_fields:
        setattr(r.support, field, ["p1l7"] if field in
                {"metric", "fiscal_year", "units", "old", "new"} else [])
    r.reason, r.reason_fact_ids = "not_stated", []
    e.estimates.append(r)
    e.changes.append(Fact(
        id="f9", text="Dividend per share increases without a stated cause.",
        kind="broker", sources=["p1l7"], required=True,
    ))
    # An extra measure in a note must travel with its own evidence, not just EPS's row.
    e.estimates[0].note = "Unadjusted FY26 EPS is EUR 0.90."
    e.estimates[0].note_sources = ["p1l9"]
    return e, lines


def immediate_worker(monkeypatch):
    monkeypatch.setattr(web.worker, "submit", lambda fn, *args: fn(*args))


@pytest.mark.parametrize("known_recipient", [True, False])
def test_api_unclear_revision_draft_recipient_sender_and_highlighted_evidence(
    corpus, monkeypatch, known_recipient,
):
    e, lines = unclear_fixture(known_recipient)
    rid = corpus("20260511_Synthetic_unclear.pdf", "\n".join(lines.values()))
    calls = fake_process(monkeypatch, [payload(e.model_dump())])
    immediate_worker(monkeypatch)
    client = web.app.test_client()
    created = client.post("/api/runs", json={
        "report_id": rid, "ticker": "ABC LN", "model": "opus", "effort": "high",
    })
    assert created.status_code == 202
    state = client.get(f"/api/runs/{created.json['id']}").json
    assert state["status"] == "complete", state.get("error")
    b = state["result"]["brief"]
    draft = b["email_draft"]
    assert b["rationale"] == "partly_clear" and len(calls) == 1
    assert "Dividend per share (FY27)" in draft["body"]
    assert "EPS (FY26)" not in draft["body"]
    assert draft["body"].endswith("Thank you,\n[Your name]")
    assert draft["to"] == ("b.analyst@example.test" if known_recipient else "[TODO: address]")
    assert draft["analyst"] == ("B Analyst" if known_recipient else "[TODO: analyst]")
    assert "p1l7" in draft["sources"]
    if known_recipient:
        assert "p1l6" in draft["sources"]
    for refs, expected in [(draft["sources"], lines["p1l7"]),
                           (b["estimates"][0]["sources"], lines["p1l9"])]:
        source = client.get(f"/source/{rid}?refs={','.join(refs)}")
        assert source.status_code == 200 and expected.encode() in source.data
    assert client.post("/api/email/send", json=draft).status_code == 404
    assert not any("send" in rule.rule or "email" in rule.rule for rule in web.app.url_map.iter_rules())


def test_api_followup_preserves_parent_and_uses_only_selected_report(corpus, monkeypatch):
    e, lines = unclear_fixture(True)
    rid = corpus("20260511_Synthetic_parent.pdf", "\n".join(lines.values()))
    other = corpus("20260511_Synthetic_other.pdf", "Bloomberg: XYZ LN\nUNRELATED_REPORT_SECRET")
    followup = e.model_copy(deep=True)
    followup.answer = [Fact(
        id="f10", text="B Analyst: b.analyst@example.test; telephone +44 20 1234 5678.",
        kind="broker", sources=["p1l6", "p1l8"], required=True,
    )]
    calls = fake_process(monkeypatch, [payload(e.model_dump()), payload(followup.model_dump())])
    immediate_worker(monkeypatch)
    client = web.app.test_client()
    parent_id = client.post("/api/runs", json={"report_id": rid, "ticker": "ABC LN"}).json["id"]
    # Historical generated prose is not evidence for a new extraction.
    parent_result = harness.run_directory(parent_id) / "result.json"
    saved = json.loads(parent_result.read_text())
    saved["brief"]["takeaway"]["text"] = "UNSUPPORTED_PARENT_ANSWER"
    harness.save(parent_result, saved)
    child = client.post("/api/runs", json={
        "report_id": rid, "ticker": "ABC LN", "parent_id": parent_id,
        "question": "What covering-analyst contacts are disclosed?",
    })
    assert child.status_code == 202
    child_id = child.json["id"]
    directory = harness.run_directory(child_id)
    request = json.loads((directory / "request.json").read_text())
    assert request["parent_run_id"] == parent_id and request["report_id"] == rid
    prompt = (directory / "extraction/prompt.txt").read_text()
    assert lines["p1l8"] in prompt
    assert "UNSUPPORTED_PARENT_ANSWER" not in prompt and "UNRELATED_REPORT_SECRET" not in prompt
    state = client.get(f"/api/runs/{child_id}").json
    assert state["status"] == "complete" and len(calls) == 2
    answer = state["result"]["brief"]["answer"][0]
    source = client.get(f"/source/{rid}?refs={','.join(answer['sources'])}")
    assert source.status_code == 200 and lines["p1l8"].encode() in source.data
    mismatch = client.post("/api/runs", json={
        "report_id": other, "ticker": "XYZ LN", "parent_id": parent_id, "question": "Switch report",
    })
    assert mismatch.status_code == 400 and len(calls) == 2


@pytest.mark.parametrize("status", ["queued", "running", "failed"])
def test_followup_rejects_incomplete_parent_before_new_job(corpus, status):
    rid = corpus("20260511_Synthetic_parent.pdf", "\n".join(LINES.values()))
    parent = harness.prepare(rid, "ABC LN")
    harness.save(harness.run_directory(parent) / "status.json", {"status": status})
    before = set(harness.RUNS.iterdir())
    with pytest.raises(ValueError, match="completed parent"):
        harness.prepare(rid, "ABC LN", "Question", parent)
    assert set(harness.RUNS.iterdir()) == before
