"""Synthetic comparison coverage, rendering and scoped preflight regressions."""

import pytest
from tests.support import extracted_v3, extracted, LINES, REQUEST
from find_rpt.evidence import (
    Quote,
    validate_extraction,
    picture_claim,
    comparison_provenance,
    select_facts,
    compose,
    main_word_count,
    composition_packet,
)
from find_rpt import reports
import app as web


def three_years():
    e = extracted_v3()
    lines = dict(
        LINES, p1l7="FY28 EPS EUR Current Broker Consensus", p1l8="1.60", p1l9="1.70"
    )
    e.quotes += [Quote(line_id=k, text=lines[k]) for k in ["p1l7", "p1l8", "p1l9"]]
    r = e.estimates[1].model_copy(deep=True)
    r.id = "r3"
    r.fiscal_year = "FY28"
    r.old = None
    r.new = 1.6
    r.consensus_after = 1.7
    r.reported_revision_pct = None
    for field in ["metric", "fiscal_year", "units"]:
        setattr(r.support, field, ["p1l7"])
    r.support.old = []
    r.support.new = ["p1l7", "p1l8"]
    r.support.consensus_after = ["p1l7", "p1l9"]
    r.support.reported_revision_pct = []
    e.estimates.append(r)
    g = e.estimate_picture.groups[0]
    g.fiscal_years.append("FY28")
    g.row_ids.append("r3")
    g.header_sources.append("p1l7")
    return e, lines


def test_last_year_comparison_is_preserved_and_sources_are_derived_locally():
    e, lines = three_years()
    validate_extraction(e, lines)
    c = picture_claim(e)
    assert "3 current broker/consensus pairs" in c.text
    assert {"p1l7", "p1l8", "p1l9"} <= set(c.sources)
    b = compose(e, select_facts(e, REQUEST), REQUEST)
    assert len(b.estimates) == 3 and b.estimates[-1].consensus_after == 1.7
    assert comparison_provenance(e)[0]["row_ids"] == ["r1", "r2", "r3"]


@pytest.mark.parametrize(
    "defect",
    [
        "missing_row",
        "missing_declared_year",
        "missing_group",
        "unknown_id",
        "definition_mix",
        "missing_value_source",
    ],
)
def test_comparison_integrity_failures_do_not_silently_drop_values(defect):
    e, lines = three_years()
    g = e.estimate_picture.groups[0]
    if defect == "missing_row":
        e.estimates.pop()
    if defect == "missing_declared_year":
        g.fiscal_years.pop()
    if defect == "missing_group":
        e.estimate_picture.groups = []
    if defect == "unknown_id":
        g.row_ids[-1] = "r99"
    if defect == "definition_mix":
        e.estimates[-1].metric = "A different EPS definition"
    if defect == "missing_value_source":
        e.estimates[-1].support.consensus_after = []
    with pytest.raises(ValueError):
        validate_extraction(e, lines)


def test_zero_consensus_is_a_pair_and_missing_prior_is_not_reused():
    e = extracted_v3()
    e.estimates[0].consensus_after = 0
    validate_extraction(e, LINES)
    c = picture_claim(e)
    assert "2 current" in c.text and "no prior pairs" in c.text
    assert e.estimates[0].consensus_before is None


def test_no_revision_no_consensus_accepts_forecasts_or_an_empty_table():
    e = extracted_v3()
    e.estimate_picture.groups = []
    e.drivers = []
    for r in e.estimates:
        r.old = None
        r.support.old = []
        r.reported_revision_pct = None
        r.support.reported_revision_pct = []
        r.consensus_after = None
        r.support.consensus_after = []
        r.reason = "not_a_revision"
        r.reason_fact_ids = []
    e.changes = []
    for rows in [e.estimates, []]:
        e.estimates = rows
        b = compose(validate_extraction(e, LINES), select_facts(e, REQUEST), REQUEST)
        assert (
            not b.revisions_present
            and b.rationale == "not_applicable"
            and b.email_draft is None
        )
        assert b.estimate_picture.text == "The table has no broker/consensus pairs."


