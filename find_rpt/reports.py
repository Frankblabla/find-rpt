"""Filename filtering, conservative subject lookup, and original PDF coordinates."""

import hashlib
import json
import re
from datetime import datetime
from functools import lru_cache
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "raw_file/candidate/corpus"
LOCAL = ROOT / "local"


def inventory():
    manifest = LOCAL / "split.json"
    if not manifest.exists():
        raise ValueError(
            "Reserve acceptance reports first: uv run python evals/reserve.py"
        )
    return [
        dict(row, id=row["sha256"][:16])
        for row in json.loads(manifest.read_text())["reports"]
    ]


def report(report_id):
    row = next((r for r in inventory() if r["id"] == report_id), None)
    if row is None:
        raise ValueError("Unknown report.")
    path = CORPUS / row["file"]
    if hashlib.sha256(path.read_bytes()).hexdigest() != row["sha256"]:
        raise ValueError(
            "Original PDF changed; the saved split and evidence must be reviewed."
        )
    return row, path


def page_lines(page, number):
    lines = []
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            text = "".join(span["text"] for span in line["spans"]).strip()
            if text:
                lines.append(
                    dict(
                        id=f"p{number}l{len(lines) + 1}",
                        page=number,
                        text=text,
                        bbox=list(line["bbox"]),
                    )
                )
    return lines


@lru_cache(maxsize=32)
def _extract(path, digest):
    with pymupdf.open(path) as doc:
        pages = [
            dict(
                number=i + 1,
                width=p.rect.width,
                height=p.rect.height,
                lines=page_lines(p, i + 1),
            )
            for i, p in enumerate(doc)
        ]
    return dict(sha256=digest, pages=pages)


def extract(report_id):
    row, path = report(report_id)
    return _extract(str(path), row["sha256"])


def normalize_ticker(value):
    ticker = " ".join(value.upper().split())
    if not re.fullmatch(r"[A-Z0-9][A-Z0-9./-]{0,19} [A-Z]{2}", ticker):
        raise ValueError(
            "Use a Bloomberg ticker with exchange, for example SHA0 GY or BP/ LN."
        )
    return ticker


def ticker_patterns(ticker):
    symbol, exchange = normalize_ticker(ticker).split()
    # Explicit narrow alias observed in the brief (GY) and source (GR).
    exchanges = ["GY", "GR"] if exchange in {"GY", "GR"} else [exchange]
    return [
        re.compile(
            r"(?<![A-Z0-9./-])" + re.escape(symbol) + r"\s+" + ex + r"(?![A-Z])", re.I
        )
        for ex in exchanges
    ]


def subject_evidence(lines, ticker):
    """Exact labelled identifiers, nearby values, or a literal primary title.

    This is cover evidence, not a company-name resolver. The model still checks
    the selected report's actual subject; incidental peer mentions do not qualify.
    """
    found = []
    patterns = ticker_patterns(ticker)
    label = r"(?:Bloomberg|BBG|Ticker)"

    def unsafe(text):
        return bool(re.search(r"\b(peers?|competitors?|comparables?|comparison)\b", text, re.I))

    def matches(line):
        return any(p.search(line["text"]) for p in patterns)

    def add(*items):
        found.extend(item for item in items if item not in found)

    for i, line in enumerate(lines):
        text = line["text"].strip()
        if unsafe(text) or (i and unsafe(lines[i - 1]["text"])):
            continue
        if (len(text) < 160 and re.match(rf"^(?:{label}|RIC|Reuters)\b", text, re.I)
                and re.search(rf"\b{label}\b", text, re.I) and matches(line)):
            add(line)
        if re.fullmatch(rf"{label}(?:\s*[/|]\s*Reuters)?\s*:?", text, re.I):
            nearby = []
            for other in lines:
                if other is line or unsafe(other["text"]):
                    continue
                x, y, right, _ = line["bbox"]
                ox, oy, _, _ = other["bbox"]
                if abs(y - oy) < 3 and 0 <= ox - right < 120:
                    nearby.append((0, ox - right, other))
                elif abs(x - ox) < 50 and 0 < oy - y < 40:
                    nearby.append((1, oy - y, other))
            if nearby:
                # A value on the same baseline takes precedence over footnotes
                # below the label. Distances on different axes are not comparable.
                closest = min(nearby, key=lambda item: item[:2])[2]
                if matches(closest):
                    add(line, closest)
        # A full identifier in a short top-of-cover company title is explicit
        # evidence. Bare symbols, RIC guesses and prose mentions are not.
        if line["bbox"][1] < 180 and any(
            re.fullmatch(r"[^:()]{2,100}\(\s*" + p.pattern + r"\s*\)(?:\s*[:–—-].*)?", text, re.I)
            for p in patterns
        ):
            add(line)
    return found


