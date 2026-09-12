"""Two concrete contracts and local composition; no semantic-verifier claim."""

import re
from typing import Literal
from pydantic import Field
from find_rpt.schema import (
    StrictModel,
    Claim,
    Estimate,
    Brief,
    Draft,
    validate_evidence,
)


class Quote(StrictModel):
    line_id: str
    text: str


class Fact(StrictModel):
    id: str
    text: str
    kind: Literal["broker", "not_reported"]
    sources: list[str]
    required: bool


class Support(StrictModel):
    metric: list[str]
    fiscal_year: list[str]
    units: list[str]
    old: list[str]
    new: list[str]
    consensus_before: list[str]
    consensus_after: list[str]
    reported_revision_pct: list[str]
    reported_revision_bps: list[str] = Field(default_factory=list)


class EvidenceEstimate(StrictModel):
    id: str
    metric: str
    fiscal_year: str
    units: str
    old: float | None
    new: float | None
    consensus_before: float | None
    consensus_after: float | None
    reported_revision_pct: float | None
    reported_revision_bps: float | None = None
    support: Support
    note: str
    note_sources: list[str]
    reason: Literal["stated", "not_stated", "not_a_revision"]
    reason_fact_ids: list[str]


class Person(StrictModel):
    name: str
    role: str
    sources: list[str]


class Management(StrictModel):
    named_executives: list[Person] = Field(max_length=6)
    conversation_reported: bool
    conversation_sources: list[str]


class Analyst(StrictModel):
    name: str | None
    name_sources: list[str]
    address: str | None
    address_sources: list[str]


class Extraction(StrictModel):
    subject_match: Literal["confirmed", "ambiguous", "mismatch"]
    title: str
    report_date: str
    identity: Fact
    quotes: list[Quote] = Field(max_length=350)
    takeaway: Fact
    changes: list[Fact] = Field(max_length=8)
    drivers: list[Fact] = Field(max_length=2)
    event: Fact
    estimate_picture: Fact
    material: list[Fact]
    conflicts: list[Fact] = Field(max_length=4)
    answer: list[Fact] = Field(max_length=4)
    estimates: list[EvidenceEstimate] = Field(max_length=80)
    management: Management
    analyst: Analyst
    limitations: list[str] = Field(max_length=8)


class ComparisonGroup(StrictModel):
    metric: str
    basis: Literal["current", "prior"]
    fiscal_years: list[str] = Field(min_length=1, max_length=12)
    row_ids: list[str] = Field(min_length=1, max_length=12)
    header_sources: list[str] = Field(min_length=1)


class ComparisonPicture(StrictModel):
    groups: list[ComparisonGroup] = Field(max_length=30)
    scenario: Fact | None


class ExtractionV3(Extraction):
    schema_version: Literal[3]
    estimate_picture: ComparisonPicture


def picture_facts(e):
    if isinstance(e.estimate_picture, Fact):
        return [e.estimate_picture]
    return [e.estimate_picture.scenario] if e.estimate_picture.scenario else []


def plain_text(text):
    # Only established financial shorthand; never change source quotes or conflicts.
    for pattern, replacement in [
        (r"\bDPS\b", "dividend per share"),
        (r"\b(?:PO|TP)\b", "price target"),
        (r"\bprice objective\b", "price target"),
    ]:
        text = re.sub(pattern, replacement, text)
    return text


def displayed(f, e):
    untouched = {e.identity.id, *(item.id for item in e.conflicts)}
    text = (
        plain_text(f.text)
        if isinstance(e, ExtractionV3) and f.id not in untouched
        else f.text
    )
    return Claim(text=text, kind=f.kind, sources=f.sources)


def comparison_provenance(e):
    if not isinstance(e, ExtractionV3):
        return []
    by_id = {r.id: r for r in e.estimates}
    groups = []
    for group in e.estimate_picture.groups:
        value_fields = (
            ["new", "consensus_after"]
            if group.basis == "current"
            else ["old", "consensus_before"]
        )
        refs = list(group.header_sources)
        for rid in group.row_ids:
            row = by_id[rid]
            for field in ["metric", "fiscal_year", "units", *value_fields]:
                refs.extend(getattr(row.support, field))
        groups.append(dict(**group.model_dump(), sources=list(dict.fromkeys(refs))))
    return groups