def test_wording_expansion_counts_words_and_preserves_raw_quotes_and_required_facts():
    e = extracted_v3()
    e.takeaway.text = "PO and DPS rise."
    e.changes[0].text = "price target and dividend per share rise."
    raw = e.model_dump_json()
    choice = select_facts(e, REQUEST)
    assert choice.change_ids == []
    b = compose(e, choice, REQUEST)
    assert b.takeaway.text == "price target and dividend per share rise."
    assert main_word_count(b) <= 220 and e.model_dump_json() == raw
    e.changes[0].required = True
    assert select_facts(e, REQUEST).change_ids == ["f3"]
    # Legacy composition and source conflicts are not rewritten.
    old = extracted()
    old.takeaway.text = "PO and DPS rise."
    assert (
        compose(old, select_facts(old, REQUEST), REQUEST).takeaway.text
        == "PO and DPS rise."
    )
    e.conflicts = [e.takeaway.model_copy(update={"id": "f9"})]
    assert (
        compose(e, select_facts(e, REQUEST), REQUEST).material[-1].text
        == "PO and DPS rise."
    )


def test_expanded_mandatory_prose_exceeds_target_without_truncation():
    e = extracted_v3()
    for f in [e.takeaway, *e.drivers, e.event]:
        f.text = " ".join(["DPS"] * 25)
    raw = e.model_dump_json()
    b = compose(e, select_facts(e, REQUEST), REQUEST)
    assert main_word_count(b) > 220
    assert len(b.drivers) == len(e.drivers)
    assert raw == e.model_dump_json()


def test_compact_host_wording_counts_toward_budget_and_keeps_required_text():
    e = extracted_v3()
    e.estimates = []
    e.estimate_picture.groups = []
    e.changes[0].required = True
    e.management.named_executives = []
    e.management.conversation_reported = False
    e.management.conversation_sources = []
    e.changes[0].text = "A required valuation fact stays verbatim."
    b = compose(e, select_facts(e, REQUEST), REQUEST)
    packet = composition_packet(e, REQUEST)
    assert (
        packet["contact"]["text"]
        == "No executive names or management conversation reported."
    )
    assert b.changes[0].text == e.changes[0].text
    assert main_word_count(b) == packet["fixed_word_count"] + len(
        e.changes[0].text.split()
    )
    spare = 220 - main_word_count(b)
    e.takeaway.text += " evidence" * spare
    raw = e.model_dump_json()
    assert main_word_count(compose(e, select_facts(e, REQUEST), REQUEST)) == 220
    assert e.model_dump_json() == raw
    e.takeaway.text += " overflow"
    raw = e.model_dump_json()
    b = compose(e, select_facts(e, REQUEST), REQUEST)
    assert main_word_count(b) == 221
    assert b.changes[0].text == e.changes[0].text
    assert e.model_dump_json() == raw


@pytest.mark.parametrize(
    "metric",
    [
        "Price target (EUR)",
        "ADR price target (EUR)",
        "12m price target (EUR)",
        "12-month price target (EUR)",
    ],
)
def test_sourced_non_fiscal_target_qualifiers_are_preserved(metric):
    e = extracted_v3()
    e.estimates = e.estimates[:1]
    e.estimate_picture.groups = []
    r = e.estimates[0]
    r.consensus_after = None
    r.support.consensus_after = []
    r.metric = metric
    r.fiscal_year = "n/a"
    r.support.fiscal_year = []
    lines = dict(LINES, p1l7="ADR 12m price target (EUR); 12-month price target (EUR)")
    e.quotes.append(Quote(line_id="p1l7", text=lines["p1l7"]))
    r.support.metric = r.support.units = ["p1l7"]
    b = compose(validate_extraction(e, lines), select_facts(e, REQUEST), REQUEST)
    assert b.estimates[0].metric == metric and b.estimates[0].fiscal_year == "n/a"
    r.metric = metric.replace("EUR", "USD")
    with pytest.raises(ValueError, match="qualifiers need matching source"):
        validate_extraction(e, lines)
    r.metric = "24m price target (EUR)"
    with pytest.raises(ValueError, match="qualifiers need matching source"):
        validate_extraction(e, lines)
    r.metric = "ADR price target (EUR)"
    e.quotes[-1].text = lines["p1l7"] = "Price target (EUR)"
    with pytest.raises(ValueError, match="qualifiers need matching source"):
        validate_extraction(e, lines)


