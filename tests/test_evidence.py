"""Evidence and composition behavior checks using synthetic source data only."""

import json
import pytest
from find_rpt.schema import Brief
from tests.support import (
    LINES, REQUEST, CHOICE, extracted, extracted_v3, fake_process, payload, valid_brief,
)
from find_rpt import harness
from find_rpt.evidence import (
    Extraction,
    Selection,
    validate_extraction,
    compose,
    composition_packet,
    main_word_count,
    select_facts,
)


REQUEST = dict(ticker="ABC LN", question="")
def test_both_years_and_values_survive_editorial_selection():
    e = validate_extraction(extracted(), LINES)
    e.estimates[1].old = 1.41
    e.estimates[1].reason = "stated"
    e.estimates[1].reason_fact_ids = ["f4"]
    b = compose(validate_extraction(e, LINES), CHOICE, REQUEST)
    assert [(r.fiscal_year, r.old, r.new) for r in b.estimates] == [
        ("FY26", 1, 1.2),
        ("FY27", 1.41, 1.4),
    ]
    assert b.estimates[1].reported_revision_pct == 0
    assert b.estimates[0].consensus_before is None
    assert b.estimates[0].consensus_after == 1.3


def test_zero_and_rounded_values_keep_reported_rates():
    e = extracted()
    r = e.estimates[0]
    r.old = 0
    r.new = 0
    r.reported_revision_pct = 0.1
    b = compose(validate_extraction(e, LINES), CHOICE, REQUEST)
    from find_rpt.schema import comparisons

    assert comparisons(b.estimates[0])["revision"]["percent"] is None
    assert b.estimates[0].reported_revision_pct == 0.1


@pytest.mark.parametrize(
    "defect", ["unknown_quote", "wrong_quote", "missing_label", "unknown_fact_ref"]
)
def test_evidence_failures_are_rejected(defect):
    e = extracted()
    if defect == "unknown_quote":
        e.quotes[0].line_id = "p99l99"
    if defect == "wrong_quote":
        e.quotes[0].text = "Invented text"
    if defect == "missing_label":
        e.estimates[0].support.fiscal_year = []
    if defect == "unknown_fact_ref":
        e.takeaway.sources = ["p99l99"]
    with pytest.raises(ValueError):
        validate_extraction(e, LINES)


def test_unknown_writer_fields_ids_and_required_omission_fail():
    with pytest.raises(ValueError):
        Selection.model_validate(dict(change_ids=[], material_ids=[], text="New prose"))
    with pytest.raises(ValueError, match="evidence ID"):
        compose(extracted(), Selection(change_ids=["f999"], material_ids=[]), REQUEST)
    e = extracted()
    e.changes[0].required = True
    with pytest.raises(ValueError, match="mandatory"):
        compose(e, CHOICE, REQUEST)


def test_overflow_preserves_full_sentences_and_mandatory_conflict():
    e = extracted()
    for f in [e.takeaway, e.changes[0], *e.drivers, e.event, e.estimate_picture]:
        f.text = " ".join(["word"] * 44) + "."
    e.conflicts = [e.material[0]] if e.material else []
    before = e.model_dump_json()
    b = compose(e, Selection(change_ids=["f3"], material_ids=[]), REQUEST)
    assert main_word_count(b) > 220
    assert b.takeaway.text == e.takeaway.text
    assert b.changes[0].text == e.changes[0].text
    assert e.model_dump_json() == before
    e = extracted()
    f = e.changes.pop()
    f.text = "The source gives conflicting periods."
    e.conflicts = [f]
    assert compose(e, CHOICE, REQUEST).material[0].text == f.text


def test_stated_cause_does_not_require_numerical_bridge_email():
    e = extracted()
    e.estimates[0].note = "No full accounting bridge or prior consensus is provided."
    e.estimates[0].note_sources = ["p1l4"]
    b = compose(validate_extraction(e, LINES), CHOICE, REQUEST)
    assert b.email_draft is None and b.rationale == "clear"


