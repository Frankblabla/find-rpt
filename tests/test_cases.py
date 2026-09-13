"""Native conversation tools: immutable artifacts, small answers and safe updates."""

import pytest

import app as web
from find_rpt import cases
from tests.support import LINES, extracted_v3


@pytest.fixture
def published(corpus):
    corpus("20260511_Test_native.pdf", "\n".join(LINES.values()))
    ctx = cases.start("ABC LN", "2026-05-11", "Test", session="native-test")
    evidence = cases.case_path(ctx["id"]) / "work" / "extraction.json"
    cases.save(evidence, extracted_v3().model_dump())
    cases.publish(ctx["id"], evidence, 0)
    return ctx["id"]


def answer_file(case_id, base=1, text="Higher demand lifts EPS."):
    path = cases.case_path(case_id) / "work" / "answer.json"
    cases.save(
        path,
        dict(
            question="Explain the earnings driver.",
            base_version=base,
            claims=[dict(text=text, kind="broker", sources=["p1l4"])],
            quotes=[dict(line_id="p1l4", text=LINES["p1l4"])],
        ),
    )
    return path


def test_source_ids_are_enough_for_publication_and_followup(published):
    folder = cases.case_path(published)
    candidate = folder / "work" / "without-quotes.json"
    value = extracted_v3().model_dump()
    value.pop("quotes")
    cases.save(candidate, value)
    result = cases.publish(published, candidate, 1)
    _, saved, meta = cases.version(published)
    assert saved["evidence"]["quotes"]
    assert all(q["text"] == LINES[q["line_id"]] for q in saved["evidence"]["quotes"])
    assert result["artifact_sha256"] == meta["files_sha256"]
    candidate = answer_file(published, base=2)
    value = cases.load(candidate)
    value.pop("quotes")
    cases.save(candidate, value)
    reply = cases.save_answer(published, candidate)
    assert cases.read_answer(published, reply["answer_id"])["quotes"] == [
        dict(line_id="p1l4", text=LINES["p1l4"])
    ]
    delivery = cases.deliver(published)
    assert delivery["artifact_status"] == "full"
    assert delivery["email_draft"] == saved["brief"]["email_draft"]
    assert delivery["artifact_sha256"] == meta["files_sha256"]


@pytest.mark.parametrize("defect", ["unknown_line", "altered_quote"])
def test_automatic_source_copy_never_repairs_false_evidence(published, defect):
    candidate = answer_file(published)
    value = cases.load(candidate)
    if defect == "unknown_line":
        value.pop("quotes")
        value["claims"][0]["sources"] = ["p99l99"]
    else:
        value["quotes"][0]["text"] = "Invented cause."
    cases.save(candidate, value)
    with pytest.raises(ValueError):
        cases.save_answer(published, candidate)
    assert cases.deliver(published)["version"] == 1


def test_full_workflow_preserves_prior_versions_and_reuses_data(published, monkeypatch):
    import subprocess

    monkeypatch.setattr(
        subprocess, "Popen", lambda *a, **k: pytest.fail("Unexpected subprocess/model")
    )
    cid = cases.resolve(session="native-test")
    assert cid == published
    old_path, original, _ = cases.version(cid)
    old_hashes = {p.name: cases.digest(p) for p in old_path.iterdir()}
    answer = cases.save_answer(cid, answer_file(cid))
    assert answer["html_unchanged"] and cases.context(cid)["latest_version"] == 1
    assert (
        cases.context(cid)["recent_answers"][0]["claims"][0]["text"]
        == "Higher demand lifts EPS."
    )
    cases.revise(cid, answer["answer_id"], 1)
    _, amended, _ = cases.version(cid)
    assert amended["brief"]["estimates"] == original["brief"]["estimates"]
    assert any(
        c["text"] == "Higher demand lifts EPS." for c in amended["brief"]["material"]
    )
    cases.rerender(cid, 2, years=["FY26"], detail="compact")
    path, filtered, _ = cases.version(cid)
    assert filtered["evidence"] == amended["evidence"]
    assert len(filtered["brief"]["estimates"]) == 2
    assert "Showing 1 of 2 rows" in (path / "brief.html").read_text()
    assert {p.name: cases.digest(p) for p in old_path.iterdir()} == old_hashes
    cases.attach(cid, "resumed-session")
    assert cases.resolve(session="resumed-session") == cid
    client = web.app.test_client()
    assert client.get(f"/case/{cid}").location.endswith(f"/case/{cid}/3")
    assert client.get(f"/case/{cid}/1").status_code == 200
    assert (
        client.get(f"/case/{cid}/3/data.json").json["evidence"] == amended["evidence"]
    )
    rid = filtered["report"]["id"]
    assert client.get(f"/source/{rid}?refs=p1l4").status_code == 200