def validate_picture(e, quotes):
    if not isinstance(e, ExtractionV3):
        return
    by_id = {r.id: r for r in e.estimates}
    expected = {
        (basis, r.id)
        for r in e.estimates
        for basis, a, b in [
            ("current", r.new, r.consensus_after),
            ("prior", r.old, r.consensus_before),
        ]
        if a is not None and b is not None
    }
    seen = set()
    for group in e.estimate_picture.groups:
        if any(ref not in quotes for ref in group.header_sources):
            raise ValueError("Comparison header refers to an undeclared source quote.")
        if len(group.row_ids) != len(set(group.row_ids)) or any(
            rid not in by_id for rid in group.row_ids
        ):
            raise ValueError(
                "Comparison group has duplicate or unknown estimate row IDs."
            )
        rows = [by_id[rid] for rid in group.row_ids]
        if any(
            normalized(row.metric).casefold() != normalized(group.metric).casefold()
            for row in rows
        ):
            raise ValueError("Comparison group mixes metric definitions.")
        periods = [normalized(y).casefold() for y in group.fiscal_years]
        actual = [normalized(row.fiscal_year).casefold() for row in rows]
        if len(periods) != len(set(periods)) or sorted(periods) != sorted(actual):
            raise ValueError(
                "Comparison group does not cover each declared fiscal year exactly once."
            )
        for rid in group.row_ids:
            key = (group.basis, rid)
            if key not in expected or key in seen:
                raise ValueError(
                    "Comparison group needs one explicit broker/consensus pair per basis and row."
                )
            seen.add(key)
    if seen != expected:
        raise ValueError(
            "Comparison coverage omits an extracted broker/consensus pair."
        )


def picture_claim(e):
    if not isinstance(e, ExtractionV3):
        return claim(e.estimate_picture)
    groups = comparison_provenance(e)
    counts = {
        basis: sum(len(g["row_ids"]) for g in groups if g["basis"] == basis)
        for basis in ["current", "prior"]
    }
    if not groups:
        text = "The table has no broker/consensus pairs."
    else:
        text = f"The table includes {counts['current']} current broker/consensus pairs"
        text += (
            f" and {counts['prior']} prior pairs."
            if counts["prior"]
            else "; no prior pairs are available."
        )
        text += " Metric definitions are kept separate."
    refs = list(dict.fromkeys(ref for g in groups for ref in g["sources"]))
    if e.estimate_picture.scenario:
        scenario = displayed(e.estimate_picture.scenario, e)
        text += " " + scenario.text
        refs = list(dict.fromkeys(refs + scenario.sources))
    return Claim(text=text, kind="broker" if refs else "not_reported", sources=refs)


class Selection(StrictModel):
    change_ids: list[str]
    material_ids: list[str]


def facts(e):
    return [
        e.identity,
        e.takeaway,
        *e.changes,
        *e.drivers,
        e.event,
        *picture_facts(e),
        *e.material,
        *e.conflicts,
        *e.answer,
    ]


def normalized(text):
    return " ".join(text.split())


def word_count(text):
    return len(text.split())


def has_numeric_revision(row):
    return (
        (row.reported_revision_pct is not None and row.reported_revision_pct != 0)
        or (row.reported_revision_bps is not None and row.reported_revision_bps != 0)
        or (row.old is not None and row.new is not None and row.old != row.new)
    )


def target_qualifier(text):
    """Compare sourced horizons without treating punctuation or mth/month as meaning."""
    text = re.sub(r"(\d+)\s*-?\s*(?:months?|mths?|m)\b", r"\1 month", text.casefold())
    return " ".join(re.findall(r"[a-z]+|\d+", text))


def is_changed(row):
    # Source assessment and calculable arithmetic are different: a prior range
    # can establish a revision without supplying an exact old value.
    return has_numeric_revision(row) or row.reason != "not_a_revision"


def row_sources(row):
    return list(
        dict.fromkeys(
            [ref for refs in row.support.model_dump().values() for ref in refs]
            + row.note_sources
        )
    )


