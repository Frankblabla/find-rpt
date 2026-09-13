"""Durable report cases and immutable artifacts. No model invocation lives here."""

import hashlib
import json
import re
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import Field

from find_rpt import reports
from find_rpt.evidence import (
    ExtractionV3,
    Fact,
    Quote,
    comparison_provenance,
    complete_quotes,
    facts,
    main_word_count,
    normalized,
    select_facts,
    compose,
    validate_extraction,
)
from find_rpt.schema import StrictModel, Draft, comparisons


class AnswerClaim(StrictModel):
    text: str = Field(min_length=1)
    kind: Literal["broker", "not_reported"] = "broker"
    sources: list[str]


class Answer(StrictModel):
    question: str = Field(min_length=1)
    base_version: int = Field(ge=1)
    claims: list[AnswerClaim] = Field(min_length=1)
    quotes: list[Quote] = Field(default_factory=list)


class Checkpoint(StrictModel):
    """An explicitly partial first read, before full estimate extraction."""

    title: str = Field(min_length=1)
    report_date: str = Field(min_length=1)
    subject_match: Literal["confirmed", "ambiguous", "mismatch"]
    identity: AnswerClaim
    claims: list[AnswerClaim] = Field(min_length=1)
    quotes: list[Quote] = Field(default_factory=list)
    pending: list[str] = Field(min_length=1)


def now():
    return datetime.now(timezone.utc).isoformat()


def load(path):
    return json.loads(path.read_text())


def save(path, value):
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")
    temp.replace(path)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def case_path(case_id):
    if not re.fullmatch(r"[a-f0-9]{32}", case_id):
        raise ValueError("Invalid case ID.")
    return reports.LOCAL / "cases" / case_id


def session_path(session):
    if not re.fullmatch(r"[a-zA-Z0-9_-]{1,80}", session):
        raise ValueError("Invalid session ID.")
    return reports.LOCAL / "case-sessions" / (session + ".json")


def attach(case_id, session):
    read_case(case_id)
    path = session_path(session)
    path.parent.mkdir(parents=True, exist_ok=True)
    save(path, dict(case_id=case_id))


def resolve(case_id=None, session=None):
    if case_id:
        return case_id
    if session and session_path(session).exists():
        return load(session_path(session))["case_id"]
    raise ValueError(
        "No active case. Start a report or attach an existing case to this session."
    )


def read_case(case_id):
    folder = case_path(case_id)
    state = load(folder / "case.json")
    row, _ = reports.report(state["report_id"])
    if (
        row["sha256"] != state["report_sha256"]
        or digest(folder / "report.txt") != state["packet_sha256"]
    ):
        raise ValueError("Original report or frozen case packet changed.")
    return folder, state


@contextmanager
def changing(case_id, base_version):
    folder, _ = read_case(case_id)
    lock = folder / ".write-lock"
    try:
        handle = lock.open("x")
    except FileExistsError as exc:
        raise ValueError(
            "Another write is in progress. Inspect the case before retrying."
        ) from exc
    try:
        handle.close()
        state = load(folder / "case.json")
        if base_version != state["latest_version"]:
            raise ValueError(
                "Stale version. Read case context before changing the artifact."
            )
        yield folder, state
    finally:
        lock.unlink()


def start(ticker, date, broker, report_id=None, confirm=False, session=None):
    if session:
        session_path(session)
    found = reports.lookup(ticker, date, broker, report_id=report_id)
    options = found["candidates"] + (
        found["review_candidates"] if confirm and report_id else []
    )
    if len(options) != 1:
        raise ValueError(
            "Choose one verified report, or review a PDF and supply its report ID with --confirm-selection."
        )
    row = options[0]
    selected = reports.select_report(row["id"], ticker, confirm)
    selected["recorded_at"] = now()
    case_id = uuid.uuid4().hex
    folder = case_path(case_id)
    folder.mkdir(parents=True)
    for name in ["versions", "answers", "work"]:
        (folder / name).mkdir()
    (folder / "report.txt").write_text(reports.packet(row["id"]))
    save(folder / "extraction-schema.json", ExtractionV3.model_json_schema())
    save(folder / "answer-schema.json", Answer.model_json_schema())
    save(folder / "checkpoint-schema.json", Checkpoint.model_json_schema())
    request = dict(
        report_id=row["id"],
        ticker=reports.normalize_ticker(ticker),
        broker=row["broker"],
        lookup_date=row["date"],
        selection=selected,
        question="",
        prior_questions=[],
    )
    save(folder / "request.json", request)
    save(
        folder / "case.json",
        dict(
            id=case_id,
            report_id=row["id"],
            ticker=request["ticker"],
            report_sha256=row["sha256"],
            packet_sha256=digest(folder / "report.txt"),
            created_at=now(),
            latest_version=0,
            latest_answer=0,
            selection=selected,
        ),
    )
    if session:
        attach(case_id, session)
    return context(case_id)


