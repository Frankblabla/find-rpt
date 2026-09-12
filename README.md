# Find Rpt

A Claude Code skill for finding sell-side reports, creating a source-linked HTML
brief, and continuing the discussion. Ask questions in the same conversation,
change the HTML, or revise a clarification email draft. Email is never sent.

Claude handles reasoning and conversational context. Small Python tools handle
lookup, original-PDF references, validation, arithmetic and versioned artifacts.
Those tools do not call another model. The earlier web application remains a
working baseline and supplies the local PDF highlight viewer.

## Start here

Requires Python 3.11+, `uv`, and Claude Code installed and signed in. Run from
this repository:

```bash
uv sync --locked
claude --model opus --effort high
```

In that Claude conversation:

```text
/find-rpt "CPG LN" 2026-05-11 "Jefferies"
Explain the second change, with original source links.
Make a compact HTML version showing only FY26 estimates.
Add that explanation to the brief.
```

The project skill is discovered from [.claude/skills/find-rpt/SKILL.md](.claude/skills/find-rpt/SKILL.md).
Use ordinary native tool permissions; trust this repository and allow its local
commands when prompted. The skill starts the local viewer and returns an HTML
link. It first saves an explicitly partial brief, then continues to the full
extraction and review. Required content may exceed the approximate 220-word
prose target without a length-only rejection or retry. Do not launch with `--safe-mode` or `--disable-slash-commands`, which disable
skills. Model/effort are selectable through Claude launch options; Opus/high is
our launch recommendation, not a forced setting in the skill.

The brief shows one email outcome: the draft itself, or one sentence explaining
why no draft was created. Unexplained estimate revisions trigger a draft
automatically. A separate draft can be requested later in the conversation.
The default CPG example has no identified revisions and no email draft.

The page prioritizes cited findings and estimate tables. Empty comparison columns
are omitted; zero values remain visible. Charts and processing details are
available on expansion. Default examples show all saved estimate rows.

Q&A saves a short cited answer and leaves the HTML unchanged. Presentation changes
create a new HTML version from the same validated data. Content changes are
validated again. New updates retain recovery versions; explicitly retired local HTML links redirect to the latest result. Claude consumes model usage for
reasoning and tool calls; Python tools themselves consume no model tokens.

Before handoff, the skill now asks the same agent to reread the saved output and
relevant original passages, then leave a short review note with scope and findings.
This is a lightweight self-review procedure, not an independent verifier or a
Python-enforced publication gate. A subsequent ten-report evaluation exercised it
and still found missed qualifiers and a wrong revision classification. Review
notes do not establish factual accuracy; earlier outputs are not retroactively
marked reviewed.

Use `claude --resume` to select the same conversation after exiting. A new
conversation can also attach to a known case: ask it to resume the case ID from
its HTML URL. Native session history remembers the conversation; local case files
retain the report, answers and artifacts if conversational context is lost.

If the model stops after saving an artifact, recover its latest link without any
model usage (replace `CASE_ID` with the ID in its earlier HTML URL):

```bash
uv run python -m find_rpt.tools deliver --case CASE_ID
```

The result says `partial`, `full` or `unavailable`. A partial brief lists unfinished
work; it is useful for Q&A but must be completed before amendments or a draft.
Recovery verifies saved artifacts and reports available review-note paths; it does
not claim a completed review just because HTML exists.

## Source files and artifacts

This workspace already has the private corpus and manifest. For a fresh checkout,
put the supplied PDFs under `raw_file/candidate/corpus/` with their original names,
then restore the bundled metadata-only manifest:

```bash
mkdir -p local
cp -n submission/corpus-manifest.json local/split.json
```

The copy preserves an existing local manifest. PDFs and runtime data remain
excluded from Git. The bundled split retains historical labels and isolation
wording; current ordinary application access includes all 101 entries. Only for
a genuinely different corpus, create a new manifest before inspecting reports
with `uv run python evals/reserve.py`; never replace this corpus's established split.

All 101 manifest reports are accessible. Date/broker filtering and conservative
cover matching locate candidates. Unverified ticker identities require original
PDF review and explicit file confirmation. This is not full-corpus accuracy proof.

