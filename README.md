# Find Rpt

A Claude Code skill for finding sell-side reports, creating a source-linked HTML
brief, and continuing the discussion. Ask questions in the same conversation,
change the HTML, or revise a clarification email draft. Email is never sent.

Claude handles reasoning and conversational context. Small Python tools handle
lookup, original-PDF references, validation, arithmetic and versioned artifacts.
Those tools do not call another model. The earlier web application remains a
working baseline and supplies the local PDF highlight viewer.

## Start here

Requires Python 3.11+, `uv`, and Claude Code installed and signed in. Place the
supplied PDFs in [`corpus/`](corpus/README.md), keeping their original filenames.
Then run from this repository:

```bash
uv sync --locked
claude --model opus --effort high
```

At the Claude Code prompt in your terminal, submit this request and wait for the
agent's response:

```text
/find-rpt "CPG LN" 2026-05-11 "Jefferies"
```

## Read the brief and follow up

1. **Open the link returned by Claude.** Its response includes a local HTML URL
   such as `http://127.0.0.1:8765/case/CASE_ID/VERSION`. Click that link in your
   terminal, or copy the complete URL into a browser. An early link may be marked
   **partial**; the agent continues and returns the full brief when ready.
2. **Read the generated HTML in the browser.** It contains the findings, estimate
   table, uncertainties and one email outcome: a draft, or a reason no draft was
   created. The CPG example normally has no identified revisions and no draft.
3. **Click a citation beside a claim or value.** The local viewer opens the
   original PDF with the referenced lines highlighted. Use it to check the source,
   then return to the brief.
4. **Return to the same Claude Code conversation in your terminal.** Submit one
   follow-up at a time. The browser displays artifacts; Claude Code handles the
   continuing conversation.

For example:

```text
Explain the FY26 guidance, with original source links.
```

That saves a cited answer and leaves the HTML unchanged. To change the page, ask:

```text
Make a compact HTML version showing only FY26 estimates.
```

To add new explanation to its content, ask:

```text
Add that explanation to the brief.
```

For each HTML update, open the new link returned by Claude. If the local link
does not open, start the viewer in another terminal from this repository, then
retry the link:

```bash
uv run python -m find_rpt.tools serve
```

## Workflow and configuration

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
reasoning and tool calls; Python tools themselves consume no model tokens. Inputs cite source line IDs;
Python copies the corresponding original quotations into saved evidence. Native
Edit supports small corrections, and prose length or item counts do not block
publication. Source identity, supplied quote text and saved hashes remain checked.

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

Reports are discovered directly from `corpus/` using `YYYYMMDD_Broker_hash.pdf`
filenames. Adding or removing a PDF takes effect on the next lookup; there is no
manifest, import command or index to maintain. Files without this naming pattern
or a valid date are ignored. Only `corpus/README.md` is tracked in Git; PDFs and
runtime data stay private.

Date/broker filtering and conservative cover matching locate candidates.
Unverified ticker identities require original PDF review and explicit file
confirmation. File contents determine report IDs, so saved evidence cannot
silently switch to an edited PDF. Discovery is not full-corpus accuracy proof.

The cleaned workspace retains one current HTML per case. Required original audit evidence is kept separately under `local/evidence/`. Artifacts live in `local/cases/CASE_ID/`: `case.json` and `request.json` record
identity; `answers/` stores Q&A; `versions/0001/` contains `brief.html`, evidence,
result JSON and hashes. Each changed artifact gets a new version. Standalone HTML
can be read without the viewer, but source links require the local corpus and
viewer on port 8765. Start it manually with
`uv run python -m find_rpt.tools serve` if needed. `FIND_RPT_PORT` changes its port;
use the same setting when creating HTML and starting the viewer.

## Repository map

```text
corpus/        Local source PDFs; only the placement instructions are committed
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
| Review outcomes and limitations | [Results by broker](submission/evaluation.md) |

```bash
uv run pytest -q
node --test tests/*.test.mjs
```

Current checks: **154 Python tests and 11 JavaScript tests pass**. These synthetic
checks verify application behavior; source correctness still requires review.

The [broker results table](submission/evaluation.md) now reports a same-version
rerun of the 25 recorded tasks: **25 full HTML deliveries, 25 normal completions,
and 25 final replies with the latest saved link**, compared with 24 full deliveries
and 19 completed workflows in the earlier records. These are reused development
reports, not an unseen accuracy benchmark. Scoped source checks still find
interpretation and coverage issues, which remain visible in the table.

The current [native evaluation runner](evals/native.py) defaults to Opus/high,
USD15 per report and 30 minutes, without a separate turn cap. This is an evaluation
budget, not a forced limit on interactive conversations. See the
[test guide](tests/README.md#real-model-evaluations-are-separate) for explicit paid-run
instructions. No automatic batch retries are used. The
[real native conversation](submission/examples/native-conversation.md) separately
illustrates source Q&A, HTML changes and resume with reviewer corrections.

Exact citations establish source locations and quotations; they cannot guarantee
interpretation or completeness. Original run evidence stays private under
`local/evidence/`. A future unseen evaluation remains limited to 30 distinct
companies; the current regression reuses the existing reports.

## Earlier baseline

`uv run python app.py` serves the form-based app at <http://127.0.0.1:8765>.
`uv run python -m find_rpt 'CPG LN' 2026-05-11 'Jefferies'` performs model-free
lookup; `--analyze` invokes its one-shot pipeline. That pipeline also supports
follow-up runs, but rebuilds the brief. The native skill does not use it.
Baseline environment settings are documented in [.env.example](.env.example).

This repository contains the selected submission snapshot. Original PDFs, full
private logs and local development history are excluded. Email remains draft-only.