@pytest.mark.parametrize("defect", ["quote", "missing_refs", "stale", "period"])
def test_failed_updates_keep_last_valid_artifact(published, defect):
    path, _, _ = cases.version(published)
    digest = cases.digest(path / "brief.html")
    candidate = answer_file(published)
    value = cases.load(candidate)
    if defect == "quote":
        value["quotes"][0]["text"] = "Invented evidence."
    elif defect == "missing_refs":
        value["claims"][0]["sources"] = []
    elif defect == "stale":
        value["base_version"] = 2
    cases.save(candidate, value)
    with pytest.raises(ValueError):
        if defect == "period":
            cases.rerender(published, 1, years=["FY99"])
        else:
            cases.save_answer(published, candidate)
    assert cases.context(published)["latest_version"] == 1
    assert cases.digest(path / "brief.html") == digest


def test_tampered_answer_and_artifact_are_rejected(published):
    cases.save_answer(published, answer_file(published))
    folder = cases.case_path(published)
    saved = folder / "answers/0001.json"
    saved.write_text(saved.read_text().replace("Higher demand", "Invented demand"))
    with pytest.raises(ValueError, match="Saved answer changed"):
        cases.revise(published, 1, 1)
    assert cases.load(folder / "case.json")["latest_version"] == 1
    html = folder / "versions/0001/brief.html"
    html.write_text("Overwritten")
    assert web.app.test_client().get(f"/case/{published}/1").status_code == 400


def test_user_draft_has_sourced_recipient_and_safe_html(published):
    question = "Could you explain the EPS demand sensitivity? <script>alert(1)</script>"
    answer = cases.save_answer(published, answer_file(published, text=question))
    cases.revise(published, answer["answer_id"], 1, draft=True)
    path, result, _ = cases.version(published)
    draft = result["brief"]["email_draft"]
    assert draft["to"] == "b.analyst@example.test"
    assert draft["analyst"] == "B Analyst"
    assert draft["body"].endswith("[Your name]")
    assert result["draft_origin"]["source"] == "user_request"
    html = (path / "brief.html").read_text()
    assert "<script>" not in html and "&lt;script&gt;" in html
    assert "never sent" in html
    cases.rerender(published, 2, detail="compact")
    assert cases.version(published)[1]["brief"]["email_draft"] == draft


def test_identity_gate_applies_before_publication(corpus):
    corpus("20260511_Test_identity.pdf", "\n".join(LINES.values()))
    ctx = cases.start("ABC LN", "2026-05-11", "Test")
    candidate = cases.case_path(ctx["id"]) / "work/extraction.json"
    value = extracted_v3().model_dump()
    value["subject_match"] = "mismatch"
    cases.save(candidate, value)
    with pytest.raises(ValueError, match="identity"):
        cases.publish(ctx["id"], candidate, 0)
    assert cases.context(ctx["id"])["latest_version"] == 0


def test_reasons_and_context_use_two_paragraphs_with_inline_sources(published):
    from find_rpt.render import render_html

    _, result, meta = cases.version(published)
    result["brief"]["drivers"] = [
        dict(text="Higher demand lifts earnings.", sources=["p1l4"]),
        dict(text="Better pricing supports margins.", sources=["p1l5"]),
    ]
    html = render_html(result, published, meta)
    section = html.split("<h2>Reasons and context</h2>", 1)[1].split("</section>", 1)[0]
    assert section.count("<p>") == 2
    assert "Higher demand lifts earnings." in section
    assert "Better pricing supports margins." in section
    assert "refs=p1l4" in section and "refs=p1l5" in section
    assert result["brief"]["context"]["text"] in section


