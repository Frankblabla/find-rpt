# Tests

Run from the repository root:

```bash
uv sync --locked
uv run pytest -q
node --test tests/*.test.mjs
```

The suite has **154 Python cases and 11 JavaScript cases**. It uses temporary
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
| `test_baseline.py` | Direct corpus discovery, file changes, earlier web/batch interface, lookup, source rendering, missing values and model-process configuration |
| `test_full_flow.py` | Synthetic API workflows, draft recipients, follow-up lineage and original-PDF links |
| `test_native_evaluation.py` | Native runner counts saved full artifacts, normal client completion and the final handoff separately; verifies closed stdin and native Edit access |
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

`evals/native.py` is the current native evaluation entry point. The other scripts
retain earlier baseline experiments and require their private frozen inputs.
The current workflow can be evaluated with a private JSON selection:

```json
[{"ticker":"CPG LN","date":"2026-05-11","broker":"Jefferies"}]
```

Save it under `local/`, then explicitly start a paid run:

```bash
uv run python evals/native.py local/selection.json --output local/evaluation --budget 15 --workers 3
```

The output directory must be new and remain inside ignored `local/`. Model/effort
and timeout are selectable; defaults are Opus/high and 30 minutes per report,
without a separate turn cap. With N reports the default aggregate list-cost cap
is N × USD15; a final request can slightly exceed a client cap. This is not a
spending target or a subscription charge estimate. The runner
freezes the inputs and product files, saves every first attempt and raw event log,
and never silently retries a failed session. `summary.json` distinguishes full
HTML, normal completion and a final reply containing the saved latest link.
It does not award a semantic accuracy pass. Optional `report_id` and
`confirm_selection: true` retain an explicitly selected source; report that scope
separately from automatic lookup. Do not include expected report answers in inputs.