def version(case_id, number=None):
    folder, state = read_case(case_id)
    number = state["latest_version"] if number is None else number
    if not isinstance(number, int) or number < 1:
        raise ValueError("Create the first brief before this operation.")
    path = folder / "versions" / f"{number:04d}"
    meta = load(path / "version.json")
    for name, expected in meta["files_sha256"].items():
        if digest(path / name) != expected:
            raise ValueError(
                "Saved artifact changed; original versions must remain immutable."
            )
    return path, load(path / "result.json"), meta


def context(case_id):
    folder, state = read_case(case_id)
    out = dict(
        **state,
        directory=str(folder),
        request_path=str(folder / "request.json"),
        report_path=str(folder / "report.txt"),
        source_pdf_path=str(reports.CORPUS / reports.report(state["report_id"])[0]["file"]),
        work_directory=str(folder / "work"),
        extraction_schema=str(folder / "extraction-schema.json"),
        answer_schema=str(folder / "answer-schema.json"),
        extraction_instructions=str(
            reports.ROOT / ".agents/skills/find-rpt/references/extract.md"
        ),
    )
    if (folder / "checkpoint-schema.json").exists():
        out["checkpoint_schema"] = str(folder / "checkpoint-schema.json")
    if state["latest_version"]:
        path, result, meta = version(case_id)
        previous = (
            version(case_id, meta["parent_version"])[1]
            if meta["parent_version"]
            and meta["parent_version"] not in state.get("retired_versions", [])
            else None
        )
        out.update(
            result_path=str(path / "result.json"),
            evidence_path=str(path / "evidence.json"),
            html_path=str(path / "brief.html"),
            html_url=meta["url"],
            view=result["view"],
            periods=list(
                dict.fromkeys(r["fiscal_year"] for r in result["brief"]["estimates"])
            ),
            current_prose={
                k: result["brief"][k]
                for k in [
                    "title",
                    "takeaway",
                    "changes",
                    "drivers",
                    "context",
                    "material",
                ]
            },
            email_draft=result["brief"]["email_draft"],
            last_change=meta.get("changes", describe_change(previous, result)),
            artifact_status=result.get("artifact_status", "full"),
        )
    recent = sorted((folder / "answers").glob("*.json"))[-5:]
    out["recent_answers"] = [
        {k: answer[k] for k in ["id", "question", "base_version", "claims"]}
        for answer in [read_answer(case_id, int(p.stem)) for p in recent]
    ]
    return out


def describe_change(previous, result):
    """Expose editorial removals as well as additions to the conversation."""
    before = previous["brief"] if previous else {}
    after = result["brief"]

    def prose(brief):
        texts = []
        for field in [
            "takeaway",
            "changes",
            "drivers",
            "context",
            "estimate_picture",
            "material",
        ]:
            value = brief.get(field, [])
            claims = value if isinstance(value, list) else [value]
            texts.extend(claim["text"] for claim in claims)
        return texts

    return {
        "changed_sections": [key for key in after if before.get(key) != after[key]],
        "added_prose": [text for text in prose(after) if text not in prose(before)],
        "removed_prose": [text for text in prose(before) if text not in prose(after)],
        "view_changed": previous is None or previous["view"] != result["view"],
    }


def original_lines(case_id):
    _, state = read_case(case_id)
    return [
        line
        for page in reports.extract(state["report_id"])["pages"]
        for line in page["lines"]
    ]