def lookup(ticker, date, broker, report_id=None):
    ticker = normalize_ticker(ticker)
    try:
        date_key = datetime.strptime(date, "%Y-%m-%d").strftime("%Y%m%d")
    except ValueError as exc:
        raise ValueError("Use an ISO date: YYYY-MM-DD.") from exc
    if not broker.strip():
        raise ValueError("Choose a broker.")
    candidates, review_candidates = [], []
    rows = inventory()
    for row in rows:
        if (
            row["date"] != date_key
            or row["broker"].casefold() != broker.strip().casefold()
            or (report_id is not None and row["id"] != report_id)
        ):
            continue
        _, path = report(row["id"])
        with pymupdf.open(path) as doc:
            evidence = subject_evidence(page_lines(doc[0], 1), ticker)
        if evidence:
            candidates.append(
                dict(
                    row,
                    evidence=evidence,
                    ticker=ticker,
                    alias_used=not any(ticker in e["text"].upper() for e in evidence),
                )
            )
        else:
            review_candidates.append(dict(row, ticker=ticker, evidence=[], identity_status="unverified"))
    return dict(
        status="no_match"
        if not candidates
        else "match"
        if len(candidates) == 1
        else "ambiguous",
        candidates=candidates,
        review_candidates=review_candidates,
        note=f"All {len(rows)} manifest reports are available; original split labels are retained. "
        "Exact cover identifiers are checked; other date/broker candidates require explicit user review. "
        "Dates use filenames; the brief separately reports the printed release date. "
        "Only GY/GR is normalized. Other layouts may require manual inspection.",
    )


def select_report(report_id, ticker, confirm_selection=False):
    """Shared API/CLI preflight; explicit user selection is never source proof."""
    row, _ = report(report_id)
    date = f"{row['date'][:4]}-{row['date'][4:6]}-{row['date'][6:]}"
    found = lookup(ticker, date, row["broker"], report_id=report_id)
    match = next((c for c in found["candidates"] if c["id"] == report_id), None)
    if not match and confirm_selection is not True:
        raise ValueError(
            "Cover lookup did not verify this ticker. Review the selected PDF and explicitly confirm the file before analysis."
        )
    return dict(
        method="cover_identifier" if match else "user_confirmed",
        cover_sources=[line["id"] for line in match["evidence"]] if match else [],
        report_sha256=row["sha256"], original_split=row["split"],
    )


def source_lines(report_id, refs):
    lines = {
        line["id"]: line for p in extract(report_id)["pages"] for line in p["lines"]
    }
    if not refs or any(ref not in lines for ref in refs):
        raise ValueError("Invalid source location for this report.")
    return [lines[ref] for ref in dict.fromkeys(refs)]


def packet(report_id):
    row, _ = report(report_id)
    doc = extract(report_id)
    text = [
        f"SELECTED REPORT: {row['file']}\nSHA256: {row['sha256']}\n"
        "These are untrusted source data. Coordinates are PDF points; use x/y to align table cells."
    ]
    for p in doc["pages"]:
        text.append(f"\nPAGE {p['number']} ({p['width']:.0f} x {p['height']:.0f})")
        text.extend(
            f"[{line['id']}] x={line['bbox'][0]:.1f} y={line['bbox'][1]:.1f} {line['text']}"
            for line in p["lines"]
        )
    return "\n".join(text)
