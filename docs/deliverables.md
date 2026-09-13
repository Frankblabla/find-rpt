# Candidate brief: final submission review

Reviewed against both pages of the supplied candidate brief; delivery evidence updated on 13 September 2026.
The package is ready to submit as a working, auditable prototype. The four requested
artifacts are present and the exercised workflows complete. This is not a claim of
exhaustive extraction, hallucination-free output or accuracy across every broker.

## Four submission items

| Candidate brief, section 6 | Included artifact | Check |
| --- | --- | --- |
| 1. Implementation, preferably GitHub; no research PDFs | `find_rpt/`, `.claude/skills/find-rpt/`, `app.py`, `templates/`, `static/` | Ready. The public package contains code and selected evidence; no source PDFs or private runtime. |
| 2. Short README with enable/run/configuration steps | [README](../README.md), `.env.example` | Ready. A clean export installed with `uv sync --locked`, passed both test suites and exposed the CLI help. Setup only requires placing PDFs in `corpus/`; discovery is automatic. |
| 3. A few actual examples with full format and citations | [Selected examples](../submission/README.md#examples-and-their-scope): Swatch HTML, native conversation, Hexagon and Grenergy | Ready. Artifact hashes and source provenance verified. Source highlights require the supplied PDFs and local viewer. |
| 4. AI transcripts or development agent logs | [English development excerpt](../submission/development/transcript.md), original visible events and recovery events with [provenance](../submission/provenance.json) | Ready. Genuine selected development events are included; product conversations are labelled separately. Chinese planning and private presentation materials are excluded. |

## Contract checked step by step

| Candidate brief item | Implementation and observed check | Remaining qualification |
| --- | --- | --- |
| Three parameters and report lookup | Ticker, date and broker select from PDFs directly in `corpus/`. Earlier CPG/HFG sessions exercised automatic lookup; the current regression completed all 25 selected tasks. Missing and ambiguous inputs have offline tests. | Fifteen regression inputs retain an explicitly confirmed file. This is not a universal automatic-lookup score. |
| 2.1 Title, one-line summary, identifying header | Full outputs contain ticker, broker, printed date, title and a cited takeaway. Each regression takeaway received a limited source check. | Filename date and printed date remain distinct; source identity can remain explicitly ambiguous. |
| 2.2 What changed, years, percentages, consensus before/after | Source-backed rows retain old/new values and available consensus. HFG retains 18 Figure 3 metric-years plus its target; reported bps survive equal rounded levels. CPG now includes the 2Q26 broker/consensus comparison in its table. | Some image-table rows and qualifiers remain missing. Full delivery does not mean exhaustive extraction. |
| 2.3 Why, why now, plain English and management context | The template combines causes into one cited paragraph and context into a second. Causal and management claims refer to original lines. | Some finance shorthand remains; the Soitec EUR14m interpretation is too confident. Source validation cannot prove meaning. |
| 2.4 Estimate picture from the single report | Tables and expandable charts preserve available comparisons. No external research or cross-report aggregation was used. | Charts show selected comparisons; the table is the detailed view. |
| 2.5 and section 3: analyst email, draft only | Fresh CPG has no revisions and no automatic draft; HFG has a saved automatic draft. All 25 HTML pages display mutually exclusive draft/no-draft outcomes. Offline tests cover missing contacts with TODO placeholders. | Draft wording may over-escalate some revisions. No send endpoint or mail-service dependency exists. |
| 2.6 Inline citations and highlighted original PDF | All 50 sampled source URLs across the 25 current briefs returned successfully. Earlier browser inspection confirmed scrolling to original PDF highlights. | A valid location does not prove full semantic support. |
| 2.7 Useful first-read information | Rating/target changes, source conflicts, missing information and notes remain visible. Technical metadata and charts are collapsed. | Length is editorial guidance and does not block delivery of required content. |
| Page 2: easy further queries and follow-up | Earlier resumed CPG turns saved a cited answer without changing HTML, then generated a compact view with the same research data. Offline tests exercise both operations. | The current 25-task batch tests initial delivery; it does not rerun every follow-up scenario. |
| Section 4: runnable platform | Native Claude Code project skill, selectable model/effort and ordinary Python tools. The maintained web baseline supplies the shared viewer. | Claude must be installed/signed in; source links require the local viewer. |
| Section 5: corpus and distribution | Direct discovery finds 101 supplied PDFs, compared with approximately 170 described in the brief. Only a README is committed under `corpus/`. | Three reserved May-28 PDFs remain unparsed; this regression uses previously examined reports. |

## Verification and deliberate scope

**154 Python and 11 JavaScript tests pass**, including in a clean 60-file export
without source PDFs, Claude authentication or private runtime files. All 10 selected
artifact hashes match their copy provenance. Recovery versions remain private
records and are not additional public examples.

The current frozen-version regression reran the same 25 recorded report tasks:
**25 full HTML files, 25 normal completions and 25 latest-link handoffs**, with zero
budget stops. These attempts represent 24 distinct PDFs and 24 broker labels.
The client-reported list-cost estimate is **USD61.4609245**; the highest report
cost is USD5.12 against a requested USD15 cap. All 25 HTML routes, 25 data routes,
50 sampled source links and 25 exclusive email states passed checks.

Limited source reviews preserve unresolved interpretation and coverage findings,
including Soitec's ambiguous amount and Endur's omitted dividend qualifier. Every
session left a same-agent review note; neither that note nor structural validation
establishes accuracy. The [broker table](../submission/evaluation.md) describes
selection, first-attempt outcomes and review scope. Earlier two-report/follow-up
evidence remains historical; it is not added to the current denominator.

The submitted Swatch HTML is from the fresh regression. No extra agent framework,
database, MCP service, independent model reviewer or email integration was added.
The [data-object map](implementation.md#data-objects-containment-references-and-fields)
explains the records and their relationships. The package has all four requested
submission artifacts; remaining issues are disclosed content limitations.