def read_sources(case_id=None, report_id=None, refs=None, query=None, page=None):
    if case_id:
        _, state = read_case(case_id)
        report_id = state["report_id"]
    if not report_id:
        raise ValueError("Specify a case or report ID.")
    lines = [line for p in reports.extract(report_id)["pages"] for line in p["lines"]]
    if refs:
        wanted = set(refs)
        if not wanted.issubset({line["id"] for line in lines}):
            raise ValueError("Unknown source line.")
        indexes = [i for i, line in enumerate(lines) if line["id"] in wanted]
    elif query:
        indexes = [
            i
            for i, line in enumerate(lines)
            if query.casefold() in line["text"].casefold()
        ][:12]
    elif page is not None:
        return [line for line in lines if line["page"] == page]
    else:
        raise ValueError("Choose --refs, --query or --page.")
    keep = {
        j
        for i in indexes
        for j in range(max(0, i - 2), min(len(lines), i + 3))
        if lines[j]["page"] == lines[i]["page"]
    }
    return [lines[i] for i in sorted(keep)]


def checked_evidence(case_id, value):
    lines = {line["id"]: line["text"] for line in original_lines(case_id)}
    e = validate_extraction(ExtractionV3.model_validate(value), lines)
    check_identity(case_id, e.subject_match)
    return e


def check_identity(case_id, subject_match):
    _, state = read_case(case_id)
    if subject_match == "mismatch" or (
        subject_match == "ambiguous"
        and state["selection"]["method"] != "user_confirmed"
    ):
        raise ValueError(
            "Report identity is not established; no brief or draft can be published."
        )


def check_claims(case_id, claims, quotes):
    """Shared source checks for short answers and partial first reads."""
    lines = {line["id"]: line["text"] for line in original_lines(case_id)}
    complete_quotes(quotes, [ref for claim in claims for ref in claim.sources], lines)
    by_id = {q.line_id: q.text for q in quotes}
    if len(by_id) != len(quotes):
        raise ValueError("Duplicate quote ID.")
    for ref, text in by_id.items():
        if ref not in lines or normalized(text) != normalized(lines[ref]):
            raise ValueError(f"Quote differs from original {ref}.")
    for claim in claims:
        if (
            not claim.text.strip()
            or (claim.kind == "broker" and not claim.sources)
            or any(r not in by_id for r in claim.sources)
        ):
            raise ValueError(
                "Every sourced answer clause needs complete declared source lines."
            )


def assemble(case_id, e):
    folder, state = read_case(case_id)
    request = load(folder / "request.json")
    b = compose(e, select_facts(e, request), request)
    row, _ = reports.report(state["report_id"])
    return dict(
        artifact_status="full",
        brief=b.model_dump(),
        evidence=e.model_dump(),
        request=request,
        report=row,
        comparisons=[comparisons(r) for r in b.estimates],
        comparison_provenance=comparison_provenance(e),
        main_word_count=main_word_count(b),
        composition_notice=(
            f"Required prose is {main_word_count(b)} words, above the 220-word target. Required facts are retained."
            if main_word_count(b) > 220
            else None
        ),
        view=dict(years=[], detail="full"),
    )


def write_version(folder, state, result, reason):
    from find_rpt.render import render_html, base_url

    number = (
        max(
            [int(p.name) for p in (folder / "versions").iterdir() if p.name.isdigit()]
            + [0]
        )
        + 1
    )
    meta = dict(
        version=number,
        parent_version=state["latest_version"],
        created_at=now(),
        reason=reason,
        url=f"{base_url()}/case/{state['id']}/{number}",
        research_source_sha256=state["report_sha256"],
    )
    previous = version(state["id"])[1] if state["latest_version"] else None
    meta["changes"] = describe_change(previous, result)
    html = render_html(result, state["id"], meta)
    path = folder / "versions" / f"{number:04d}"
    path.mkdir()
    save(path / "result.json", result)
    save(path / "evidence.json", result["evidence"])
    (path / "brief.html").write_text(html)
    meta["files_sha256"] = {
        name: digest(path / name)
        for name in ["result.json", "evidence.json", "brief.html"]
    }
    save(path / "version.json", meta)
    state["latest_version"] = number
    save(folder / "case.json", state)
    return dict(
        case_id=state["id"],
        version=number,
        html_path=str(path / "brief.html"),
        source_pdf_sha256=state["report_sha256"],
        artifact_sha256=meta["files_sha256"],
        email_draft=result["brief"].get("email_draft"),
        revisions_present=result["brief"].get("revisions_present"),
        rationale=result["brief"].get("rationale"),
        html_url=meta["url"],
        result_path=str(path / "result.json"),
        main_words=result["main_word_count"],
        reason=reason,
        changes=meta["changes"],
        artifact_status=result.get("artifact_status", "full"),
    )


