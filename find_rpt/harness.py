"""One evidence extraction invocation, then deterministic local composition. No retry loop."""

import hashlib
import json
import os
import platform
import pymupdf
import re
import shutil
import signal
import subprocess
import time
import uuid
from datetime import datetime, timezone

from find_rpt.reports import LOCAL, ROOT, extract, packet, report, normalize_ticker, select_report
from find_rpt.schema import Brief, comparisons
from find_rpt.evidence import (
    ExtractionV3,
    comparison_provenance,
    validate_extraction,
    composition_packet,
    compose,
    select_facts,
    main_word_count,
)

SKILL = ROOT / ".agents/skills/find-rpt/SKILL.md"
RUNS = LOCAL / "runs"
MODELS = ("opus", "sonnet", "haiku")
EFFORTS = ("low", "medium", "high")


def save(path, value):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n")
    temporary.replace(path)


def run_directory(run_id):
    if not re.fullmatch(r"[a-f0-9]{32}", run_id):
        raise ValueError("Invalid run ID.")
    return RUNS / run_id


def selection(model=None, effort=None):
    model = os.environ.get("FIND_RPT_MODEL", "opus") if model is None else model
    effort = os.environ.get("FIND_RPT_EFFORT", "high") if effort is None else effort
    if model not in MODELS or effort not in EFFORTS:
        raise ValueError(
            "Choose opus, sonnet, or haiku and low, medium, or high effort. No fallback is configured."
        )
    return model, effort


def prepare(report_id, ticker, question="", parent_id=None, *, model=None, effort=None, confirm_selection=False):
    model, effort = selection(model, effort)
    ticker = normalize_ticker(ticker)
    row, _ = report(report_id)
    history = []
    if parent_id:
        parent = json.loads((run_directory(parent_id) / "request.json").read_text())
        if parent["report_id"] != report_id or parent["ticker"] != ticker:
            raise ValueError("Follow-up must use the same selected report and ticker.")
        state = json.loads((run_directory(parent_id) / "status.json").read_text())
        if state["status"] != "complete":
            raise ValueError("Follow-up requires a completed parent result.")
        history = parent["prior_questions"] + (
            [parent["question"]] if parent["question"] else []
        )
        if parent.get("selection", {}).get("method") == "user_confirmed":
            confirm_selection = True
    selected = select_report(report_id, ticker, confirm_selection)
    selected["recorded_at"] = datetime.now(timezone.utc).isoformat()
    run_id = uuid.uuid4().hex
    directory = run_directory(run_id)
    directory.mkdir(parents=True)
    request = dict(
        report_id=report_id,
        ticker=ticker,
        broker=row["broker"],
        lookup_date=row["date"],
        question=question,
        prior_questions=history,
        parent_run_id=parent_id,
        model=model,
        effort=effort,
        selection=selected,
    )
    save(directory / "request.json", request)
    (directory / "report.txt").write_text(packet(report_id))
    shutil.copyfile(SKILL, directory / "SKILL.md")
    save(directory / "schema.json", Brief.model_json_schema())
    stage = directory / "extraction"
    stage.mkdir()
    (stage / "SKILL.md").write_text(
        SKILL.read_text()
        + "\n\n"
        + (SKILL.parent / "references" / "extract.md").read_text()
    )
    save(stage / "schema.json", ExtractionV3.model_json_schema())
    (directory / "composition").mkdir()
    save(
        directory / "status.json", dict(id=run_id, status="queued", report_id=report_id)
    )
    return run_id


def claude_command(binary, directory, model, effort):
    model, effort = selection(model, effort)
    return [
        binary,
        "-p",
        "--model",
        model,
        "--effort",
        effort,
        "--output-format",
        "json",
        "--json-schema",
        (directory / "schema.json").read_text(),
        "--system-prompt-file",
        str(directory / "SKILL.md"),
        "--restricted",
        "--safe-mode",
        "--tools",
        "",
        "--strict-mcp-config",
        "--mcp-config",
        '{"mcpServers":{}}',
        "--setting-sources",
        "",
        "--settings",
        '{"disableAllHooks":true}',
        "--no-session-persistence",
        "--no-chrome",
        "--permission-mode",
        "dontAsk",
        "--max-turns",
        "3",
    ]


def claude_environment():
    # Keep subscription/keychain authentication, without inheriting API credentials,
    # provider routing, model aliases, or configuration from the development agent.
    keys = {
        "HOME",
        "PATH",
        "USER",
        "LOGNAME",
        "SHELL",
        "TMPDIR",
        "LANG",
        "LC_ALL",
        "LC_CTYPE",
        "SSL_CERT_FILE",
        "SSL_CERT_DIR",
    }
    return {key: value for key, value in os.environ.items() if key in keys}