@pytest.mark.parametrize(
    "metric", ["EPS (EUR)", "Sales", "Price target growth", "Price target FY26"]
)
def test_ordinary_forecasts_cannot_hide_missing_periods_in_metric_labels(metric):
    e = extracted_v3()
    e.estimates[0].metric = metric
    e.estimates[0].fiscal_year = "n/a"
    e.estimates[0].support.fiscal_year = []
    with pytest.raises(ValueError, match="supported fiscal period"):
        validate_extraction(e, LINES)


@pytest.mark.parametrize(
    "metric,label",
    [
        ("Target price (12-mth)", "Target price (12-mth) EUR"),
        ("12-month target price", "Target price (12-mth) EUR"),
        ("Price target (Dec-27)", "Price target (Dec-27) EUR"),
    ],
)
def test_target_horizon_spelling_does_not_prevent_publication(metric, label):
    e = extracted_v3()
    row = e.estimates[0]
    row.metric, row.fiscal_year = metric, "n/a"
    row.support.fiscal_year = []
    row.support.metric = row.support.units = ["p1l7"]
    row.consensus_after = None
    row.support.consensus_after = []
    e.estimate_picture.groups[0].fiscal_years = ["FY27"]
    e.estimate_picture.groups[0].row_ids = ["r2"]
    lines = dict(LINES, p1l7=label)
    e.quotes.append(Quote(line_id="p1l7", text=label))
    brief = compose(validate_extraction(e, lines), select_facts(e, REQUEST), REQUEST)
    assert brief.estimates[0].metric == metric
    assert (brief.estimates[0].old, brief.estimates[0].new) == (1, 1.2)


def test_reported_basis_points_survive_equal_rounded_levels_and_require_evidence():
    from find_rpt.schema import comparisons
    from find_rpt.evidence import ExtractionV3

    value = extracted_v3().model_dump()
    row = value["estimates"][0]
    row.update(
        metric="Operating margin",
        units="%",
        old=16.0,
        new=16.0,
        reported_revision_pct=None,
        reported_revision_bps=2,
    )
    row["support"].update(reported_revision_pct=[], reported_revision_bps=["p1l7"])
    value["estimate_picture"]["groups"][0].update(fiscal_years=["FY27"], row_ids=["r2"])
    value["estimate_picture"]["groups"].append(
        dict(
            metric="Operating margin",
            basis="current",
            fiscal_years=["FY26"],
            row_ids=["r1"],
            header_sources=["p1l2"],
        )
    )
    lines = dict(
        LINES, p1l7="FY26 operating margin: 16.0% old, 16.0% new; change +2bps."
    )
    value["quotes"].append(dict(line_id="p1l7", text=lines["p1l7"]))
    e = ExtractionV3.model_validate(value)
    brief = compose(validate_extraction(e, lines), select_facts(e, REQUEST), REQUEST)
    assert brief.revisions_present and brief.rationale == "clear"
    assert brief.estimates[0].reported_revision_bps == 2
    assert comparisons(brief.estimates[0])["revision"]["absolute"] == 0
    e.estimates[0].support.reported_revision_bps = []
    with pytest.raises(ValueError, match="reported_revision_bps"):
        validate_extraction(e, lines)