def test_comparison_columns_omit_missing_data_but_keep_zero(published):
    from find_rpt.render import render_html
    from find_rpt.schema import Estimate, comparisons

    _, result, meta = cases.version(published)
    result["brief"]["revisions_present"] = False
    for row in result["brief"]["estimates"]:
        row.update(old=None, consensus_before=None, consensus_after=None)
    for row in result["evidence"]["estimates"]:
        row["reason"] = "not_a_revision"
    result["comparisons"] = [
        comparisons(Estimate.model_validate(row))
        for row in result["brief"]["estimates"]
    ]
    html = render_html(result, published, meta)
    assert "<th>Prior figure</th>" not in html
    assert "<th>Revision</th>" not in html
    assert "<th>Prior vs consensus</th>" not in html
    assert "<th>Reported vs consensus</th>" not in html
    assert "<th>Reported figure</th>" in html

    result["brief"]["estimates"][0].update(old=0, consensus_before=0, consensus_after=0)
    result["brief"]["revisions_present"] = True
    result["evidence"]["estimates"][0]["reason"] = "not_stated"
    result["comparisons"][0] = comparisons(
        Estimate.model_validate(result["brief"]["estimates"][0])
    )
    html = render_html(result, published, meta)
    assert "<th>Prior figure</th>" in html
    assert "<th>Revision</th>" in html
    assert "<th>Prior vs consensus</th>" in html
    assert "<th>Reported vs consensus</th>" in html
    assert "<td>0</td>" in html and "Consensus 0" in html


def test_retired_history_keeps_latest_context_and_followups_usable(published):
    import shutil

    cases.rerender(published, 1, detail="compact")
    folder, state = cases.read_case(published)
    expected_change = cases.version(published)[2]["changes"]
    state["retired_versions"] = [1]
    cases.save(folder / "case.json", state)
    shutil.rmtree(folder / "versions/0001")

    assert cases.context(published)["last_change"] == expected_change
    assert cases.deliver(published)["version"] == 2
    client = web.app.test_client()
    old = client.get(f"/case/{published}/1")
    assert old.status_code == 302 and old.location == f"/case/{published}"
    assert client.get(old.location, follow_redirects=True).status_code == 200
    assert client.get(f"/case/{published}/1/data.json").status_code == 410
    assert client.get(f"/case/{published}/999").status_code == 404
    answer = cases.save_answer(published, answer_file(published, 2))
    cases.revise(published, answer["answer_id"], 2, draft=True)
    path, result, _ = cases.version(published)
    assert result["brief"]["email_draft"] is not None
    assert "Previous version" not in (path / "brief.html").read_text()


@pytest.mark.parametrize("scenario", ["no_revision", "clear", "unexplained", "requested"])
def test_publication_explains_automatic_email_decision(published, scenario):
    value = extracted_v3().model_dump()
    if scenario in {"no_revision", "requested"}:
        for row in value["estimates"]:
            row.update(old=row["new"], reported_revision_pct=0,
                       reason="not_a_revision", reason_fact_ids=[])
    elif scenario == "unexplained":
        value["estimates"][0].update(reason="not_stated", reason_fact_ids=[])
    candidate = cases.case_path(published) / "work/email-decision.json"
    cases.save(candidate, value)
    cases.publish(published, candidate, 1)
    if scenario == "requested":
        answer = cases.save_answer(published, answer_file(published, 2))
        cases.revise(published, answer["answer_id"], 2, draft=True)
    path, result, _ = cases.version(published)
    html = (path / "brief.html").read_text()
    assert 'id="email-draft"' in html
    assert bool(result["brief"]["email_draft"]) == (scenario in {"unexplained", "requested"})
    if scenario == "no_revision":
        assert "no estimate revisions were identified" in html
    if scenario == "clear":
        assert "the report explains the identified estimate revisions" in html
    if scenario == "unexplained":
        assert "For estimate revisions whose rationale remains unclear" in html
    if scenario == "requested":
        assert "Requested in the conversation" in html
    if scenario in {"requested", "unexplained"}:
        assert "No email drafted" not in html
        assert "Email draft unavailable" not in html
    else:
        assert "<h2>Email draft</h2>" not in html
        assert "<pre>" not in html


def checkpoint_file(case_id):
    value = dict(
        title="Synthetic first read",
        report_date="2026-05-11",
        subject_match="confirmed",
        identity=dict(text="ABC LN", kind="broker", sources=["p1l1"]),
        claims=[dict(text="Higher demand lifts EPS.", kind="broker", sources=["p1l4"])],
        quotes=[dict(line_id=k, text=LINES[k]) for k in ["p1l1", "p1l4"]],
        pending=["Full estimate and consensus extraction; source review."],
    )
    path = cases.case_path(case_id) / "work/checkpoint.json"
    cases.save(path, value)
    return path