def test_separate_unexplained_change_gets_specific_local_email_and_fixed_sender():
    e = extracted()
    r = e.estimates[1]
    r.metric = "Dividend per share"
    r.new = 1.3
    r.reason = "not_stated"
    b = compose(validate_extraction(e, LINES), CHOICE, REQUEST)
    assert b.rationale == "partly_clear"
    assert "Dividend per share (FY27)" in b.email_draft.body
    assert "EPS (FY26)" not in b.email_draft.body
    assert b.email_draft.body.endswith("Thank you,\n[Your name]")
    assert b.email_draft.to == "b.analyst@example.test"
    e.analyst.name = None
    e.analyst.name_sources = []
    e.analyst.address = None
    e.analyst.address_sources = []
    b = compose(validate_extraction(e, LINES), CHOICE, REQUEST)
    assert (
        b.email_draft.analyst == "[TODO: analyst]"
        and b.email_draft.to == "[TODO: address]"
    )


def test_unsupported_identity_and_missing_cause_reference_fail():
    e = extracted()
    e.analyst.address = "invented@example.test"
    with pytest.raises(ValueError, match="identity"):
        validate_extraction(e, LINES)
    e = extracted()
    e.estimates[0].reason_fact_ids = []
    with pytest.raises(ValueError, match="reason needs evidence"):
        validate_extraction(e, LINES)


def test_named_executive_does_not_establish_conversation():
    b = compose(validate_extraction(extracted(), LINES), CHOICE, REQUEST)
    assert (
        "A Person (CEO)" in b.context.text
        and "No management conversation" in b.context.text
    )
    e = extracted()
    e.management.conversation_reported = True
    with pytest.raises(ValueError):
        validate_extraction(e, LINES)


def test_writer_receives_bounded_packet_without_report_or_editable_estimates():
    packet = composition_packet(extracted(), REQUEST)
    assert "report" not in packet and "estimates" not in packet
    assert (
        len(json.dumps(packet).encode()) < 48000 and packet["target_main_words"] == 220
    )
    assert packet["fixed_word_count"] < 220


def test_real_path_synthetic_extraction_local_composition_and_historical_loading(
    corpus, monkeypatch
):
    rid = corpus("20260511_Test_a.pdf", "\n".join(LINES.values()))
    calls = fake_process(monkeypatch, [payload(extracted_v3().model_dump())])
    run_id = harness.prepare(rid, "ABC LN")
    state = harness.execute(run_id)
    assert state["status"] == "complete", state.get("error")
    assert len(calls) == 1 and state["estimated_cost_usd"] == 0.02
    loaded = harness.read_run(run_id)["result"]
    loaded_brief = Brief.model_validate(loaded["brief"])
    assert loaded["main_word_count"] == main_word_count(loaded_brief)
    assert len(loaded_brief.estimates) == 2
    directory = harness.run_directory(run_id)
    assert (directory / "composition" / "input.json").exists()
    assert all(
        (directory / name / "validated.json").exists()
        for name in ["extraction", "composition"]
    )
    historical = "a" * 32
    old = harness.run_directory(historical)
    old.mkdir()
    body = {"brief": valid_brief().model_dump(), "runtime": {"harness": "Codex"}}
    harness.save(old / "status.json", dict(status="complete"))
    harness.save(old / "result.json", body)
    assert harness.read_run(historical)["result"] == body