def test_selected_api_preflight_never_opens_another_cover(corpus, monkeypatch):
    rid = corpus("20260511_Test_a.pdf", "Bloomberg: ABC LN")
    other = corpus("20260511_Test_b.pdf", "Bloomberg: XYZ LN")
    _, forbidden = reports.report(other)
    original_open = reports.pymupdf.open
    opened = []

    def guarded(path, *a, **kw):
        assert str(path) != str(forbidden), "Opened unselected cover"
        opened.append(str(path))
        return original_open(path, *a, **kw)

    monkeypatch.setattr(reports.pymupdf, "open", guarded)
    monkeypatch.setattr(web.worker, "submit", lambda *a: None)
    response = web.app.test_client().post(
        "/api/runs",
        json={"report_id": rid, "ticker": "ABC LN", "model": "opus", "effort": "high"},
    )
    assert response.status_code == 202 and opened


@pytest.mark.parametrize("cause", ["stated", "not_stated"])
def test_qualitative_revision_keeps_unknown_arithmetic_and_correct_email_semantics(
    cause,
):
    from find_rpt.schema import comparisons

    e = extracted_v3()
    r = e.estimates[0]
    e.estimates = [r]
    e.estimate_picture.groups = []
    r.metric = "EPS" if cause == "stated" else "Dividend per share"
    r.old = r.consensus_after = r.reported_revision_pct = None
    r.support.old = r.support.consensus_after = r.support.reported_revision_pct = []
    r.reason = cause
    r.reason_fact_ids = ["f4"] if cause == "stated" else []
    r.note = f"FY26 {r.metric} rises from below EUR 1.00 to EUR 1.20; exact prior value unavailable."
    lines = dict(LINES, p1l7=r.note)
    e.quotes.append(Quote(line_id="p1l7", text=lines["p1l7"]))
    r.note_sources = r.support.metric = r.support.fiscal_year = r.support.units = (
        r.support.new
    ) = ["p1l7"]
    original = e.model_dump_json()
    b = compose(validate_extraction(e, lines), select_facts(e, REQUEST), REQUEST)
    assert e.model_dump_json() == original
    assert b.revisions_present and b.estimates[0].old is None
    assert comparisons(b.estimates[0])["revision"] == {
        "absolute": None,
        "percent": None,
    }
    if cause == "stated":
        assert b.rationale == "clear" and b.email_draft is None
    else:
        assert (
            b.rationale == "unclear"
            and "Dividend per share (FY26)" in b.email_draft.body
        )
    r.note = ""
    r.note_sources = []
    with pytest.raises(ValueError, match="explicitly sourced note"):
        validate_extraction(e, lines)


@pytest.mark.parametrize(
    "defect",
    [
        "equal_levels",
        "zero_rate",
        "no_current",
        "missing_cause",
        "bad_quote",
        "missing_year",
    ],
)
def test_qualitative_revision_does_not_bypass_numeric_or_source_gates(defect):
    e = extracted_v3()
    r = e.estimates[0]
    r.old = r.reported_revision_pct = None
    r.support.old = r.support.reported_revision_pct = []
    r.note = "FY26 EPS rises to EUR 1.20 from below EUR 1.00."
    lines = dict(LINES, p1l7=r.note)
    e.quotes.append(Quote(line_id="p1l7", text=r.note))
    r.note_sources = ["p1l7"]
    if defect == "equal_levels":
        r.old = r.new
        r.support.old = ["p1l3"]
    if defect == "zero_rate":
        r.reported_revision_pct = 0
        r.support.reported_revision_pct = ["p1l3"]
    if defect == "no_current":
        r.new = None
        r.support.new = []
    if defect == "missing_cause":
        r.reason_fact_ids = []
    if defect == "bad_quote":
        e.quotes[-1].text = "Invented source text"
    if defect == "missing_year":
        r.support.fiscal_year = []
    with pytest.raises(ValueError):
        validate_extraction(e, lines)