def publish(case_id, evidence_file, base_version):
    with changing(case_id, base_version) as (folder, state):
        e = checked_evidence(case_id, load(Path(evidence_file)))
        return write_version(
            folder, state, assemble(case_id, e), "Validated evidence publication"
        )


def checkpoint(case_id, evidence_file, base_version):
    """Save a usable first read; never replace an existing artifact with a fallback."""
    with changing(case_id, base_version) as (folder, state):
        if state["latest_version"]:
            raise ValueError(
                "A saved artifact already exists. Use deliver or publish the full extraction."
            )
        value = Checkpoint.model_validate(load(Path(evidence_file)))
        check_identity(case_id, value.subject_match)
        if value.identity.kind != "broker" or not value.identity.sources:
            raise ValueError("Partial identity needs original report evidence.")
        check_claims(case_id, [value.identity, *value.claims], value.quotes)
        if any(not text.strip() for text in value.pending):
            raise ValueError("Describe the unfinished work in pending.")
        request = load(folder / "request.json")
        row, _ = reports.report(state["report_id"])
        # This display projection is intentionally not a full Brief/ExtractionV3.
        brief = dict(
            title=value.title,
            report_date=value.report_date,
            subject_match=value.subject_match,
            identity=value.identity.model_dump(),
            takeaway=value.claims[0].model_dump(),
            changes=[],
            drivers=[],
            material=[c.model_dump() for c in value.claims[1:]],
            context=dict(
                text="Full analysis is pending.", kind="not_reported", sources=[]
            ),
            estimates=[],
            email_draft=None,
            limitations=value.pending,
        )
        result = dict(
            artifact_status="partial",
            brief=brief,
            evidence=value.model_dump(),
            request=request,
            report=row,
            comparisons=[],
            comparison_provenance=[],
            main_word_count=sum(len(c.text.split()) for c in value.claims),
            view=dict(years=[], detail="full"),
        )
        return write_version(
            folder,
            state,
            result,
            "Partial first read; full extraction and review are pending",
        )


def deliver(case_id):
    """Recover the latest verified artifact link without another model invocation."""
    folder, state = read_case(case_id)
    if not state["latest_version"]:
        return dict(
            case_id=case_id,
            artifact_status="unavailable",
            message="No saved HTML exists yet.",
        )
    path, result, meta = version(case_id)
    return dict(
        case_id=case_id,
        version=meta["version"],
        artifact_status=result.get("artifact_status", "full"),
        html_url=meta["url"],
        html_path=str(path / "brief.html"),
        source_pdf_sha256=state["report_sha256"],
        artifact_sha256=meta["files_sha256"],
        email_draft=result["brief"].get("email_draft"),
        revisions_present=result["brief"].get("revisions_present"),
        rationale=result["brief"].get("rationale"),
        pending=result["brief"].get("limitations", [])
        if result.get("artifact_status") == "partial"
        else [],
        review_notes=[
            str(p)
            for p in sorted(
                (folder / "work").glob(f"review-version-{meta['version']}*.md")
            )
            if re.match(rf"review-version-{meta['version']}(?:\D|$)", p.name)
        ],
        review_status="Same-agent review is not independently verified; inspect the note's scope if present.",
    )


def read_answer(case_id, number):
    folder, state = read_case(case_id)
    path = folder / "answers" / f"{number:04d}.json"
    if digest(path) != state.get("answer_hashes", {}).get(str(number)):
        raise ValueError(
            "Saved answer changed; original answers must remain immutable."
        )
    return load(path)


