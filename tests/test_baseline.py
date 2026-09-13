"""Synthetic fixtures exercise lookup, evidence, arithmetic, and failure handling.

These are not report-agent runs and do not establish research-answer accuracy.
"""

import json

import pytest

import app as web
from find_rpt import harness, reports
from find_rpt.schema import difference, validate_evidence
from tests.support import valid_brief


def test_labelled_subject_alias_no_match_and_ambiguity(corpus):
    first = corpus(
        "20260622_Test Broker_a.pdf",
        "Subject: Example\nBloomberg: SHA0 GR\nPeer: SAP GY",
    )
    corpus("20260622_Test Broker_b.pdf", "Subject: Other\nSAP GY appears incidentally")
    assert (
        reports.lookup("sha0 gy", "2026-06-22", "test broker")["candidates"][0]["id"]
        == first
    )
    assert reports.lookup("SAP GY", "2026-06-22", "Test Broker")["status"] == "no_match"
    assert (
        reports.lookup("SHA0 GY", "2026-06-21", "Test Broker")["status"] == "no_match"
    )
    corpus(
        "20260622_Test Broker_c.pdf",
        "Subject: Another plausible report\nBloomberg: SHA0 GR",
    )
    assert (
        reports.lookup("SHA0 GY", "2026-06-22", "Test Broker")["status"] == "ambiguous"
    )


def test_pdf_placement_enables_lookup_and_source_access_without_setup(corpus):
    held = corpus("20260511_Test_a.pdf", "Bloomberg: BP/ LN")
    assert not (reports.LOCAL / "split.json").exists()
    match = reports.lookup("BP/ LN", "2026-05-11", "Test")["candidates"][0]
    assert match["id"] == held
    client = web.app.test_client()
    catalog = client.get("/api/catalog").json
    assert catalog["total"] == 1 and catalog["brokers"] == ["Test"]
    assert client.get(f"/pdf/{held}").data.startswith(b"%PDF")
    assert client.get(f"/source/{held}?refs=p1l1").status_code == 200
    assert not (reports.LOCAL / "split.json").exists()


def test_discovery_ignores_legacy_evaluation_metadata(corpus):
    rid = corpus("20260511_Test_a.pdf", "Bloomberg: ABC LN")
    old_split = reports.LOCAL / "split.json"
    old_split.write_text("Unrelated historical evaluation data")
    assert reports.lookup("ABC LN", "2026-05-11", "Test")["candidates"][0]["id"] == rid
    assert old_split.read_text() == "Unrelated historical evaluation data"


def test_file_addition_rename_and_removal_need_no_reindex(corpus):
    rid = corpus("20260511_Test_a.pdf", "Bloomberg: ABC LN")
    other = corpus("20260512_Other_b.pdf", "Bloomberg: XYZ LN")
    assert {r["id"] for r in reports.inventory()} == {rid, other}
    _, path = reports.report(rid)
    renamed = path.with_name("20260513_Renamed_a.pdf")
    path.rename(renamed)
    assert reports.lookup("ABC LN", "2026-05-13", "Renamed")["candidates"][0]["id"] == rid
    assert reports.lookup("ABC LN", "2026-05-11", "Test")["status"] == "no_match"
    renamed.unlink()
    assert [r["id"] for r in reports.inventory()] == [other]
    with pytest.raises(ValueError, match="unavailable"):
        reports.extract(rid)


def test_empty_corpus_and_unrecognized_files_are_safe(corpus):
    for name in ["README.md", "notes.pdf", "20260230_Test_a.pdf", "20260511__a.pdf"]:
        (reports.CORPUS / name).write_text("Not a report")
    assert web.app.test_client().get("/api/catalog").json["total"] == 0
    for path in reports.CORPUS.iterdir():
        path.unlink()
    reports.CORPUS.rmdir()
    assert reports.lookup("ABC LN", "2026-05-11", "Test")["status"] == "no_match"


def test_slash_ticker_and_exact_boundaries(corpus):
    corpus("20260511_Test_a.pdf", "Bloomberg: BP/ LN")
    assert reports.lookup("BP/ LN", "2026-05-11", "Test")["status"] == "match"
    assert reports.lookup("BP LN", "2026-05-11", "Test")["status"] == "no_match"
    with pytest.raises(ValueError):
        reports.lookup("../../etc", "2026-05-11", "Test")


