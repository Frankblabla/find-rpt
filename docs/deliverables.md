# Candidate brief: final submission review

Reviewed against both pages of the supplied candidate brief on 12 September 2026.
The package is ready to submit as a working, auditable prototype. The four requested
artifacts are present and the exercised workflows complete. This is not a claim of
exhaustive extraction, hallucination-free output or accuracy across every broker.

## Four submission items

| Candidate brief, section 6 | Included artifact | Check |
| --- | --- | --- |
| 1. Implementation, preferably GitHub; no research PDFs | `find_rpt/`, `.claude/skills/find-rpt/`, `app.py`, `templates/`, `static/` | Ready. The public package contains code and selected evidence; no source PDFs or private runtime. |
| 2. Short README with enable/run/configuration steps | [README](../README.md), `.env.example` | Ready. A clean export installed with `uv sync --locked`, passed both test suites and exposed the CLI help. Corpus placement and manifest restoration are documented. |
| 3. A few actual examples with full format and citations | [Selected examples](../submission/README.md#examples-and-their-scope): Swatch HTML, native conversation, Hexagon and Grenergy | Ready. Artifact hashes and source provenance verified. Source highlights require the supplied PDFs and local viewer. |
| 4. AI transcripts or development agent logs | [English development excerpt](../submission/development/transcript.md), original visible events and recovery events with [provenance](../submission/provenance.json) | Ready. Genuine selected development events are included; product conversations are labelled separately. Chinese planning and private presentation materials are excluded. |

## Contract checked step by step

| Candidate brief item | Implementation and observed check | Remaining qualification |
| --- | --- | --- |
| Three parameters and report lookup | Fresh CPG/Jefferies and HFG/Stifel sessions found the correct PDFs by date, broker and cover ticker. Missing date/report, unverified identity and malformed ticker paths were exercised. | An unverified identifier requires explicit file confirmation; it is never silently treated as verified. |
| 2.1 Title, one-line summary, identifying header | Both new HTML outputs contain ticker, broker, printed date, report title and a cited takeaway. | Filename date and printed date remain distinct. |
| 2.2 What changed, years, percentages, consensus before/after | Revalidated 26 rows and their independent arithmetic across the two outputs. HFG retains all 18 Figure 3 metric-years plus the target; its printed -1bp survives equal rounded 3.5% levels. Missing consensus stays unavailable. | Extraction completeness remains model-dependent. CPG's 2Q26 comparison appears in prose but not the table. |
| 2.3 Why, why now, plain English and management context | Source-checked the key causal passages and event/management attribution. Fixed the template to combine causes into one cited paragraph and context into a second; added a regression test. | Some HFG prose still uses finance shorthand such as SOTP and QoQ. Source validation cannot guarantee readability or causal interpretation. |
| 2.4 Estimate picture from the single report | Tables and expandable comparison charts preserve available old/new and consensus pairs. No external research or cross-report aggregation was used. | Charts show selected comparisons; the table is the detailed view. |
| 2.5 and section 3: analyst email, draft only | CPG has no broker estimate revisions and no draft. HFG automatically drafts seven metric/year questions to sourced analyst Clément Genelot. Saved HTML and final replies agree. Offline tests cover missing contact details with TODO placeholders. | HFG's limitation loosely calls all sales-growth changes upward, although the table correctly retains negative FY27/28 changes. No send endpoint or mail-service dependency exists. |
| 2.6 Inline citations and highlighted original PDF | Claim and row links resolve to exact original lines. Browser inspection confirmed automatic scrolling to blue highlights on the original CPG guidance passage. | A valid location does not prove that every claim is fully supported. |
| 2.7 Useful first-read information | Rating/target changes, source conflicts, missing information and important notes remain visible. Technical metadata and charts are collapsed. | The new briefs have 272/276 main-prose words; the editorial target does not reject necessary content. |
| Page 2: easy further queries and follow-up | Two resumed CPG turns saved a cited guidance answer without changing HTML, then produced a compact view with all seven rows and identical research data. | Q&A and HTML changes are intentionally different operations; the user can ask for either. |
| Section 4: runnable platform | Native Claude Code project skill, selectable model/effort and ordinary Python commands. The maintained web baseline supplies the shared viewer. | Claude must be installed/signed in; source links require a running local viewer. |
| Section 5: corpus and distribution | The manifest covers the 101 PDFs actually supplied, compared with approximately 170 described in the brief. No original PDFs are committed. | Three reserved May-28 PDFs remain unopened; this check used previously examined reports. |

## Verification and deliberate scope

Current offline checks: **139 Python and 11 JavaScript tests pass**, including in
a clean submission export without PDFs, Claude authentication or old runtime files.
Five lookup scenarios plus malformed input, 59 documentation links and 11 submitted
artifact hashes were checked. Current local outputs retain one HTML per case;
retired versions remain only where needed as private audit evidence.

Two fresh Opus/high report sessions and two resumed follow-up turns completed
normally. Source checks covered the final claims, estimate rows, email outcome and
original passages; findings are preserved rather than rewritten into passes.
The client-reported list-cost estimate was **USD7.822414** for all four turns.
See the [evaluation summary](../submission/evaluation.md) for exact outcomes,
launch caveats and the separate historical batches.

The remaining issues are bounded extraction/readability limitations, not missing
submission files or a broken exercised delivery path. No extra agent framework,
database, MCP service, independent model reviewer or email integration was added.
The [data-object map](implementation.md#data-objects-containment-references-and-fields)
explains the existing records and their relationships.
