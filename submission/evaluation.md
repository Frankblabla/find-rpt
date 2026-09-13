# Evaluation summary

## Reproducible offline checks

**142 Python tests and 11 JavaScript tests pass.** The [test guide](../tests/README.md)
explains each file and the commands. Synthetic fixtures verify source/identity
boundaries, arithmetic, drafts, follow-up lineage, artifact preservation and
partial-to-full recovery. They do not prove model accuracy.

Corpus setup was simplified on 13 September: place PDFs in `corpus/` and lookup
discovers them directly. Offline checks cover discovery without a manifest,
additions/removals and changed-source rejection. The 101 existing PDF identities
and 16 saved briefs remain unchanged; no additional model evaluation was run.

The hard 220-word publication limit has been removed from native and baseline
composition. Required facts can exceed the editorial target. Preserved rejected
Ahold and Jahez inputs now publish offline; sourced Danone basis-point changes
survive an explicitly recorded field migration. These are model-free regressions,
not fresh generation successes.

## Submission check: 12 September 2026

The final targeted check used the current skill and simplified HTML, with one
new Opus/high session each for CPG LN / Jefferies and HFG GY / Stifel Nicolaus,
then two resumed CPG follow-ups. Both reports were already development examples;
this was a regression smoke check, not a blind holdout or a new broker-coverage claim.
Actual model: `claude-opus-5`. Requested initial budget: USD6 per report; follow-ups:
USD1.50 and USD1.00. There were no budget stops or automatic batch retries.

| Check | Observed outcome |
| --- | --- |
| CPG initial generation | Normal completion; partial then full; seven rows, 81 quote lines; no email draft. Same-agent review made one content-selection correction. |
| HFG initial generation | Normal completion; partial then full; 19 rows, 146 quote lines; automatic draft and final reply agree. One target-label validation retry recovered. |
| CPG source question | Normal completion; the answer preserved the lower-bound meaning of "above 11%" and did not change HTML. |
| CPG compact view | Normal completion; all seven rows and identical evidence/brief/comparisons retained, with no re-extraction or draft. |
| Structural/source checks | Both saved outputs revalidated; computed comparisons matched; original PDF highlights and exclusive email outcomes checked. |
| Installation and offline tests | Clean submission export: locked install, 139 Python tests, 11 JavaScript tests and CLI help passed at that check. Current counts are listed above. |
| Cost | Client-reported list-cost estimate USD7.822414 across four turns; this is not a subscription charge statement. |

Scoped source review found remaining limitations: CPG's 2Q26 broker/consensus
pair appears in prose but was not extracted as a table row; HFG's limitation
calls all sales-growth changes upward while its FY27/28 table correctly shows
negative changes; HFG retains shorthand such as SOTP and QoQ. These do not prevent
saved delivery, but the runs are not labelled full accuracy passes. The original
outputs and findings were retained; no manual semantic repair was counted as
fresh generation success.

The two initial launches also inherited orchestration-script text on stdin.
Both clients explicitly ignored it; it supplied no expected report answers.
Follow-ups used closed stdin. Three attempted helper commands were permission-
denied, and the clients continued using supported reads. These are disclosed
launch/tool events, not hidden retries. Private raw logs and original case evidence
are in `local/evidence/submission-check/`; they are not uploaded.

The requirement audit also found and fixed a display issue: multiple causes
previously produced more than two reasons/context paragraphs. Causes now share
one paragraph with their separate citations, followed by one context paragraph.
A focused regression protects this without changing source values or the model
workflow. The [deliverable review](../docs/deliverables.md) maps every requested
submission item and contract step to its evidence and limits.

## Earlier thirteen-broker evaluation

A fixed development selection used one initial Opus/high session for each of
thirteen previously unattempted broker labels. Actual model: `claude-opus-5`.
Requested bounds: USD3, 720 seconds and 32 turns per case. No extra model reviewer,
follow-up session or paid post-batch repair was used.