def claude_metadata(payload):
    model_usage = payload.get("modelUsage", {})
    return dict(
        effective_models=list(model_usage) if isinstance(model_usage, dict) else [],
        effective_effort=payload.get("effort"),
        model_usage=model_usage,
        usage=payload.get("usage"),
        estimated_cost_usd=payload.get("total_cost_usd"),
        cost_basis="Claude Code client-side estimate; not a subscription invoice or quota cap.",
        harness_session_id=payload.get("session_id"),
        num_turns=payload.get("num_turns"),
    )


def parse_claude_output(payload, contract=Brief):
    if (
        not isinstance(payload, dict)
        or payload.get("is_error")
        or payload.get("subtype") != "success"
    ):
        raise ValueError(
            "Claude Code reported a failed or incomplete result. Raw output retained; no retry or fallback."
        )
    if not isinstance(payload.get("structured_output"), dict):
        raise ValueError(
            "Claude Code did not return structured_output. Raw output retained; no retry or fallback."
        )
    return contract.model_validate(payload["structured_output"])


def invoke_stage(
    directory, binary, model, effort, prompt, contract, validator, timeout
):
    """One process and one validation attempt; preserve failures in the stage itself."""
    start = time.monotonic()
    meta = dict(
        status="running",
        requested_model=model,
        requested_effort=effort,
        started_at=datetime.now(timezone.utc).isoformat(),
        max_turns=3,
        timeout_seconds=timeout,
    )
    command = claude_command(binary, directory, model, effort)
    (directory / "prompt.txt").write_text(prompt)
    meta.update(
        command=command,
        **{
            name + "_sha256": hashlib.sha256(
                (directory / filename).read_bytes()
            ).hexdigest()
            for name, filename in [
                ("prompt", "prompt.txt"),
                ("skill", "SKILL.md"),
                ("schema", "schema.json"),
            ]
        },
    )
    save(directory / "status.json", meta)
    try:
        with (
            (directory / "prompt.txt").open() as stdin,
            (directory / "harness-output.json").open("w") as stdout,
            (directory / "stderr.log").open("w") as errors,
        ):
            process = subprocess.Popen(
                command,
                stdin=stdin,
                stdout=stdout,
                stderr=errors,
                cwd=directory,
                env=claude_environment(),
                start_new_session=True,
            )
            try:
                code = process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
                raise ValueError(
                    "Claude Code timed out. Partial output retained; no retry or fallback."
                )
        meta["returncode"] = code
        try:
            payload = json.loads((directory / "harness-output.json").read_text())
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Claude Code returned invalid JSON (exit {code}); raw output retained."
            ) from exc
        if isinstance(payload, dict):
            meta.update(claude_metadata(payload))
            if isinstance(payload.get("structured_output"), dict):
                save(directory / "response.json", payload["structured_output"])
        if code:
            raise ValueError(
                f"Claude Code exited with code {code}; no retry or fallback."
            )
        response = validator(parse_claude_output(payload, contract))
        save(directory / "validated.json", response.model_dump())
        meta["status"] = "complete"
        return response
    except Exception as exc:
        meta.update(status="failed", error=str(exc))
        raise
    finally:
        meta["elapsed_seconds"] = round(time.monotonic() - start, 2)
        save(directory / "status.json", meta)


def stage_totals(directory):
    stages = {
        name: json.loads((directory / name / "status.json").read_text())
        for name in ["extraction", "composition"]
        if (directory / name / "status.json").exists()
    }
    costs = [s.get("estimated_cost_usd") for s in stages.values()]
    return dict(
        stages=stages,
        estimated_cost_usd=sum(costs)
        if costs and all(c is not None for c in costs)
        else None,
        effective_models=list(
            dict.fromkeys(
                m for s in stages.values() for m in s.get("effective_models", [])
            )
        ),
        usage={name: s.get("usage") for name, s in stages.items()},
        num_turns=sum(s.get("num_turns") or 0 for s in stages.values()),
    )