def test_original_coordinates_and_bad_reference_rejection(corpus):
    rid = corpus(
        "20260511_Test_a.pdf", "Bloomberg: ABC LN\nEPS revised from 1.00 to 1.20"
    )
    line = reports.source_lines(rid, ["p1l2"])[0]
    assert line["text"] == "EPS revised from 1.00 to 1.20"
    x0, y0, x1, y1 = line["bbox"]
    assert 0 <= x0 < x1 <= 600 and 0 <= y0 < y1 <= 800
    client = web.app.test_client()
    html = client.get(f"/source/{rid}?refs=p1l2").get_data(as_text=True)
    assert 'class="highlight"' in html and "EPS revised" in html
    assert client.get(f"/page/{rid}/1.png").data.startswith(b"\x89PNG")
    assert client.get(f"/source/{rid}?refs=p9l99").status_code == 400
    assert client.get(f"/page/{rid}/99.png").status_code == 404


def test_changed_original_fails_closed(corpus):
    rid = corpus("20260511_Test_a.pdf", "Bloomberg: ABC LN")
    reports.extract(rid)
    _, path = reports.report(rid)
    path.write_bytes(path.read_bytes() + b"changed")
    with pytest.raises(ValueError, match="changed"):
        reports.extract(rid)
    replacement = reports.inventory()[0]["id"]
    assert replacement != rid and reports.extract(replacement)["pages"]


def test_missing_zero_negative_and_consensus_arithmetic():
    assert difference(2, None) == dict(absolute=None, percent=None)
    assert difference(2, 0) == dict(absolute=2, percent=None)
    assert difference(-1, -2) == dict(absolute=1, percent=50)
    assert difference(0.55, 0.38)["percent"] == pytest.approx(44.7368421053)


def test_rejects_fabricated_citation_and_missing_escalation():
    brief = valid_brief()
    brief.takeaway.sources = ["p900l1"]
    with pytest.raises(ValueError, match="citation"):
        validate_evidence(brief, {"p1l1"})
    brief = valid_brief()
    brief.rationale = "unclear"
    with pytest.raises(ValueError, match="email draft"):
        validate_evidence(brief, {"p1l1"})


def test_missing_harness_preserves_failed_attempt(corpus, monkeypatch):
    rid = corpus("20260511_Test_a.pdf", "Bloomberg: ABC LN")
    monkeypatch.setenv("FIND_RPT_CLAUDE", "nonexistent-find-rpt-harness")
    run_id = harness.prepare(rid, "ABC LN")
    state = harness.execute(run_id)
    assert state["status"] == "failed" and "missing" in state["error"]
    assert (harness.run_directory(run_id) / "SKILL.md").exists()
    assert not (harness.run_directory(run_id) / "result.json").exists()


def test_followup_cannot_switch_sources(corpus):
    a = corpus("20260511_Test_a.pdf", "Bloomberg: ABC LN")
    b = corpus("20260511_Test_b.pdf", "Bloomberg: XYZ LN")
    parent = harness.prepare(a, "ABC LN")
    with pytest.raises(ValueError, match="same selected report"):
        harness.prepare(b, "XYZ LN", "Question", parent)


def test_local_json_boundary_and_no_email_send_endpoint(corpus):
    corpus("20260511_Test_a.pdf", "Bloomberg: ABC LN")
    client = web.app.test_client()
    assert (
        client.post(
            "/api/lookup", json={}, headers={"Origin": "https://other.example"}
        ).status_code
        == 403
    )
    assert client.get("/", headers={"Host": "other.example"}).status_code == 403
    assert client.post("/api/lookup", data="ticker=ABC").status_code == 415
    assert not any(
        "send" in rule.rule or "email" in rule.rule
        for rule in web.app.url_map.iter_rules()
    )