def validate_extraction(e, lines):
    """Check exact quotations, field provenance and structural completeness, not entailment."""
    quotes = {q.line_id: q.text for q in e.quotes}
    if len(quotes) != len(e.quotes):
        raise ValueError("Duplicate evidence quote ID.")
    for ref, text in quotes.items():
        if ref not in lines or normalized(text) != normalized(lines[ref]):
            raise ValueError(f"Evidence quote does not match original line {ref}.")

    def refs_ok(refs, required=True, field="source-bearing item"):
        unknown = [ref for ref in refs if ref not in quotes]
        if (required and not refs) or unknown:
            raise ValueError(
                f"Missing or unknown evidence/source ID for {field}: {unknown or 'required references absent'}."
            )

    items = facts(e)
    if len({f.id for f in items}) != len(items):
        raise ValueError("Duplicate fact ID.")
    for f in items:
        if not re.fullmatch(r"f[1-9][0-9]*", f.id):
            raise ValueError("Fact IDs must use f1, f2, ...")
        if not f.text.strip() or word_count(f.text) > 45:
            raise ValueError(
                f"Fact {f.id} must contain 1–45 words; no truncation applied."
            )
        refs_ok(f.sources, f.kind != "not_reported")
    refs_ok(e.identity.sources)
    if not e.title.strip() or not e.report_date.strip():
        raise ValueError("Missing report title/date.")
    if len({r.id for r in e.estimates}) != len(e.estimates):
        raise ValueError("Duplicate estimate ID.")
    causal_facts = {
        f.id
        for f in [
            e.takeaway,
            *e.changes,
            *e.drivers,
            e.event,
            *picture_facts(e),
            *e.material,
            *e.conflicts,
        ]
        if f.kind == "broker"
    }
    for r in e.estimates:
        if not re.fullmatch(r"r[1-9][0-9]*", r.id):
            raise ValueError("Estimate IDs must use r1, r2, ...")
        non_fiscal = normalized(r.fiscal_year).casefold() in {"n/a", "not applicable"}
        if non_fiscal:
            labels = {"target price", "price target", "price objective"}
            target = re.fullmatch(
                r"(?:(ADR) )?(?:(\d{1,2}(?:m|mths?|[- ]months?)) )?"
                r"(target price|price target|price objective)(?: \(([^()]+)\))?",
                normalized(r.metric),
                re.IGNORECASE,
            )
            if not target:
                raise ValueError(f"Estimate {r.id} requires a supported fiscal period.")
            refs_ok(r.support.metric, field=f"estimate {r.id}.metric")
            label_text = normalized(
                " ".join(quotes[ref] for ref in r.support.metric)
            ).casefold()
            if not any(
                re.search(r"\b" + re.escape(label) + r"\b", label_text)
                for label in labels
            ):
                raise ValueError(
                    f"Non-fiscal exception needs an explicit target-price source label for {r.id}."
                )
            # Qualifiers identify a security, horizon or currency, so require
            # their source evidence instead of stripping them from the metric.
            adr, horizon, _, qualifier = target.groups()
            refs_ok(r.support.units, field=f"estimate {r.id}.units")
            unit_text = " ".join(quotes[ref] for ref in r.support.units)
            if (
                (adr and not re.search(r"\bADR\b", label_text, re.IGNORECASE))
                or (
                    horizon
                    and f" {target_qualifier(horizon)} "
                    not in f" {target_qualifier(label_text)} "
                )
                or (
                    qualifier
                    and (
                        f" {target_qualifier(qualifier)} "
                        not in f" {target_qualifier(label_text + ' ' + unit_text)} "
                        or (
                            re.fullmatch(r"[A-Z]{3}", qualifier)
                            and qualifier.casefold() != normalized(r.units).casefold()
                        )
                    )
                )
            ):
                raise ValueError(
                    f"Target-price qualifiers need matching source evidence for {r.id}."
                )
        for field, refs in r.support.model_dump().items():
            present = getattr(r, field) is not None and not (
                field == "fiscal_year" and non_fiscal
            )
            refs_ok(refs, present, f"estimate {r.id}.{field}")
            if not present and refs:
                raise ValueError(f"Unavailable {field} must not claim value support.")
        refs_ok(r.note_sources, bool(r.note), f"estimate {r.id}.note")
        if any(fid not in causal_facts for fid in r.reason_fact_ids):
            raise ValueError(
                "Revision reason must resolve to a sourced main-prose broker fact."
            )
        if r.reason == "stated" and not r.reason_fact_ids:
            raise ValueError("Stated revision reason needs evidence.")
        if r.reason != "stated" and r.reason_fact_ids:
            raise ValueError("Unstated reason cannot contain stated-cause evidence.")
        if has_numeric_revision(r) and r.reason == "not_a_revision":
            raise ValueError(
                "Changed metric-year must have a revision reason assessment."
            )
        if not has_numeric_revision(r) and r.reason != "not_a_revision":
            if (
                r.old is not None
                or r.new is None
                or r.reported_revision_pct is not None
            ):
                raise ValueError(
                    "Qualitative revision needs a current value and an unavailable exact prior value/rate."
                )
            if not r.note.strip() or not r.note_sources:
                raise ValueError(
                    "Qualitative revision needs an explicitly sourced note."
                )
    validate_picture(e, quotes)
    m = e.management
    for person in m.named_executives:
        refs_ok(person.sources)
        text = normalized(" ".join(quotes[r] for r in person.sources)).casefold()
        if (
            not person.name.strip()
            or not person.role.strip()
            or normalized(person.name).casefold() not in text
        ):
            raise ValueError(
                "Executive name needs source evidence and role must be nonempty."
            )
        # Roles may paraphrase a sourced appointment or departure. Exact substring
        # matching would reject valid prose without establishing semantic truth.
    refs_ok(m.conversation_sources, m.conversation_reported)
    if not m.conversation_reported and m.conversation_sources:
        raise ValueError(
            "Absent management conversation cannot have conversation evidence."
        )
    a = e.analyst
    for value, refs in [(a.name, a.name_sources), (a.address, a.address_sources)]:
        refs_ok(refs, value is not None)
        if value is None and refs:
            raise ValueError("Unknown analyst field cannot claim identity evidence.")
        if value is not None and (
            not value.strip()
            or normalized(value).casefold()
            not in normalized(" ".join(quotes[r] for r in refs)).casefold()
        ):
            raise ValueError("Analyst identity not present in supplied evidence.")
    if a.address and (
        not a.name
        or normalized(a.name).casefold()
        not in normalized(" ".join(quotes[r] for r in a.address_sources)).casefold()
    ):
        raise ValueError("Analyst address evidence must establish the named recipient.")
    if a.address and not re.fullmatch(r"[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+", a.address):
        raise ValueError("Invalid sourced analyst email address.")
    if word_count(" ".join(f.text for f in e.answer)) > 120:
        raise ValueError("Follow-up answer exceeds 120 words; no truncation applied.")
    return e


