"""Small synthetic builders and the fake model process used by behavior tests."""

import json

from find_rpt import harness
from find_rpt.schema import Brief
from find_rpt.evidence import Extraction, ExtractionV3, Selection


def valid_brief():
    c = dict(text="Synthetic statement", kind="broker", sources=["p1l1"])
    return Brief(
        subject_match="confirmed",
        identity=c,
        title="Synthetic fixture",
        report_date="2026-05-11",
        takeaway=c,
        changes=[c],
        drivers=[c],
        context=c,
        estimates=[],
        estimate_picture=c,
        material=[],
        revisions_present=True,
        rationale="clear",
        escalation_reason=None,
        email_draft=None,
        answer=[],
        limitations=[],
    )



LINES = {
    "p1l1": "Bloomberg: ABC LN",
    "p1l2": "FY26 FY27 EPS EUR Old New Change Consensus",
    "p1l3": "1.00 1.20 20% 1.30; 1.40 1.40 0% 1.50",
    "p1l4": "Higher demand lifts EPS; dividend cause is not stated.",
    "p1l5": "A Person CEO",
    "p1l6": "B Analyst b.analyst@example.test",
}



def extracted():
    def fact(i, text, source="p1l4", required=True):
        return dict(
            id=f"f{i}", text=text, kind="broker", sources=[source], required=required
        )

    def row(i, year, old, new, rate):
        return dict(
            id=f"r{i}",
            metric="EPS",
            fiscal_year=year,
            units="EUR",
            old=old,
            new=new,
            consensus_before=None,
            consensus_after=1.3,
            reported_revision_pct=rate,
            support={
                key: ([] if key == "consensus_before" else ["p1l2", "p1l3"])
                for key in [
                    "metric",
                    "fiscal_year",
                    "units",
                    "old",
                    "new",
                    "consensus_before",
                    "consensus_after",
                    "reported_revision_pct",
                ]
            },
            note="",
            note_sources=[],
            reason="stated" if old != new else "not_a_revision",
            reason_fact_ids=["f4"] if old != new else [],
        )

    return Extraction.model_validate(
        dict(
            subject_match="confirmed",
            title="Synthetic report",
            report_date="2026-05-11",
            identity=fact(1, "ABC LN", "p1l1"),
            quotes=[dict(line_id=k, text=v) for k, v in LINES.items()],
            takeaway=fact(2, "Demand supports earnings."),
            changes=[fact(3, "EPS rises.", required=False)],
            drivers=[fact(4, "Higher demand lifts EPS.")],
            event=fact(5, "A results review."),
            estimate_picture=fact(6, "Current consensus is available.", "p1l2"),
            material=[],
            conflicts=[],
            answer=[],
            estimates=[row(1, "FY26", 1, 1.2, 20), row(2, "FY27", 1.4, 1.4, 0)],
            management=dict(
                named_executives=[dict(name="A Person", role="CEO", sources=["p1l5"])],
                conversation_reported=False,
                conversation_sources=[],
            ),
            analyst=dict(
                name="B Analyst",
                name_sources=["p1l6"],
                address="b.analyst@example.test",
                address_sources=["p1l6"],
            ),
            limitations=[],
        )
    )



def extracted_v3():
    data = extracted().model_dump()
    data.update(
        schema_version=3,
        estimate_picture={
            "groups": [
                {
                    "metric": "EPS",
                    "basis": "current",
                    "fiscal_years": ["FY26", "FY27"],
                    "row_ids": ["r1", "r2"],
                    "header_sources": ["p1l2"],
                }
            ],
            "scenario": None,
        },
    )
    return ExtractionV3.model_validate(data)



REQUEST = dict(ticker="ABC LN", question="")



CHOICE = Selection(change_ids=[], material_ids=[])



def fake_process(monkeypatch, payloads):
    calls = []
    monkeypatch.setattr(harness.shutil, "which", lambda name: "/synthetic/claude")
    monkeypatch.setattr(
        harness.subprocess, "check_output", lambda *a, **k: "Synthetic CLI"
    )

    class Process:
        def __init__(self, command, **kwargs):
            calls.append(command)
            kwargs["stdout"].write(json.dumps(payloads[len(calls) - 1]))

        def wait(self, **kwargs):
            return 0

    monkeypatch.setattr(harness.subprocess, "Popen", Process)
    return calls



def payload(data):
    return dict(
        subtype="success", structured_output=data, total_cost_usd=0.02, num_turns=1
    )