def save_answer(case_id, answer_file):
    answer = Answer.model_validate(load(Path(answer_file)))
    with changing(case_id, answer.base_version) as (folder, state):
        version(case_id)
        check_claims(case_id, answer.claims, answer.quotes)
        number = (
            max([int(p.stem) for p in (folder / "answers").glob("*.json")] + [0]) + 1
        )
        value = dict(id=number, created_at=now(), **answer.model_dump())
        save(folder / "answers" / f"{number:04d}.json", value)
        state["latest_answer"] = number
        state.setdefault("answer_hashes", {})[str(number)] = digest(
            folder / "answers" / f"{number:04d}.json"
        )
        save(folder / "case.json", state)
        from find_rpt.render import source_url

        return dict(
            case_id=case_id,
            answer_id=number,
            base_version=answer.base_version,
            question=answer.question,
            claims=[
                dict(
                    **c.model_dump(),
                    source_url=source_url(state["report_id"], c.sources),
                )
                for c in answer.claims
            ],
            html_unchanged=True,
        )


def revise(case_id, answer_id, base_version, draft=False):
    with changing(case_id, base_version) as (folder, state):
        _, result, _ = version(case_id)
        answer = read_answer(case_id, answer_id)
        if result.get("artifact_status") == "partial":
            raise ValueError(
                "The answer is saved. Complete extraction with publish before amending or drafting; the partial HTML remains available."
            )
        if answer["base_version"] != base_version:
            raise ValueError(
                "This answer belongs to another version. Review the current context first."
            )
        e = checked_evidence(case_id, result["evidence"])
        if draft:
            a = e.analyst
            refs = list(
                dict.fromkeys(
                    a.name_sources
                    + a.address_sources
                    + [r for c in answer["claims"] for r in c["sources"]]
                )
            )
            d = Draft(
                analyst=a.name or "[TODO: analyst]",
                to=a.address or "[TODO: address]",
                subject=f"{state['ticker']}: report clarification",
                body="Dear "
                + (a.name or "[TODO: analyst]")
                + ",\n\nCould you clarify the following points in your report?\n\n"
                + "\n".join(
                    f"{i}. {c['text']}" for i, c in enumerate(answer["claims"], 1)
                )
                + "\n\nThank you,\n[Your name]",
                sources=refs,
            )
            result["brief"].update(
                email_draft=d.model_dump(),
                escalation_reason="Clarification draft requested by the user.",
            )
            result["draft_origin"] = dict(
                answer_id=answer_id, source="user_request", quotes=answer["quotes"]
            )
        else:
            used = {f.id for f in facts(e)}
            for claim in answer["claims"]:
                n = 1
                while f"f{n}" in used:
                    n += 1
                used.add(f"f{n}")
                e.material.append(Fact(id=f"f{n}", required=True, **claim))
            quotes = {q.line_id: q for q in e.quotes}
            quotes.update({q["line_id"]: Quote(**q) for q in answer["quotes"]})
            e.quotes = list(quotes.values())
            e = checked_evidence(case_id, e.model_dump())
            revised = assemble(case_id, e)
            revised["view"] = result["view"]
            if result.get("draft_origin"):
                revised["draft_origin"] = result["draft_origin"]
                revised["brief"]["email_draft"] = result["brief"]["email_draft"]
                revised["brief"]["escalation_reason"] = result["brief"][
                    "escalation_reason"
                ]
            result = revised
        return write_version(
            folder,
            state,
            result,
            f"{'Draft' if draft else 'Content update'} from saved answer {answer_id}",
        )


def rerender(case_id, base_version, years=None, detail=None):
    with changing(case_id, base_version) as (folder, state):
        _, result, _ = version(case_id)
        if years is not None:
            available = {row["fiscal_year"] for row in result["brief"]["estimates"]}
            if set(years) - available:
                raise ValueError(
                    "Unknown period. Available: " + ", ".join(sorted(available))
                )
            result["view"]["years"] = years
        if detail:
            if detail not in {"compact", "full"}:
                raise ValueError("Choose compact or full detail.")
            result["view"]["detail"] = detail
        return write_version(
            folder, state, result, "Presentation only; research data unchanged"
        )