def claim(f):
    return Claim(text=f.text, kind=f.kind, sources=f.sources)


def contact(e):
    m = e.management
    if (
        isinstance(e, ExtractionV3)
        and not m.named_executives
        and not m.conversation_reported
    ):
        return Claim(
            text="No executive names or management conversation reported.",
            kind="not_reported",
            sources=[],
        )
    named = "; ".join(f"{p.name} ({p.role})" for p in m.named_executives)
    text = (
        f"Named executives: {named}. " if named else "No named executive is reported. "
    )
    text += (
        "A management conversation is reported."
        if m.conversation_reported
        else "No management conversation is established by the report."
    )
    refs = list(
        dict.fromkeys(
            [r for p in m.named_executives for r in p.sources] + m.conversation_sources
        )
    )
    return Claim(text=text, kind="broker" if refs else "not_reported", sources=refs)


def email(e, request):
    missing = [r for r in e.estimates if is_changed(r) and r.reason == "not_stated"]
    if not missing:
        return None
    a = e.analyst
    # Only metric-year questions; no model-authored body, signature or sender.
    questions = [
        f"What explains the revision to {r.metric} ({r.fiscal_year})?" for r in missing
    ]
    body = (
        "Dear "
        + (a.name or "[TODO: analyst]")
        + ",\n\n"
        + 'Could you clarify the following revisions in your report "'
        + e.title
        + '" ('
        + e.report_date
        + ")?\n\n"
        + "\n".join(f"{i}. {q}" for i, q in enumerate(questions, 1))
        + "\n\nThank you,\n[Your name]"
    )
    return Draft(
        analyst=a.name or "[TODO: analyst]",
        to=a.address or "[TODO: address]",
        subject=f"{request['ticker']}: clarification of estimate revisions",
        body=body,
        sources=list(
            dict.fromkeys(
                a.name_sources
                + a.address_sources
                + [ref for r in missing for ref in row_sources(r)]
            )
        ),
    )


def main_word_count(b):
    return sum(
        word_count(c.text)
        for c in [
            b.takeaway,
            *b.changes,
            *b.drivers,
            b.context,
            b.estimate_picture,
            *b.material,
        ]
    )


def required_ids(e):
    # Cause evidence must survive selection regardless of its display section.
    return {f.id for f in facts(e) if f.required} | {
        fid for row in e.estimates for fid in row.reason_fact_ids
    }


