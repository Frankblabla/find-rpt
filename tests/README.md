# Tests

Run from the repository root:

```bash
uv sync --locked
uv run pytest -q
node --test tests/*.test.mjs
```

The suite has **139 Python cases and 11 JavaScript cases**. It uses temporary
synthetic PDFs and fake model processes. It does not require the private corpus,
Claude authentication, a running server, network access or paid model calls.
Python verifies behavior through direct functions, the CLI boundary and Flask's
local test client. JavaScript uses Node's built-in test runner; no npm install is
needed. PyMuPDF currently emits five upstream deprecation warnings.

## Find the relevant behavior

| File | What it checks |
| --- | --- |
| `test_cases.py` | Native case lifecycle: partial/full publication, Q&A, version preservation, stale updates, recovery, exclusive draft/no-draft outcomes, empty-versus-zero comparison columns, two-paragraph reasons/context, retired-history follow-up, drafts and tampering |
| `test_evidence.py` | Extraction/selection contracts, retained facts, source support, composition and baseline process failures |
| `test_comparison_picture.py` | Fiscal periods, comparison grouping, target labels, reported bps, qualitative revisions and arithmetic boundaries |
| `test_selection.py` | Ticker identity, manual confirmation, provenance, selected-source access and CLI selection |
| `test_baseline.py` | Earlier web/batch interface, lookup, source rendering, missing values and model-process configuration |
| `test_full_flow.py` | Synthetic API workflows, draft recipients, follow-up lineage and original-PDF links |
| `test_heldout.py` | Evaluation-runner safeguards using synthetic files: frozen selection, no repeats and failure recording |
| `app.test.mjs` | Browser state: stale requests, selection confirmation, identity blocking and explicit no-draft reasons |
| `estimates.test.mjs` | Estimate grouping and revision display, including zero, rounded levels and basis points |

`conftest.py` owns the temporary corpus fixture. `support.py` contains the shared
synthetic records and fake model process. Test modules do not import other test
modules. Keep new regression cases beside the behavior they protect; this small
suite does not need additional unit/integration directory layers.

For focused development, run a file or select a behavior:

```bash
uv run pytest tests/test_cases.py -q
uv run pytest -k 'basis_points or overflow or partial' -q
```

## Real model evaluations are separate

Scripts in `evals/` prepare or run explicit evaluations; they are not part of
ordinary test execution. Selected original run evidence is consolidated in ignored `local/evidence/`.
Do not rerun a paid batch as a submission check. The committed-format
[submission summary](../submission/evaluation.md) records observed outcomes,
costs and limitations. Passing synthetic tests proves the specified application
behavior, not financial accuracy or all-corpus coverage.
