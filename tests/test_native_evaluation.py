"""The paid runner's delivery denominator must reflect actual saved artifacts."""

import json
from types import SimpleNamespace
import subprocess

import pytest

from evals import native
from find_rpt import cases
from tests.support import LINES, extracted_v3


@pytest.mark.parametrize(
    "publish,subtype,link,expected",
    [(True, "success", True, (True, True, True)),
     (True, "error_max_budget_usd", True, (True, False, False)),
     (False, "success", False, (False, False, False)),
     (True, "success", False, (True, True, False))],
)
def test_native_delivery_counts_require_artifact_and_normal_exit(
    corpus, tmp_path, monkeypatch, publish, subtype, link, expected
):
    rid = corpus("20260511_Test_native.pdf", "\n".join(LINES.values()))
    args = SimpleNamespace(output=tmp_path / "evaluation", model="opus", effort="high",
                           budget=15, timeout=1800)
    args.output.mkdir()
    row = dict(ticker="ABC LN", date="2026-05-11", broker="Test", report_id=rid)
    monkeypatch.setattr(native.shutil, "which", lambda _: "/synthetic/claude")

    class Client:
        returncode = 0

        def __init__(self, command, **kwargs):
            assert kwargs["stdin"] == subprocess.DEVNULL
            assert "Edit" in command and "--max-turns" not in command
            session = command[command.index("--session-id") + 1]
            ctx = cases.start("ABC LN", "2026-05-11", "Test", session=session)
            url = ""
            if publish:
                path = cases.case_path(ctx["id"]) / "work" / "extraction.json"
                cases.save(path, extracted_v3().model_dump())
                url = cases.publish(ctx["id"], path, 0)["html_url"]
            kwargs["stdout"].write(json.dumps(dict(type="result", subtype=subtype,
                is_error=subtype != "success", result=url if link else "No handoff link.",
                total_cost_usd=0.1)) + "\n")
            kwargs["stdout"].flush()

        def wait(self, timeout):
            return self.returncode

    monkeypatch.setattr(native.subprocess, "Popen", Client)
    outcome = native.invoke(1, row, args, native.freeze())
    assert (outcome["full_html"], outcome["completed"], outcome["final_link_present"]) == expected
    assert (args.output / "case-01/events.jsonl").exists()