@pytest.mark.parametrize("stage", ["extraction", "composition"])
def test_baseline_preserves_raw_input_and_only_rejects_invalid_evidence(
    corpus, monkeypatch, stage
):
    rid = corpus("20260511_Test_a.pdf", "\n".join(LINES.values()))
    e = extracted_v3()
    if stage == "extraction":
        e.quotes[0].text = "Unsupported quote"
    else:
        e.conflicts = [e.changes.pop()]
        e.material = [e.takeaway.model_copy(update={"id": "f8", "required": True})]
        for f in [e.takeaway, *e.drivers, e.event, *e.material, *e.conflicts]:
            f.text = " ".join(["long"] * 45)
    calls = fake_process(
        monkeypatch,
        [payload(e.model_dump()), payload(dict(change_ids=["f999"], material_ids=[]))],
    )
    run_id = harness.prepare(rid, "ABC LN")
    state = harness.execute(run_id)
    directory = harness.run_directory(run_id)
    assert (directory / "extraction" / "harness-output.json").exists() and (
        directory / "extraction" / "response.json"
    ).exists()
    if stage == "extraction":
        assert state["status"] == "failed" and stage in state["error"]
        assert not (directory / "result.json").exists()
    else:
        assert state["status"] == "complete"
        result = json.loads((directory / "result.json").read_text())
        assert result["main_word_count"] > 220
        assert result["evidence"] == e.model_dump()
    assert len(calls) == 1
    before = (directory / "status.json").read_bytes()
    with pytest.raises(ValueError):
        harness.execute(run_id)
    assert before == (directory / "status.json").read_bytes()
    if stage == "composition":
        assert (directory / "extraction" / "validated.json").exists()


def test_local_selection_adds_whole_optional_facts_only_when_they_fit():
    e = extracted()
    e.changes[0].text = " ".join(["optional"] * 45)
    e.conflicts = [e.changes[0].model_copy(update={"id": "f7", "required": True})]
    for f in [e.takeaway, *e.drivers, e.event]:
        f.text = " ".join(["required"] * 40)
    before = e.model_dump_json()
    choice = select_facts(e, REQUEST)
    assert "f3" not in choice.change_ids
    assert e.model_dump_json() == before
    assert main_word_count(compose(e, choice, REQUEST)) <= 220


def test_recipient_address_sources_include_separate_name_and_address_lines():
    from find_rpt.evidence import Quote

    e = extracted()
    lines = dict(LINES, p1l6="B Analyst", p1l7="b.analyst@example.test")
    e.quotes[5].text = lines["p1l6"]
    e.quotes.append(Quote(line_id="p1l7", text=lines["p1l7"]))
    e.analyst.address_sources = ["p1l7"]
    with pytest.raises(ValueError, match="named recipient"):
        validate_extraction(e, lines)
    e.analyst.address_sources = ["p1l6", "p1l7"]
    assert validate_extraction(e, lines).analyst.address == "b.analyst@example.test"


def test_model_authored_sender_or_email_fields_are_not_accepted():
    data = extracted().model_dump()
    data["email_draft"] = {"body": "Regards, invented@example.test"}
    with pytest.raises(ValueError):
        Extraction.model_validate(data)


def test_revision_cause_in_change_section_is_valid_and_cannot_be_omitted():
    e = extracted()
    e.changes[0].text = "Revised estimates lift valuation."
    e.changes[0].required = False
    e.estimates[0].reason_fact_ids = ["f3"]
    validate_extraction(e, LINES)
    with pytest.raises(ValueError, match="mandatory"):
        compose(e, CHOICE, REQUEST)
    choice = select_facts(e, REQUEST)
    assert choice.change_ids == ["f3"]
    assert compose(e, choice, REQUEST).email_draft is None
    e.changes[0].kind = "not_reported"
    with pytest.raises(ValueError, match="sourced main-prose"):
        validate_extraction(e, LINES)


def test_non_fiscal_target_price_keeps_all_values_without_an_invented_year():
    from find_rpt.evidence import Quote

    e = extracted()
    r = e.estimates[0]
    lines = dict(LINES, p1l7="Target price (EUR)")
    e.quotes.append(Quote(line_id="p1l7", text=lines["p1l7"]))
    r.metric = "Target price"
    r.fiscal_year = "n/a"
    r.support.fiscal_year = []
    r.support.metric = ["p1l7"]
    b = compose(validate_extraction(e, lines), CHOICE, REQUEST)
    assert b.estimates[0].fiscal_year == "n/a"
    assert b.estimates[0].old == 1 and b.estimates[0].new == 1.2
    r.support.metric = ["p1l2"]
    with pytest.raises(ValueError, match="explicit target-price source label"):
        validate_extraction(e, lines)


