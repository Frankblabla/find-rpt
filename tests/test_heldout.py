"""Synthetic fixtures only: no reserved production PDF or live model is used."""

from pathlib import Path
import pytest

from evals import heldout
from find_rpt import harness, reports
from tests.support import LINES, extracted_v3, fake_process, payload


@pytest.fixture
def evaluation(corpus, tmp_path, monkeypatch):
    identities = []
    for index, broker in enumerate(heldout.BROKERS):
        rid = corpus(
            f"20260511_{broker}_a.pdf",
            "\n".join(LINES.values()) + f"\nSynthetic selected fixture {index}",
        )
        identities.append({"report_id": rid, "ticker": "ABC LN"})
        corpus(f"20260511_{broker}_z.pdf", f"Bloomberg: XYZ LN\nUNSELECTED {index}")
    heldout.save(tmp_path / "split.json", {
        "reports": [dict(row, split="acceptance") for row in reports.inventory()],
    })
    base = tmp_path / "evaluation"
    base.mkdir()
    product = tmp_path / "product.txt"
    product.write_text("Synthetic frozen product identity")
    freeze = base / "product-freeze.json"
    heldout.save(freeze, {
        "product_files_sha256": {"product.txt": heldout.sha(product)},
        "production_split_sha256": heldout.sha(tmp_path / "split.json"),
        "config": {"model": "opus", "effort": "high", "timeout_seconds": 420,
                   "harness_executable": "/synthetic/claude"},
    })
    freeze.with_suffix(".sha256").write_text(heldout.sha(freeze) + "\n")
    for key, value in {
        "ROOT": tmp_path, "FREEZE": freeze, "SPLIT": tmp_path / "split.json",
        "CORPUS": tmp_path / "corpus", "EVALUATION": base / "heldout",
    }.items():
        monkeypatch.setattr(heldout, key, value)
    identity_path = base / "identities.json"
    heldout.save(identity_path, identities)
    return identities, identity_path


@pytest.mark.parametrize("fails", [False, True])
def test_selected_only_api_run_preserves_original_split_and_prevents_repeats(evaluation, monkeypatch, fails):
    identities, source = evaluation
    heldout.prepare(source)
    rid = identities[0]["report_id"]
    row = next(r for r in heldout.selected_rows() if r["sha256"].startswith(rid))
    allowed = heldout.CORPUS / row["file"]
    original_open = reports.pymupdf.open
    opened = []

    def selected_only(path, *args, **kwargs):
        assert Path(path) == allowed, "Parsed an unselected PDF"
        opened.append(path)
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(reports.pymupdf, "open", selected_only)
    e = extracted_v3()
    if fails:
        e.quotes[0].text = "Wrong synthetic quotation"
    calls = fake_process(monkeypatch, [payload(e.model_dump())])
    split = heldout.SPLIT.read_bytes()
    previous_paths = reports.LOCAL, reports.CORPUS, harness.RUNS
    original_inventory = reports.inventory
    result = heldout.invoke(rid)
    assert result["status"] == ("failed" if fails else "complete")
    assert result["model_invocations"] == 1 and len(calls) == 1 and opened
    assert (reports.LOCAL, reports.CORPUS, harness.RUNS) == previous_paths
    assert reports.inventory is original_inventory and len(reports.inventory()) == 8
    assert heldout.SPLIT.read_bytes() == split
    directory = heldout.EVALUATION / "cases" / rid
    view = heldout.load(directory / "split.json")["reports"]
    assert len(view) == 1 and view[0]["original_split"] == "acceptance"
    assert all(r["split"] == "acceptance" for r in heldout.load(heldout.SPLIT)["reports"])
    run = directory / "runs" / result["run_id"]
    frozen_output = (run / "extraction/harness-output.json").read_bytes()
    prompt = (run / "extraction/prompt.txt").read_text()
    assert "Synthetic selected fixture 0" in prompt and "UNSELECTED" not in prompt
    assert not (previous_paths[2] / result["run_id"]).exists()
    with pytest.raises(FileExistsError):
        heldout.invoke(rid)
    assert len(calls) == 1 and (run / "extraction/harness-output.json").read_bytes() == frozen_output