def test_partial_survives_failed_publication_and_model_free_delivery(
    corpus, monkeypatch, capsys
):
    from find_rpt import tools
    import subprocess
    import json

    corpus("20260511_Test_partial.pdf", "\n".join(LINES.values()))
    cid = cases.start("ABC LN", "2026-05-11", "Test", session="partial-test")["id"]
    assert cases.deliver(cid)["artifact_status"] == "unavailable"
    cases.checkpoint(cid, checkpoint_file(cid), 0)
    original_path, partial, _ = cases.version(cid)
    hashes = {p.name: cases.digest(p) for p in original_path.iterdir()}
    assert partial["artifact_status"] == "partial"
    assert "Not assessed yet." in (original_path / "brief.html").read_text()
    assert "Partial brief." in (original_path / "brief.html").read_text()
    assert (
        "Full estimate and consensus extraction"
        in (original_path / "brief.html").read_text()
    )
    candidate = cases.case_path(cid) / "work/extraction.json"
    cases.save(candidate, {"incomplete": True})
    monkeypatch.setattr(
        "sys.argv",
        [
            "tools",
            "publish",
            "--case",
            cid,
            "--file",
            str(candidate),
            "--base-version",
            "1",
        ],
    )
    assert tools.main() == 2
    failure = json.loads(capsys.readouterr().out)
    assert failure["delivery"]["artifact_status"] == "partial"
    assert failure["delivery"]["html_url"].endswith(f"/{cid}/1")
    monkeypatch.setattr(
        subprocess, "Popen", lambda *a, **k: pytest.fail("Unexpected model")
    )
    assert cases.deliver(cases.resolve(session="partial-test"))["version"] == 1
    assert cases.save_answer(cid, answer_file(cid))["html_unchanged"]
    cases.save(candidate, extracted_v3().model_dump())
    cases.publish(cid, candidate, 1)
    assert cases.deliver(cid)["artifact_status"] == "full"
    assert cases.deliver(cid)["version"] == 2
    assert {p.name: cases.digest(p) for p in original_path.iterdir()} == hashes
    assert web.app.test_client().get(f"/case/{cid}/1").status_code == 200
    with pytest.raises(ValueError, match="already exists"):
        cases.checkpoint(cid, checkpoint_file(cid), 2)


@pytest.mark.parametrize("defect", ["identity", "quote", "missing_source"])
def test_partial_does_not_bypass_identity_or_source_checks(corpus, defect):
    corpus("20260511_Test_partial.pdf", "\n".join(LINES.values()))
    cid = cases.start("ABC LN", "2026-05-11", "Test")["id"]
    candidate = checkpoint_file(cid)
    value = cases.load(candidate)
    if defect == "identity":
        value["subject_match"] = "mismatch"
    elif defect == "quote":
        value["quotes"][1]["text"] = "Fabricated source"
    else:
        value["claims"][0]["sources"] = []
    cases.save(candidate, value)
    with pytest.raises(ValueError):
        cases.checkpoint(cid, candidate, 0)
    assert cases.deliver(cid)["artifact_status"] == "unavailable"


def test_basis_points_are_rendered_separately_from_rounded_arithmetic(published):
    value = extracted_v3().model_dump()
    r = value["estimates"][0]
    r.update(old=1.2, new=1.2, reported_revision_pct=None, reported_revision_bps=2)
    r["support"].update(reported_revision_pct=[], reported_revision_bps=["p1l3"])
    candidate = cases.case_path(published) / "work/bps.json"
    cases.save(candidate, value)
    cases.publish(published, candidate, 1)
    path, result, _ = cases.version(published)
    assert "+2 bps reported" in (path / "brief.html").read_text()
    assert result["comparisons"][0]["revision"]["absolute"] == 0


