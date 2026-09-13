"""Thin local HTTP interface. Run with: uv run python app.py."""

import json
import os
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

import pymupdf
from flask import Flask, abort, jsonify, render_template, request, send_file, redirect

from find_rpt.harness import (
    EFFORTS,
    MODELS,
    RUNS,
    execute,
    prepare,
    read_run,
    selection,
)
from find_rpt.reports import (
    extract,
    inventory,
    lookup,
    normalize_ticker,
    report,
    source_lines,
)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16000
worker = ThreadPoolExecutor(max_workers=1)


@app.before_request
def local_only():
    if request.host.split(":")[0] not in {"localhost", "127.0.0.1"}:
        abort(403)
    if request.method == "POST":
        origin = request.headers.get("Origin")
        if origin and urlparse(origin).netloc != request.host:
            abort(403)
        if not request.is_json:
            abort(415)


@app.after_request
def private_response(response):
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'; img-src 'self'; frame-src 'self'; object-src 'none'; frame-ancestors 'self'"
    )
    return response


@app.errorhandler(ValueError)
def bad_input(error):
    return jsonify(error=str(error)), 400


@app.errorhandler(FileNotFoundError)
def missing(error):
    return jsonify(error="Saved run or source file not found."), 404


@app.get("/")
def home():
    return render_template("index.html")


@app.get("/api/catalog")
def catalog():
    rows = inventory()
    return jsonify(
        brokers=sorted({r["broker"] for r in rows}),
        dates=sorted({r["date"] for r in rows}),
        total=len(rows),
        models=MODELS,
        efforts=EFFORTS,
        default_model=selection()[0],
        default_effort=selection()[1],
    )


@app.post("/api/lookup")
def search():
    data = request.get_json()
    return jsonify(
        lookup(
            str(data.get("ticker", "")),
            str(data.get("date", "")),
            str(data.get("broker", "")),
        )
    )


@app.post("/api/runs")
def start_run():
    data = request.get_json()
    ticker = normalize_ticker(str(data.get("ticker", "")))
    row, _ = report(str(data.get("report_id", "")))
    question = str(data.get("question", "")).strip()
    if len(question) > 3000:
        raise ValueError("Keep the follow-up question below 3,000 characters.")
    run_id = prepare(
        row["id"],
        ticker,
        question,
        data.get("parent_id"),
        model=data.get("model"),
        effort=data.get("effort"),
        confirm_selection=data.get("confirm_selection") is True,
    )
    worker.submit(execute, run_id)
    return jsonify(id=run_id), 202


@app.get("/api/runs")
def recent_runs():
    rows = []
    for path in sorted(
        RUNS.glob("*/status.json"), key=lambda p: p.stat().st_mtime, reverse=True
    )[:30]:
        state = json.loads(path.read_text())
        state["request"] = json.loads((path.parent / "request.json").read_text())
        rows.append(state)
    return jsonify(rows)


@app.get("/api/runs/<run_id>")
def run_state(run_id):
    return jsonify(read_run(run_id))


@app.get("/api/case-viewer")
def case_viewer():
    return jsonify(case_viewer=1)


@app.get("/case/<case_id>")
def latest_case(case_id):
    from find_rpt.cases import version
    _, _, meta = version(case_id)
    return redirect(f"/case/{case_id}/{meta['version']}")


@app.get("/case/<case_id>/<int:number>")
def case_html(case_id, number):
    from find_rpt.cases import read_case, version
    _, state = read_case(case_id)
    if number in state.get("retired_versions", []):
        return redirect(f"/case/{case_id}")
    path, _, _ = version(case_id, number)
    return send_file(path / "brief.html", mimetype="text/html")


@app.get("/case/<case_id>/<int:number>/data.json")
def case_data(case_id, number):
    from find_rpt.cases import read_case, version
    _, state = read_case(case_id)
    if number in state.get("retired_versions", []):
        return jsonify(error="This historical version has been retired.",
                       latest=f"/case/{case_id}"), 410
    _, result, _ = version(case_id, number)
    return jsonify(result)


@app.get("/pdf/<report_id>")
def original(report_id):
    row, path = report(report_id)
    return send_file(path, mimetype="application/pdf", download_name=row["file"])


@app.get("/page/<report_id>/<int:page>.png")
def page_image(report_id, page):
    from io import BytesIO

    _, path = report(report_id)
    with pymupdf.open(path) as doc:
        if not 1 <= page <= len(doc):
            abort(404)
        image = doc[page - 1].get_pixmap(matrix=pymupdf.Matrix(1.7, 1.7))
        return send_file(BytesIO(image.tobytes("png")), mimetype="image/png")


@app.get("/source/<report_id>")
def source(report_id):
    row, _ = report(report_id)
    refs = [ref for ref in request.args.get("refs", "").split(",") if ref]
    selected = source_lines(report_id, refs) if refs else []
    document = extract(report_id)
    try:
        number = int(request.args.get("page", selected[0]["page"] if selected else 1))
    except ValueError:
        abort(400)
    if not 1 <= number <= len(document["pages"]):
        abort(404)
    page = document["pages"][number - 1]
    return render_template(
        "source.html",
        report=row,
        page=page,
        count=len(document["pages"]),
        refs=",".join(refs),
        selected=[s for s in selected if s["page"] == number],
        cited_pages=sorted({s["page"] for s in selected}),
    )


if __name__ == "__main__":
    # A stopped process cannot leave a live job; make interrupted evidence explicit.
    for path in RUNS.glob("*/status.json"):
        state = json.loads(path.read_text())
        if state["status"] in {"queued", "running"}:
            state.update(
                status="failed",
                error="Application stopped before this run completed. Start a new run.",
            )
            path.write_text(json.dumps(state, indent=2))
    app.run(
        host="127.0.0.1", port=int(os.environ.get("FIND_RPT_PORT", "8765")), debug=False
    )