def test_claude_command_pins_model_and_disables_external_tools(tmp_path):
    (tmp_path / "schema.json").write_text('{"type":"object"}')
    args = harness.claude_command("/verified/claude", tmp_path, "sonnet", "low")
    for flag, value in {
        "--model": "sonnet",
        "--effort": "low",
        "--tools": "",
        "--max-turns": "3",
        "--output-format": "json",
        "--setting-sources": "",
        "--settings": '{"disableAllHooks":true}',
    }.items():
        assert args[args.index(flag) + 1] == value
    assert {
        "--safe-mode",
        "--restricted",
        "--strict-mcp-config",
        "--no-session-persistence",
    } <= set(args)
    assert "--fallback-model" not in args and "--bare" not in args
    assert args[args.index("--system-prompt-file") + 1] == str(tmp_path / "SKILL.md")
    assert (
        harness.claude_command("/verified/claude", tmp_path, "haiku", "low")[3]
        == "haiku"
    )
    with pytest.raises(ValueError, match="Choose opus"):
        harness.claude_command("/verified/claude", tmp_path, "gpt-default", "low")


def test_child_environment_excludes_development_credentials_and_routing(monkeypatch):
    for name in [
        "ANTHROPIC_API_KEY",
        "ANTHROPIC_BASE_URL",
        "CLAUDE_CODE_EFFORT_LEVEL",
        "CLAUDE_CONFIG_DIR",
        "OPENAI_API_KEY",
    ]:
        monkeypatch.setenv(name, "SYNTHETIC_TEST_VALUE")
    env = harness.claude_environment()
    assert not any(
        name.startswith(("ANTHROPIC_", "CLAUDE_", "OPENAI_")) for name in env
    )
    assert "HOME" in env and "PATH" in env


def test_claude_structured_result_and_estimated_cost_metadata():
    payload = dict(
        subtype="success",
        is_error=False,
        structured_output=valid_brief().model_dump(),
        modelUsage={"claude-sonnet-test": {"inputTokens": 100}},
        usage={"input_tokens": 100},
        total_cost_usd=0.01,
        num_turns=1,
        session_id="synthetic",
    )
    assert harness.parse_claude_output(payload).title == "Synthetic fixture"
    meta = harness.claude_metadata(payload)
    assert meta["effective_models"] == ["claude-sonnet-test"]
    assert (
        meta["estimated_cost_usd"] == 0.01
        and "not a subscription invoice" in meta["cost_basis"]
    )
    assert harness.claude_metadata({})["estimated_cost_usd"] is None


@pytest.mark.parametrize(
    "payload",
    [
        {"subtype": "error_max_turns", "is_error": True},
        {
            "subtype": "success",
            "result": '{"title":"Do not accept an unvalidated text fallback"}',
        },
        {"subtype": "success", "structured_output": {"missing": "required fields"}},
        [],
    ],
)
def test_claude_errors_never_accept_unstructured_fallback(payload):
    with pytest.raises(ValueError):
        harness.parse_claude_output(payload)


def test_failed_claude_process_is_called_once_and_raw_evidence_survives(
    corpus, monkeypatch
):
    rid = corpus("20260511_Test_a.pdf", "Bloomberg: ABC LN")
    monkeypatch.setattr(harness.shutil, "which", lambda name: "/synthetic/claude")
    monkeypatch.setattr(
        harness.subprocess, "check_output", lambda *a, **k: "Synthetic CLI"
    )
    calls = []

    class FailedProcess:
        def __init__(self, command, **kwargs):
            calls.append(command)
            kwargs["stdout"].write(
                '{"subtype":"error_max_turns","is_error":true,"total_cost_usd":0.02}'
            )

        def wait(self, **kwargs):
            return 1

    monkeypatch.setattr(harness.subprocess, "Popen", FailedProcess)
    run_id = harness.prepare(rid, "ABC LN")
    state = harness.execute(run_id)
    assert state["status"] == "failed" and state["estimated_cost_usd"] == 0.02
    assert len(calls) == 1 and calls[0][0] == "/synthetic/claude"
    directory = harness.run_directory(run_id)
    assert (directory / "extraction" / "harness-output.json").exists() and (
        directory / "extraction" / "prompt.txt"
    ).exists()
    assert not (directory / "result.json").exists()
    before = (directory / "status.json").read_bytes()
    with pytest.raises(ValueError, match="overwriting evidence"):
        harness.execute(run_id)
    assert (directory / "status.json").read_bytes() == before and len(calls) == 1


