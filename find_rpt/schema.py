"""Small output contract; numeric differences and source validity are checked locally."""

from typing import Literal
from pydantic import BaseModel, ConfigDict


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Claim(StrictModel):
    text: str
    kind: Literal["broker", "inference", "not_reported"]
    sources: list[str]


class Estimate(StrictModel):
    metric: str
    fiscal_year: str
    units: str
    old: float | None
    new: float | None
    consensus_before: float | None
    consensus_after: float | None
    reported_revision_pct: float | None
    reported_revision_bps: float | None = None
    sources: list[str]
    note: str


class Draft(StrictModel):
    analyst: str
    to: str
    subject: str
    body: str
    sources: list[str]


class Brief(StrictModel):
    subject_match: Literal["confirmed", "ambiguous", "mismatch"]
    identity: Claim
    title: str
    report_date: str
    takeaway: Claim
    changes: list[Claim]
    drivers: list[Claim]
    context: Claim
    estimates: list[Estimate]
    estimate_picture: Claim
    material: list[Claim]
    revisions_present: bool
    rationale: Literal["clear", "partly_clear", "unclear", "not_applicable"]
    escalation_reason: str | None
    email_draft: Draft | None
    answer: list[Claim]
    limitations: list[str]


def difference(value, baseline):
    if value is None or baseline is None:
        return dict(absolute=None, percent=None)
    return dict(
        absolute=value - baseline,
        percent=None if baseline == 0 else (value - baseline) / abs(baseline) * 100,
    )


def comparisons(estimate):
    return dict(
        revision=difference(estimate.new, estimate.old),
        before_consensus=difference(estimate.old, estimate.consensus_before),
        after_consensus=difference(estimate.new, estimate.consensus_after),
    )


def validate_evidence(brief, valid_ids):
    claims = [
        brief.identity,
        brief.takeaway,
        brief.context,
        brief.estimate_picture,
        *brief.changes,
        *brief.drivers,
        *brief.material,
        *brief.answer,
    ]
    for item in [
        *claims,
        *brief.estimates,
        *([brief.email_draft] if brief.email_draft else []),
    ]:
        if any(ref not in valid_ids for ref in item.sources):
            raise ValueError("Model returned a citation outside the selected report.")
        if not item.sources and getattr(item, "kind", "") != "not_reported":
            raise ValueError(
                "Model returned an evidence-bearing item without a source."
            )
    if (
        brief.revisions_present
        and brief.rationale in {"unclear", "partly_clear"}
        and not brief.email_draft
    ):
        raise ValueError(
            "Revisions have an unresolved rationale but no email draft was generated."
        )
    if brief.email_draft and not brief.email_draft.to.strip():
        raise ValueError("Email draft needs a sourced address or [TODO: address].")
    return brief