| Outcome | Observed result |
| --- | ---: |
| Latest full HTML artifacts | 13 / 13 |
| Normal native completions | 10 / 13 |
| Budget stops after full HTML was saved | 3 / 13 |
| Cases left without HTML | 0 |
| Saved versions, including initial partials | 27 |
| Latest estimate rows / exact quote lines | 227 / 1,539 |
| Detected structural errors | 0 |
| Client-reported list-cost estimate | USD32.256323 |

Model-free delivery recovered all saved links. The three budget stops were SJF
Bank, Bouvet and HelloFresh. A full artifact means its input contract passed;
it does not imply exhaustive extraction or completed review. Twelve latest
artifacts have same-agent review notes, with uneven completeness; HelloFresh has
none. Limited source spot-checks covered each takeaway, first causal claim when
present and first/middle/last estimate rows. Selected original page images were
also inspected. These are development checks, not blinded human gold labels.

Fresh HelloFresh output retains a -1bp revision despite both rounded levels being
3.5%. Several full briefs exceeded 220 words without a length-only rejection.

## Known limitations and deliberate scope

- SJF Bank's valuation-range midpoint and Bouvet's TP/Target label still failed
  structured target rows. Their numbers remain in prose with omissions disclosed.
- Soitec interprets an ambiguous EUR14m parenthesis too confidently and frames
  forecasts differing from actuals as a conflict. IAG may over-escalate outer-year
  revisions despite a general source explanation.
- Some source highlights omit claim context; image-only tables may be unextracted.
  Exact quote validation checks traceability, not semantic completeness.
- Some review notes misstate available hashes or leave rendered views unchecked.
  HelloFresh's final reply says no draft exists although its saved HTML includes one.
- Swatch's same-agent review corrected `keeps Market Perform` to `rates Market
  Perform`. Its initial partial version overstated identity; later full versions
  retain ambiguity. Earlier versions and findings remain preserved privately.

The product frozen for that earlier batch has real attempts for **13/29 broker labels**. Native
versions together cover 24/29; all historical native/baseline attempts cover
29/29, including failures. This is attempt coverage, not all-broker accuracy or
current-version regression coverage of all 29. Only 4/13 new selected reports
matched automatically in a scoped cover lookup; nine used explicit file selection.

The corpus has 101 PDFs. The three remaining May-28 reserved acceptance PDFs
were excluded and remain unopened. The old ten-report evaluation remains closed:
nine HTML artifacts, seven normal initial completions, two post-publication budget
stops and one publication failure; client-estimated cost USD22.0169405 including
two planned follow-ups. It is not relabelled by subsequent fixes.

All 23 files frozen for the latest model batch and 1,023 protected original/
historical files were unchanged at closeout. The submission cleanup reorganizes
test support and packages selected evidence without changing product behavior.
The original private audit records are preserved under their original paths inside `local/evidence/submission-evidence.zip`.


## Final interface and workspace check

After the recorded model evaluations, the interface gained an explicit email
decision for automatic, unnecessary, user-requested and unfinished cases.
The extraction guidance clarifies absent or unclear applicable reasons without
requiring a full quantitative bridge. No model batch was rerun for this change.

That interface check passed 138 Python and 11 JavaScript cases, including
follow-up after old local versions are retired. Current local HTML was refreshed
without changing research evidence, brief values or comparisons. Original
submitted excerpts remain unchanged; required private source evidence is
consolidated separately. These interface checks do not upgrade historical model
results or establish improved semantic accuracy.


The final readability pass replaces simultaneous automatic-status and draft
blocks with one exclusive email outcome. CPG's default demonstration no longer
contains its test-requested draft or FY26-only filter. Its eight extracted rows
and original evidence remain unchanged. Comparison charts and processing metadata
are collapsed; entirely missing comparison columns are omitted without hiding
zeros. These display changes were checked offline and in the local viewer,
without another model invocation.