def test_missing_eps_period_cannot_use_non_fiscal_exception():
    e = extracted()
    r = e.estimates[0]
    r.fiscal_year = "n/a"
    r.support.fiscal_year = []
    with pytest.raises(ValueError, match="supported fiscal period"):
        validate_extraction(e, LINES)
    r.fiscal_year = "FY26"
    with pytest.raises(ValueError, match="r1.fiscal_year"):
        validate_extraction(e, LINES)


def test_executive_role_can_paraphrase_sourced_context_but_name_must_match():
    e = extracted()
    person = e.management.named_executives[0]
    lines = dict(LINES, p1l5="A Person, currently CEO, will leave in 2027.")
    e.quotes[4].text = lines["p1l5"]
    person.role = "CEO (leaving in 2027)"
    assert (
        validate_extraction(e, lines).management.named_executives[0].role == person.role
    )
    person.name = "Invented Person"
    with pytest.raises(ValueError, match="Executive name"):
        validate_extraction(e, lines)


def synthetic_failed_source(corpus):
    import hashlib

    rid = corpus("20260511_Test_a.pdf", "\n".join(LINES.values()))
    run_id = harness.prepare(rid, "ABC LN")
    directory = harness.run_directory(run_id)
    stage = directory / "extraction"
    harness.save(stage / "schema.json", Extraction.model_json_schema())
    (stage / "prompt.txt").write_text("Synthetic frozen input")
    harness.save(stage / "harness-output.json", payload(extracted().model_dump()))
    harness.save(
        stage / "status.json",
        dict(
            status="failed",
            **{
                key + "_sha256": hashlib.sha256((stage / file).read_bytes()).hexdigest()
                for key, file in [
                    ("prompt", "prompt.txt"),
                    ("skill", "SKILL.md"),
                    ("schema", "schema.json"),
                ]
            },
        ),
    )
    row, _ = harness.report(rid)
    harness.save(
        directory / "status.json",
        dict(
            id=run_id,
            status="failed",
            workflow="evidence-local-composition-v2",
            report_sha256=row["sha256"],
            estimated_cost_usd=0.05,
        ),
    )
    return run_id


def test_offline_revalidation_has_lineage_zero_calls_and_preserves_source(
    corpus, monkeypatch
):
    from find_rpt.revalidate import revalidate

    source_id = synthetic_failed_source(corpus)
    source = harness.run_directory(source_id)
    before = {str(p): p.read_bytes() for p in source.rglob("*") if p.is_file()}

    def forbidden(*a, **k):
        raise AssertionError("Offline revalidation invoked a model")

    monkeypatch.setattr(harness.subprocess, "Popen", forbidden)
    state = revalidate(source_id)
    assert state["status"] == "complete", state.get("error")
    assert state["id"] != source_id and state["source_run_id"] == source_id
    assert state["offline_revalidation"] is True and state["model_invocations"] == 0
    assert state["estimated_cost_usd"] == 0
    assert all(
        __import__("pathlib").Path(name).read_bytes() == data
        for name, data in before.items()
    )
    result = harness.read_run(state["id"])["result"]
    assert result["source_run_id"] == source_id and result["model_invocations"] == 0
    assert result["brief"]["estimates"][0]["new"] == 1.2


def test_offline_revalidation_rejects_changed_frozen_input(corpus):
    from find_rpt.revalidate import revalidate

    source_id = synthetic_failed_source(corpus)
    (harness.run_directory(source_id) / "extraction/prompt.txt").write_text(
        "Changed input"
    )
    with pytest.raises(ValueError, match="Frozen source prompt hash changed"):
        revalidate(source_id)
