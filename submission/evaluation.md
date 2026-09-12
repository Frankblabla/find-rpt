# Evaluation summary

## Reproducible offline checks

**132 Python tests and 10 JavaScript tests pass.** The [test guide](../tests/README.md)
explains each file and the commands. Synthetic fixtures verify source/identity
boundaries, arithmetic, drafts, follow-up lineage, artifact preservation and
partial-to-full recovery. They do not prove model accuracy.

The hard 220-word publication limit has been removed from native and baseline
composition. Required facts can exceed the editorial target. Preserved rejected
Ahold and Jahez inputs now publish offline; sourced Danone basis-point changes
survive an explicitly recorded field migration. These are model-free regressions,
not fresh generation successes.

## Latest real evaluation

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

The current frozen product has real attempts for **13/29 broker labels**. Native
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
Full private audit records remain under `local/iteration-07-gap-13/`.