def compose(e, choice, request):
    mandatory = required_ids(e)

    def selected(ids, candidates):
        by_id = {f.id: f for f in candidates}
        if len(ids) != len(set(ids)) or any(fid not in by_id for fid in ids):
            raise ValueError(
                "Composition selected an unknown, duplicate or wrong-section evidence ID."
            )
        if any(f.id in mandatory and f.id not in ids for f in candidates):
            raise ValueError(
                "Composition omitted a mandatory fact; no automatic deletion allowed."
            )
        return [displayed(by_id[fid], e) for fid in ids]

    changes = selected(choice.change_ids, e.changes)
    material = selected(choice.material_ids, e.material) + [
        displayed(f, e) for f in e.conflicts
    ]
    management = contact(e)
    context = Claim(
        text=displayed(e.event, e).text + " " + management.text,
        kind=e.event.kind,
        sources=list(dict.fromkeys(e.event.sources + management.sources)),
    )
    rows = [
        Estimate(
            **{
                k: v
                for k, v in r.model_dump().items()
                if k in Estimate.model_fields and k != "sources"
            },
            sources=row_sources(r),
        )
        for r in e.estimates
    ]
    draft = email(e, request)
    changed = [r for r in e.estimates if is_changed(r)]
    missing = [r for r in changed if r.reason == "not_stated"]
    rationale = (
        "not_applicable"
        if not changed
        else "clear"
        if not missing
        else "unclear"
        if len(missing) == len(changed)
        else "partly_clear"
    )
    b = Brief(
        subject_match=e.subject_match,
        identity=claim(e.identity),
        title=e.title,
        report_date=e.report_date,
        takeaway=displayed(e.takeaway, e),
        changes=changes,
        drivers=[displayed(f, e) for f in e.drivers],
        context=context,
        estimates=rows,
        estimate_picture=picture_claim(e),
        material=material,
        revisions_present=bool(changed),
        rationale=rationale,
        escalation_reason="A material revision has no stated cause in the report."
        if draft
        else None,
        email_draft=draft,
        answer=[displayed(f, e) for f in e.answer],
        limitations=e.limitations,
    )
    validate_evidence(b, {q.line_id for q in e.quotes})
    return b


def composition_packet(e, request):
    required = [e.takeaway, *e.drivers, e.event, *picture_facts(e), *e.conflicts]
    candidate = e.changes + e.material
    packet = dict(
        request={k: request.get(k) for k in ["ticker", "question"]},
        required_facts=[f.model_dump() for f in required],
        contact=contact(e).model_dump(),
        changes=[f.model_dump() for f in e.changes],
        material=[f.model_dump() for f in e.material],
        fixed_word_count=sum(
            word_count(displayed(f, e).text)
            for f in [e.takeaway, *e.drivers, e.event, *e.conflicts]
        )
        + word_count(contact(e).text)
        + word_count(picture_claim(e).text),
        comparison_groups=comparison_provenance(e),
        target_main_words=220,
    )
    used = {ref for f in required + candidate for ref in f.sources} | set(
        picture_claim(e).sources
    )
    packet["quotes"] = [q.model_dump() for q in e.quotes if q.line_id in used]
    import json

    if len(json.dumps(packet, ensure_ascii=False).encode()) > 48000:
        raise ValueError(
            "Composition evidence packet exceeds 48 KB; no silent evidence truncation."
        )
    return packet


def select_facts(e, request):
    """Keep mandatory facts; add whole optional facts in source order when they fit."""
    mandatory = required_ids(e)
    choice = Selection(
        change_ids=[f.id for f in e.changes if f.id in mandatory],
        material_ids=[f.id for f in e.material if f.id in mandatory],
    )
    # Required content can exceed the editorial target; no rejection or retry.
    baseline = compose(e, choice, request)
    count = main_word_count(baseline)
    candidates = [
        (f, section)
        for section, items in [("change_ids", e.changes), ("material_ids", e.material)]
        for f in items
        if f.id not in mandatory
    ]

    def source_order(item):
        refs = [
            tuple(map(int, re.fullmatch(r"p(\d+)l(\d+)", ref).groups()))
            for ref in item[0].sources
            if re.fullmatch(r"p(\d+)l(\d+)", ref)
        ]
        return min(refs, default=(10**9, 10**9))

    seen_text = {
        normalized(c.text).casefold()
        for c in [
            baseline.takeaway,
            *baseline.changes,
            *baseline.drivers,
            baseline.context,
            baseline.estimate_picture,
            *baseline.material,
        ]
    }
    for f, section in sorted(candidates, key=source_order):
        text = displayed(f, e).text
        key = normalized(text).casefold()
        if isinstance(e, ExtractionV3) and key in seen_text:
            continue
        if count + word_count(text) <= 220:
            getattr(choice, section).append(f.id)
            count += word_count(text)
            seen_text.add(key)
    return choice
