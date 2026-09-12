"""Explicit offline revalidation of a failed extraction. Never invokes a model."""

import hashlib
import json
import time
import uuid
import platform
import pymupdf
from datetime import datetime, timezone

from find_rpt.evidence import (
    Extraction,
    ExtractionV3,
    comparison_provenance,
    validate_extraction,
    main_word_count,
)
from find_rpt.harness import (
    ROOT,
    run_directory,
    save,
    parse_claude_output,
    compose_stage,
)
from find_rpt.reports import report, packet, extract
from find_rpt.schema import Brief, comparisons


def revalidate(source_run_id):
    source = run_directory(source_run_id)
    source_state = json.loads((source / "status.json").read_text())
    if source_state.get("status") != "failed" or source_state.get("workflow") not in {
        "evidence-local-composition-v2",
        "evidence-local-composition-v3",
    }:
        raise ValueError(
            "Offline revalidation requires a failed versioned extraction attempt."
        )
    contract = ExtractionV3 if source_state["workflow"].endswith("v3") else Extraction
    raw_path = source / "extraction/harness-output.json"
    payload = json.loads(raw_path.read_text())
    request = json.loads((source / "request.json").read_text())
    row, _ = report(request["report_id"])
    if row["sha256"] != source_state.get("report_sha256"):
        raise ValueError("Original report hash differs from the source run.")
    if (source / "report.txt").read_text() != packet(row["id"]):
        raise ValueError(
            "Frozen report packet differs from the unchanged original extraction."
        )
    source_stage = json.loads((source / "extraction/status.json").read_text())
    for name, filename in [
        ("prompt", "prompt.txt"),
        ("skill", "SKILL.md"),
        ("schema", "schema.json"),
    ]:
        if (
            hashlib.sha256((source / "extraction" / filename).read_bytes()).hexdigest()
            != source_stage[name + "_sha256"]
        ):
            raise ValueError(f"Frozen source {name} hash changed.")

    run_id = uuid.uuid4().hex
    directory = run_directory(run_id)
    directory.mkdir(parents=True)
    stage = directory / "revalidation"
    stage.mkdir()
    (directory / "composition").mkdir()
    save(directory / "request.json", request)
    (directory / "report.txt").write_bytes((source / "report.txt").read_bytes())
    save(directory / "schema.json", Brief.model_json_schema())
    save(stage / "schema.json", contract.model_json_schema())
    # Preserve the raw extraction exactly, with lineage; this is not a new response.
    (stage / "source-harness-output.json").write_bytes(raw_path.read_bytes())
    lineage = dict(
        source_run_id=source_run_id,
        offline_revalidation=True,
        model_invocations=0,
        source_files_sha256={
            str(p.relative_to(source)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [
                source / "request.json",
                source / "report.txt",
                source / "status.json",
                raw_path,
                source / "extraction/prompt.txt",
                source / "extraction/SKILL.md",
                source / "extraction/schema.json",
                source / "extraction/status.json",
            ]
        },
    )
    save(directory / "lineage.json", lineage)
    start = time.monotonic()
    meta = dict(
        id=run_id,
        status="running",
        active_stage="revalidation",
        workflow=source_state["workflow"],
        source_run_id=source_run_id,
        offline_revalidation=True,
        model_invocations=0,
        harness="Local revalidation",
        configured_model=request["model"],
        effort=request["effort"],
        effective_models=[],
        effective_effort=None,
        estimated_cost_usd=0,
        cost_basis="No new model call. The original model cost belongs only to the source run.",
        started_at=datetime.now(timezone.utc).isoformat(),
        report_id=row["id"],
        report_sha256=row["sha256"],
        python_version=platform.python_version(),
        pymupdf_version=pymupdf.VersionBind,
        source_sha256={
            str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [
                ROOT / "app.py",
                *sorted((ROOT / "find_rpt").glob("*.py")),
                *sorted((ROOT / "static").glob("*")),
            ]
        },
    )
    save(directory / "status.json", meta)
    validation_meta = dict(
        status="running",
        implementation="local",
        model_invocations=0,
        source_run_id=source_run_id,
        source_sha256=meta["source_sha256"],
    )
    save(stage / "status.json", validation_meta)
    try:
        lines = {
            line["id"]: line["text"]
            for page in extract(row["id"])["pages"]
            for line in page["lines"]
        }
        evidence = validate_extraction(parse_claude_output(payload, contract), lines)
        save(stage / "validated.json", evidence.model_dump())
        validation_meta.update(
            status="complete", elapsed_seconds=round(time.monotonic() - start, 4)
        )
        meta["active_stage"] = "composition"
        response = compose_stage(directory / "composition", evidence, request)
        save(directory / "response.json", response.model_dump())
        result = dict(
            brief=response.model_dump(),
            comparisons=[comparisons(e) for e in response.estimates],
            report=row,
            request=request,
            run_id=run_id,
            source_run_id=source_run_id,
            offline_revalidation=True,
            model_invocations=0,
            evidence=evidence.model_dump(),
            comparison_provenance=comparison_provenance(evidence),
            main_word_count=main_word_count(response),
            lineage=lineage,
            runtime={
                k: meta[k]
                for k in [
                    "harness",
                    "configured_model",
                    "effort",
                    "effective_models",
                    "effective_effort",
                    "estimated_cost_usd",
                    "cost_basis",
                    "offline_revalidation",
                    "model_invocations",
                ]
            },
        )
        save(directory / "result.json", result)
        meta.update(status="complete", main_word_count=main_word_count(response))
    except Exception as exc:
        if meta["active_stage"] == "revalidation":
            validation_meta.update(status="failed", error=str(exc))
        meta.update(status="failed", error=f"{meta['active_stage']}: {exc}")
    finally:
        validation_meta.setdefault(
            "elapsed_seconds", round(time.monotonic() - start, 4)
        )
        save(stage / "status.json", validation_meta)
        meta["stages"] = {"revalidation": validation_meta}
        if (directory / "composition/status.json").exists():
            meta["stages"]["composition"] = json.loads(
                (directory / "composition/status.json").read_text()
            )
        meta["elapsed_seconds"] = round(time.monotonic() - start, 4)
        save(directory / "status.json", meta)
    return meta


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_run_id")
    args = parser.parse_args()
    state = revalidate(args.source_run_id)
    print(
        json.dumps(
            {
                k: state.get(k)
                for k in [
                    "id",
                    "status",
                    "source_run_id",
                    "offline_revalidation",
                    "model_invocations",
                    "main_word_count",
                    "error",
                ]
            },
            indent=2,
        )
    )
    raise SystemExit(0 if state["status"] == "complete" else 1)