def compose_stage(directory, evidence, request):
    if evidence.subject_match == "mismatch" or (
        evidence.subject_match == "ambiguous"
        and request.get("selection", {}).get("method") != "user_confirmed"
    ):
        raise ValueError(
            "Report identity is not established for this selection; no brief or draft was composed."
        )
    start = time.monotonic()
    meta = dict(
        status="running",
        implementation="local",
        estimated_cost_usd=0,
        model_invocations=0,
        algorithm="required facts, then optional facts in source order",
        started_at=datetime.now(timezone.utc).isoformat(),
    )
    save(directory / "status.json", meta)
    try:
        save(directory / "input.json", composition_packet(evidence, request))
        choice = select_facts(evidence, request)
        save(directory / "selection.json", choice.model_dump())
        response = compose(evidence, choice, request)
        save(directory / "validated.json", response.model_dump())
        meta.update(status="complete", main_word_count=main_word_count(response))
        return response
    except Exception as exc:
        meta.update(status="failed", error=str(exc))
        raise
    finally:
        meta["elapsed_seconds"] = round(time.monotonic() - start, 4)
        save(directory / "status.json", meta)


def execute(run_id):
    directory = run_directory(run_id)
    if json.loads((directory / "status.json").read_text())["status"] != "queued":
        raise ValueError(
            "This attempt already started; create a new run instead of overwriting evidence."
        )
    request = json.loads((directory / "request.json").read_text())
    model, effort = selection(request.get("model"), request.get("effort"))
    start = time.monotonic()
    meta = dict(
        id=run_id,
        status="running",
        workflow="evidence-local-composition-v3",
        active_stage="extraction",
        harness="Claude Code",
        configured_model=model,
        requested_model=model,
        requested_effort=effort,
        effort=effort,
        effective_effort=None,
        harness_version="unavailable",
        started_at=datetime.now(timezone.utc).isoformat(),
        report_id=request["report_id"],
        python_version=platform.python_version(),
        pymupdf_version=pymupdf.VersionBind,
        cost_basis="Claude Code client-side estimate; not a subscription invoice or quota cap.",
    )
    save(directory / "status.json", meta)
    try:
        row, _ = report(request["report_id"])
        meta.update(
            report_sha256=row["sha256"],
            source_sha256={
                str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in [
                    ROOT / "app.py",
                    *sorted((ROOT / "find_rpt").glob("*.py")),
                    *sorted((ROOT / "static").glob("*")),
                ]
            },
        )
        binary = shutil.which(os.environ.get("FIND_RPT_CLAUDE", "claude"))
        if not binary:
            raise ValueError(
                "Claude Code CLI is missing. Install and sign in; no fallback available."
            )
        meta["harness_version"] = subprocess.check_output(
            [binary, "--version"], text=True, env=claude_environment(), timeout=15
        ).strip()
        timeout = int(os.environ.get("FIND_RPT_TIMEOUT", "300"))
        if not 1 <= timeout <= 600:
            raise ValueError(
                "FIND_RPT_TIMEOUT must be between 1 and 600 seconds per stage."
            )
        lines = {
            line["id"]: line["text"]
            for p in extract(row["id"])["pages"]
            for line in p["lines"]
        }
        save(directory / "status.json", meta)
        evidence = invoke_stage(
            directory / "extraction",
            binary,
            model,
            effort,
            json.dumps(
                {"request": request, "report": (directory / "report.txt").read_text()},
                ensure_ascii=False,
            ),
            ExtractionV3,
            lambda e: validate_extraction(e, lines),
            timeout,
        )
        meta.update(active_stage="composition", **stage_totals(directory))
        save(directory / "status.json", meta)
        response = compose_stage(directory / "composition", evidence, request)
        save(directory / "response.json", response.model_dump())
        meta.update(**stage_totals(directory))
        result = dict(
            brief=response.model_dump(),
            comparisons=[comparisons(e) for e in response.estimates],
            report=row,
            request=request,
            run_id=run_id,
            evidence=evidence.model_dump(),
            comparison_provenance=comparison_provenance(evidence),
            main_word_count=main_word_count(response),
            runtime={
                key: meta[key]
                for key in [
                    "harness",
                    "harness_version",
                    "configured_model",
                    "effort",
                    "requested_model",
                    "requested_effort",
                    "effective_effort",
                    "effective_models",
                    "usage",
                    "estimated_cost_usd",
                    "cost_basis",
                    "workflow",
                ]
            },
        )
        save(directory / "result.json", result)
        meta.update(status="complete", main_word_count=main_word_count(response))
    except Exception as exc:
        meta.update(status="failed", error=f"{meta['active_stage']}: {exc}")
    finally:
        meta.update(**stage_totals(directory))
        meta["elapsed_seconds"] = round(time.monotonic() - start, 2)
        save(directory / "status.json", meta)
    return meta


def read_run(run_id):
    directory = run_directory(run_id)
    state = json.loads((directory / "status.json").read_text())
    if state["status"] == "complete":
        state["result"] = json.loads((directory / "result.json").read_text())
    return state
