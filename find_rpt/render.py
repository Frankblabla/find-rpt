"""Render a saved, validated result as a portable HTML reading artifact."""

import os
from urllib.parse import urlencode

from flask import Flask, render_template

from find_rpt.reports import ROOT

renderer = Flask(__name__, template_folder=str(ROOT / "templates"))


def base_url():
    return f"http://127.0.0.1:{int(os.environ.get('FIND_RPT_PORT', '8765'))}"


def source_url(report_id, refs):
    return (
        f"{base_url()}/source/{report_id}?" + urlencode({"refs": ",".join(refs)})
        if refs
        else None
    )


def number(value):
    return "—" if value is None else f"{value:,.4f}".rstrip("0").rstrip(".")


def relative(value):
    return "—" if value is None else f"{value:+.2f}%"


def delta(pair, units):
    if pair["absolute"] is None:
        return "—"
    if units == "%":
        return f"{pair['absolute']:+.2f} pp"
    return relative(pair["percent"])


def render_html(result, case_id, meta):
    b = result["brief"]
    years = result["view"]["years"]
    rows = []
    charts = []
    for index, (row, comparison) in enumerate(
        zip(b["estimates"], result["comparisons"])
    ):
        if years and row["fiscal_year"] not in years:
            continue
        reason = result["evidence"]["estimates"][index]["reason"]
        revision = (
            "Not a revision"
            if reason == "not_a_revision"
            else (
                f"{row['reported_revision_bps']:+g} bps reported"
                if row.get("reported_revision_bps") is not None
                else relative(row["reported_revision_pct"]) + " reported"
                if row["reported_revision_pct"] is not None
                else delta(comparison["revision"], row["units"])
            )
        )
        rows.append(dict(row=row, comparison=comparison, revision=revision))
        points = [
            (label, row[key])
            for label, key in [
                ("Prior", "old"),
                ("Stated", "new"),
                ("Consensus", "consensus_after"),
            ]
            if row[key] is not None
        ]
        if len(points) >= 2 and len(charts) < 3:
            lower = min([0] + [v for _, v in points])
            upper = max([0] + [v for _, v in points])
            span = upper - lower or 1

            def x(value, lower=lower, span=span):
                return 120 + 240 * (value - lower) / span

            charts.append(
                dict(
                    row=row,
                    height=30 * len(points) + 8,
                    zero=x(0),
                    points=[
                        dict(
                            label=label,
                            value=number(value),
                            x=min(x(0), x(value)),
                            width=max(1, abs(x(value) - x(0))),
                            y=12 + 30 * i,
                        )
                        for i, (label, value) in enumerate(points)
                    ],
                )
            )
    with renderer.app_context():
        return render_template(
            "brief.html",
            result=result,
            b=b,
            rows=rows,
            charts=charts,
            meta=meta,
            case_id=case_id,
            base=base_url(),
            number=number,
            delta=delta,
            source=lambda refs: source_url(result["report"]["id"], refs),
        )