The cleaned workspace retains one current HTML per case. Required original audit evidence is kept separately under `local/evidence/`. Artifacts live in `local/cases/CASE_ID/`: `case.json` and `request.json` record
identity; `answers/` stores Q&A; `versions/0001/` contains `brief.html`, evidence,
result JSON and hashes. Each changed artifact gets a new version. Standalone HTML
can be read without the viewer, but source links require the local corpus and
viewer on port 8765. Start it manually with
`uv run python -m find_rpt.tools serve` if needed. `FIND_RPT_PORT` changes its port;
use the same setting when creating HTML and starting the viewer.

## Repository map

```text
find_rpt/       Core functions, data validation and case tools
.claude/        Primary native Claude Code skill
app.py          Earlier web baseline and shared local source viewer
static/         Browser behavior and styles
templates/      Brief, source viewer and baseline pages
tests/          Offline behavior tests and small shared synthetic helpers
evals/          Explicit evaluation scripts; separate from routine tests
docs/           Current implementation walkthrough and deliverable checklist
submission/     Selected examples, English development logs and evaluation summary
local/          Private runtime/evaluation artifacts, ignored by Git
raw_file/       Original private PDFs, ignored by Git
```

`.agents/` retains the earlier baseline extraction skill used by the web/batch
path. It is not a second agent inside the native workflow.

## Read the code and check the delivery

| Need | Read |
| --- | --- |
| Understand the current implementation | [Code walkthrough](docs/implementation.md): execution path, data-object map and six code-reading stops |
| Review the submission | [Submission contents](submission/README.md), then the [deliverable checklist](docs/deliverables.md) if needed |
| Understand or run the tests | [Test guide](tests/README.md): behavior map, shared fixtures and offline commands |
| Review outcomes and limitations | [Evaluation summary](submission/evaluation.md) |

```bash
uv run pytest -q
node --test tests/*.test.mjs
```

Current checks: **138 Python tests and 11 JavaScript tests pass**. These include explicit email decisions and follow-up after historical-output cleanup. The six-turn
[real native exercise](submission/examples/native-conversation.md)
produced four HTML versions and five answers, with two explicit review corrections.
The earlier [ten-report evaluation](submission/evaluation.md) saved
nine briefs, including two budget interruptions; one report had no HTML.
[Preserved-input regressions](submission/evaluation.md) address its
observed target-label and bps defects and remove the hard prose limit. The old
batch is not relabelled as a pass.

The latest [thirteen-broker evaluation](submission/evaluation.md)
saved **13 full HTML briefs**: ten native sessions ended normally and three hit
their cost caps after publication. Model-free delivery recovered all saved links.
It checked 227 latest estimate rows and 1,539 exact quote lines without structural
errors; source spot-checks still found interpretation, citation and handoff
limitations. Client-reported list-cost estimate: **USD32.256323**.

The corpus has 29 broker labels. This product version has attempts for 13;
all historical versions together have attempts for 29, including failures.
See the [coverage breakdown](docs/deliverables.md#broker-coverage). These counts
are neither all-broker accuracy nor current-version regression coverage of all 29.

Synthetic checks do not establish research accuracy. Exact citations prove source
locations and quotations, not that every claim is correctly interpreted. The skill
can make one focused correction after a validation error; a remaining failure
keeps the last valid artifact. Rejected tool inputs are retained.

The [evaluation summary](submission/evaluation.md) and selected examples are
included. The necessary private evidence is consolidated under `local/evidence/` and is not published.

## Earlier baseline

`uv run python app.py` serves the form-based app at <http://127.0.0.1:8765>.
`uv run python -m find_rpt 'CPG LN' 2026-05-11 'Jefferies'` performs model-free
lookup; `--analyze` invokes its one-shot pipeline. That pipeline also supports
follow-up runs, but rebuilds the brief. The native skill does not use it.
Baseline environment settings are documented in [.env.example](.env.example).

This repository contains the selected submission snapshot. Original PDFs, full
private logs and local development history are excluded. Email remains draft-only.
