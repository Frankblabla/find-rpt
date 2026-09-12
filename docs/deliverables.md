# Candidate brief: deliverables and scope

The supplied brief allows a web app, CLI, skill or other working form. The primary
interface is a native Claude Code conversation with a project skill, model-free
Python tools and versioned HTML. The earlier web/batch baseline remains usable.

## Four submission items

| Requested item | Included artifact |
| --- | --- |
| Implementation | `find_rpt/`, `.claude/skills/find-rpt/`, `app.py`, `templates/`, `static/` |
| Short README and run instructions | [README](../README.md), `.env.example`, [implementation walkthrough](implementation.md) |
| Actual examples with sources and follow-up | [Submission examples](../submission/README.md#examples-and-their-scope): current Swatch HTML, native conversation and earlier baseline exports |
| AI transcripts or development agent logs | [Selected English development excerpt](../submission/development/transcript.md), original visible events and recovery development events with [provenance](../submission/provenance.json) |

## Requirement coverage

| Requirement | Behavior and qualification |
| --- | --- |
| Locate a report by ticker, date and broker | Date/broker filtering and conservative cover evidence; uncertain identities require explicit file confirmation. Access to all 101 supplied PDFs does not establish automatic matching or accuracy. |
| Title, header and one-line takeaway | Sourced structured brief; printed report date remains separate from filename date. |
| Changed estimates, fiscal periods, reported/calculated changes and consensus | Per-field evidence, explicit missing values, independent arithmetic and separate reported percentage/bps fields. Rounded levels do not erase a printed nonzero revision. |
| Reasons, context and useful comparisons | Cited driver/context paragraphs, material/conflict statements, estimate tables and bounded charts. Extraction can still omit material rows or image-only tables. |
| Original-source links | Local PDF highlights with source coordinates and hash checks. Exact quotations establish traceability, not complete semantic support. |
| Plain English and concise first read | Approximately 220 prose words is editorial guidance. Required facts may exceed it without rejection. Tables and separate answers are outside that count. |
| Clarification email | Automatic draft for revisions without a clear applicable rationale; one no-draft reason otherwise. Explicitly requested drafts remain available, without a contradictory no-draft message. Sourced analyst name/address or TODO recipient, metric/year questions and fixed sender; draft only. No send endpoint or email-service dependency. Draft necessity can still be overestimated. |
| Easy follow-up | Same native conversation and resume; distinct short answers, presentation changes, content amendments and draft edits with preserved versions. Actual six-turn example retains two reviewer corrections. |
| Useful output after interruption | Source-backed partial first read, then full publication; model-free delivery returns the latest verified artifact. No guarantee exists before the first save. |
| Lightweight hallucination check | Bounded same-agent source review. Its scope/findings are recorded; review-file existence does not prove completed review or factual correctness. |

## Evidence and limits

Current offline checks are **138 Python and 11 JavaScript passing tests**.
The [evaluation summary](../submission/evaluation.md) records thirteen full HTML artifacts, ten normal native
completions and three post-publication budget stops. It records source-review
limitations, failed tool calls, costs and preserved historical outcomes.

The last frozen model batch covers 13/29 exact broker labels; native versions
together cover 24/29; all historical baseline/native attempts cover 29/29, including
failures. The final email-display and cleanup changes were checked offline, not by a new model batch. This is attempt coverage, not all-broker accuracy or current-version
regression coverage of all 29. The three remaining reserved May-28 PDFs remain
unopened. The source corpus contains 101 PDFs despite the brief's approximate 170.

The [data-object map](implementation.md#data-objects-containment-references-and-fields)
explains records, fields and containment. The architecture deliberately reuses the
selected agent and ordinary Python functions, with no extra agent framework,
database, MCP layer, independent model reviewer or mail integration.

This repository includes selected actual examples, genuine English development
excerpts and the metadata-only original manifest. Full private evaluations, original
PDFs and Chinese planning stay outside the repository. Example source links require
the supplied PDFs and local viewer; historical case links require the private case
archive. The included examples and evaluation summary remain readable without it.