def test_lookup_failure_is_terminal_and_does_not_bypass_subject_gate(evaluation, monkeypatch):
    identities, source = evaluation
    identities[0]["ticker"] = "BAD LN"
    heldout.save(source, identities)
    heldout.prepare(source)
    calls = fake_process(monkeypatch, [])
    result = heldout.invoke(identities[0]["report_id"])
    assert result["status"] == "lookup_failed"
    assert result["model_invocations"] == 0 and calls == []
    directory = heldout.EVALUATION / "cases" / identities[0]["report_id"]
    assert not (directory / "api-response.json").exists()
    with pytest.raises(FileExistsError):
        heldout.invoke(identities[0]["report_id"])
    assert not heldout.EVALUATION.joinpath("evaluation.lock").exists()


def test_unavailable_query_is_not_misreported_as_a_lookup_failure(evaluation, monkeypatch):
    identities, source = evaluation
    identities[0].update(ticker=None, query_unavailable_reason="No source-established query in the synthetic cover.")
    heldout.save(source, identities)
    heldout.prepare(source)
    monkeypatch.setattr(reports.pymupdf, "open", lambda *a, **k: pytest.fail("Parsed a query-unavailable PDF"))
    calls = fake_process(monkeypatch, [])
    result = heldout.invoke(identities[0]["report_id"])
    assert result["status"] == "query_unavailable" and not result["lookup_attempted"]
    assert result["model_invocations"] == 0 and calls == []
    assert result["query_unavailable_reason"] == identities[0]["query_unavailable_reason"]
    directory = heldout.EVALUATION / "cases" / identities[0]["report_id"]
    assert not (directory / "lookup.json").exists() and not (directory / "runs").exists()
    with pytest.raises(FileExistsError):
        heldout.invoke(identities[0]["report_id"])


def test_null_query_requires_a_recorded_reason(evaluation):
    identities, source = evaluation
    identities[0]["ticker"] = None
    heldout.save(source, identities)
    with pytest.raises(ValueError, match="availability reason"):
        heldout.prepare(source)


@pytest.mark.parametrize("change", ["product", "split", "selection"])
def test_freeze_changes_fail_before_pdf_parsing_or_invocation(evaluation, monkeypatch, change):
    identities, source = evaluation
    heldout.prepare(source)
    paths = {
        "product": heldout.ROOT / "product.txt", "split": heldout.SPLIT,
        "selection": heldout.EVALUATION / "selection.json",
    }
    paths[change].write_bytes(paths[change].read_bytes() + b" ")
    monkeypatch.setattr(reports.pymupdf, "open", lambda *args, **kw: pytest.fail("Parsed PDF after freeze changed"))
    calls = fake_process(monkeypatch, [])
    with pytest.raises(ValueError, match="changed"):
        heldout.invoke(identities[0]["report_id"])
    assert calls == []


def test_unselected_case_and_concurrent_attempt_are_rejected(evaluation, monkeypatch):
    identities, source = evaluation
    heldout.prepare(source)
    calls = fake_process(monkeypatch, [])
    with pytest.raises(ValueError, match="outside"):
        heldout.invoke("0" * 16)
    lock = heldout.EVALUATION / "evaluation.lock"
    lock.write_text("Another active evaluation")
    with pytest.raises(FileExistsError):
        heldout.invoke(identities[0]["report_id"])
    assert lock.read_text() == "Another active evaluation" and calls == []
    assert not (heldout.EVALUATION / "cases" / identities[0]["report_id"] / "attempt.json").exists()


@pytest.mark.parametrize("defect", ["substitution", "review_content"])
def test_selection_accepts_only_frozen_identities(evaluation, defect):
    identities, source = evaluation
    if defect == "substitution":
        identities[0]["report_id"] = "0" * 16
    else:
        identities[0]["expected_answer"] = "Never pass private answers to the product"
    heldout.save(source, identities)
    with pytest.raises(ValueError):
        heldout.prepare(source)
    assert not heldout.EVALUATION.exists()
