"""Shared temporary corpus; no supplied PDF or model is used."""

import hashlib

import pymupdf
import pytest

from find_rpt import harness, reports


@pytest.fixture
def corpus(tmp_path, monkeypatch):
    folder = tmp_path / "corpus"
    folder.mkdir()

    def add(name, text):
        path = folder / name
        with pymupdf.open() as doc:
            p = doc.new_page(width=600, height=800)
            p.insert_text((60, 80), text, fontsize=12)
            doc.save(path)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        return digest[:16]

    monkeypatch.setattr(reports, "CORPUS", folder)
    monkeypatch.setattr(reports, "LOCAL", tmp_path)
    monkeypatch.setattr(harness, "RUNS", tmp_path / "runs")
    return add