def test_cli_keeps_rejected_candidate_for_audit(published, monkeypatch, capsys):
    from find_rpt import tools, reports

    candidate = answer_file(published)
    data = cases.load(candidate)
    data["quotes"][0]["text"] = "Unsupported quotation"
    cases.save(candidate, data)
    original = candidate.read_text()
    monkeypatch.setattr(
        "sys.argv", ["tools", "answer", "--case", published, "--file", str(candidate)]
    )
    assert tools.main() == 2
    assert "error" in capsys.readouterr().out
    event = cases.load(next((reports.LOCAL / "case-tool-events").glob("*.json")))
    assert event["status"] == "failed" and event["input_text"] == original
    assert cases.context(published)["latest_answer"] == 0


def test_missing_analyst_uses_todos_and_amend_preserves_requested_draft(published):
    _, result, _ = cases.version(published)
    result["evidence"]["analyst"] = dict(
        name=None, name_sources=[], address=None, address_sources=[]
    )
    candidate = cases.case_path(published) / "work" / "no-contact.json"
    cases.save(candidate, result["evidence"])
    cases.publish(published, candidate, 1)
    aid = cases.save_answer(published, answer_file(published, 2))["answer_id"]
    cases.revise(published, aid, 2, draft=True)
    draft = cases.version(published)[1]["brief"]["email_draft"]
    assert draft["analyst"] == "[TODO: analyst]" and draft["to"] == "[TODO: address]"
    aid = cases.save_answer(published, answer_file(published, 3))["answer_id"]
    cases.revise(published, aid, 3)
    assert cases.version(published)[1]["brief"]["email_draft"] == draft


def test_budget_tradeoff_is_reported_and_evidence_is_retained(published):
    value = extracted_v3().model_dump()
    value["material"] = [
        dict(
            id=f"f{n}",
            text=f"Optional{n} " + "context " * 39,
            kind="broker",
            sources=["p1l4"],
            required=False,
        )
        for n in range(7, 11)
    ]
    candidate = cases.case_path(published) / "work" / "editorial.json"
    cases.save(candidate, value)
    cases.publish(published, candidate, 1)
    aid = cases.save_answer(
        published, answer_file(published, 2, "Added " + "explanation " * 39)
    )["answer_id"]
    update = cases.revise(published, aid, 2)
    assert update["changes"]["removed_prose"]
    _, result, _ = cases.version(published)
    assert result["main_word_count"] <= 220
    assert all(
        text in [c["text"] for c in result["evidence"]["material"]]
        for text in update["changes"]["removed_prose"]
    )
    assert cases.context(published)["last_change"] == update["changes"]


@pytest.mark.parametrize("words_per_fact", [3, 25], ids=["fits", "over_budget"])
def test_amendment_keeps_required_facts_and_discloses_extended_prose(
    published, words_per_fact
):
    """Synthetic prose isolates the length policy from source interpretation."""
    value = extracted_v3().model_dump()
    value["material"] = [
        dict(
            id=f"f{n}",
            text=f"Context{n} " + "detail " * (words_per_fact - 1),
            kind="broker",
            sources=["p1l4"],
            required=True,
        )
        for n in range(7, 13)
    ]
    candidate = cases.case_path(published) / "work" / "six-facts.json"
    cases.save(candidate, value)
    cases.publish(published, candidate, 1)
    old_path, original, _ = cases.version(published)
    old_hashes = {p.name: cases.digest(p) for p in old_path.iterdir()}

    answer_path = answer_file(published, 2)
    answer = cases.load(answer_path)
    answer["claims"] = [
        dict(
            text=f"Clarification{n} " + "detail " * 34, kind="broker", sources=["p1l4"]
        )
        for n in range(2)
    ]
    cases.save(answer_path, answer)
    aid = cases.save_answer(published, answer_path)["answer_id"]
    cases.revise(published, aid, 2)
    if words_per_fact == 25:
        path, amended, _ = cases.version(published)
        assert amended["main_word_count"] > 220 and amended["composition_notice"]
        assert "Extended brief." in (path / "brief.html").read_text()
        assert len(amended["brief"]["material"]) == 8
    else:
        _, amended, _ = cases.version(published)
        assert len(amended["evidence"]["material"]) == 8
        assert len(amended["brief"]["material"]) == 8
        assert amended["main_word_count"] <= 220
        assert amended["brief"]["estimates"] == original["brief"]["estimates"]
        assert amended["evidence"]["material"][:6] == original["evidence"]["material"]
        assert amended["evidence"]["quotes"] == original["evidence"]["quotes"]
    assert {p.name: cases.digest(p) for p in old_path.iterdir()} == old_hashes