def test_claude_timeout_terminates_once_without_retry(corpus, monkeypatch):
    rid = corpus("20260511_Test_a.pdf", "Bloomberg: ABC LN")
    monkeypatch.setattr(harness.shutil, "which", lambda name: "/synthetic/claude")
    monkeypatch.setattr(
        harness.subprocess, "check_output", lambda *a, **k: "Synthetic CLI"
    )
    kills = []
    monkeypatch.setattr(harness.os, "killpg", lambda pid, sig: kills.append((pid, sig)))

    class StalledProcess:
        pid = 123456789

        def __init__(self, *args, **kwargs):
            self.waits = 0

        def wait(self, timeout=None):
            self.waits += 1
            if self.waits == 1:
                raise harness.subprocess.TimeoutExpired("synthetic", timeout)
            return -15

    monkeypatch.setattr(harness.subprocess, "Popen", StalledProcess)
    state = harness.execute(harness.prepare(rid, "ABC LN"))
    assert state["status"] == "failed" and "timed out" in state["error"]
    assert kills == [(123456789, harness.signal.SIGTERM)]


def test_opus_high_defaults_and_request_selection_are_frozen(corpus, monkeypatch):
    monkeypatch.delenv("FIND_RPT_MODEL", raising=False)
    monkeypatch.delenv("FIND_RPT_EFFORT", raising=False)
    assert harness.selection() == ("opus", "high")
    rid = corpus("20260511_Test_a.pdf", "Bloomberg: ABC LN")
    run_id = harness.prepare(rid, "ABC LN", model="sonnet", effort="medium")
    monkeypatch.setenv("FIND_RPT_MODEL", "haiku")
    request_data = json.loads(
        (harness.run_directory(run_id) / "request.json").read_text()
    )
    assert (request_data["model"], request_data["effort"]) == ("sonnet", "medium")
    args = harness.claude_command(
        "/synthetic/claude",
        harness.run_directory(run_id),
        request_data["model"],
        request_data["effort"],
    )
    assert args[args.index("--model") + 1] == "sonnet"
    assert args[args.index("--effort") + 1] == "medium"


def test_api_selectors_validate_before_any_harness_dispatch(corpus, monkeypatch):
    rid = corpus("20260511_Test_a.pdf", "Bloomberg: ABC LN")
    dispatched = []
    monkeypatch.setattr(web.worker, "submit", lambda *args: dispatched.append(args))
    client = web.app.test_client()
    defaults = client.get("/api/catalog").get_json()
    assert defaults["models"] == ["opus", "sonnet", "haiku"]
    assert defaults["efforts"] == ["low", "medium", "high"]
    for model, effort in [("gpt-default", "high"), ("opus", "ultra"), ("", "low")]:
        assert (
            client.post(
                "/api/runs",
                json=dict(report_id=rid, ticker="ABC LN", model=model, effort=effort),
            ).status_code
            == 400
        )
    assert not dispatched
    response = client.post(
        "/api/runs",
        json=dict(report_id=rid, ticker="ABC LN", model="opus", effort="high"),
    )
    assert response.status_code == 202 and len(dispatched) == 1
    saved = json.loads(
        (harness.run_directory(response.get_json()["id"]) / "request.json").read_text()
    )
    assert (saved["model"], saved["effort"]) == ("opus", "high")


def test_unreported_effective_effort_stays_unavailable():
    assert harness.claude_metadata({})["effective_effort"] is None
    assert harness.claude_metadata({"effort": "high"})["effective_effort"] == "high"


def test_standalone_label_with_value_beside_it_uses_bounded_geometry():
    label = dict(id="p1l1", text="Bloomberg / Reuters", bbox=[400, 500, 460, 510])
    ticker = dict(id="p1l2", text="ABC LN / ABC.L", bbox=[510, 500, 580, 510])
    assert reports.subject_evidence([label, ticker], "ABC LN") == [label, ticker]
    assert (
        reports.subject_evidence(
            [label, dict(ticker, bbox=[510, 530, 580, 540])], "ABC LN"
        )
        == []
    )
    assert (
        reports.subject_evidence(
            [label, dict(ticker, bbox=[700, 500, 780, 510])], "ABC LN"
        )
        == []
    )
