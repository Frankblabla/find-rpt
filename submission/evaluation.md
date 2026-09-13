# Evaluation by broker

**25 recorded report attempts · 24 full HTML deliveries · 19 full deliveries with normal session completion.**

This table summarizes the two archived native-agent batches and the final two-report regression. They used different product versions; this is development evidence, not a uniform current-version benchmark or an accuracy score. Synthetic checks are excluded.

**Full HTML** means a saved complete brief. **Completed** additionally requires normal agent-session completion. A budget stop can still leave usable HTML. Source review was limited to selected claims and rows; “supported” applies only to that checked scope.

| Broker label | PDFs available | Reports attempted | Full HTML | Completed | Recorded batch | Source-review finding |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| ABG Sundal Collier | 1 | 1 | 1/1 | 1/1 | 13-report | Quarterly image table omitted; sampled claims supported. |
| Alantra Equities Sociedad de Valores, S.A. | 5 | 1 | 1/1 | 1/1 | 10-report | Sampled claims supported; preview kept distinct from revisions. |
| BNP Paribas | 2 | 1 | 1/1 | 1/1 | 10-report | Image-table broker/consensus comparisons omitted. |
| Berenberg | 4 | — | — | — | — | Not covered by the native batches summarized here. |
| Bestinver Securities | 2 | 1 | 1/1 | 1/1 | 13-report | Sampled claims supported; optional facts crowd out operating context. |
| BofA Global Research | 4 | — | — | — | — | Not covered by the native batches summarized here. |
| CIC Corporate & Institutional Banking | 3 | — | — | — | — | Not covered by the native batches summarized here. |
| Citi | 4 | 1 | 1/1 | 1/1 | 13-report | Sampled claims supported; listing identity remains ambiguous. |
| DNB Carnegie | 2 | 1 | 1/1 | 1/1 | 13-report | Sampled claims supported; source tension preserved. |
| Danske Bank Commissioned Research | 1 | 1 | 1/1 | 0/1 | 13-report | Recovered after budget stop; structured valuation row omitted. |
| Danske Bank Research | 2 | 1 | 1/1 | 0/1 | 10-report | Budget stop; target qualifier missing. |
| Degroof Petercam | 2 | 1 | 1/1 | 1/1 | 13-report | Sampled values supported; some tables unextracted. |
| Deutsche Bank Research | 4 | 1 | 1/1 | 1/1 | 10-report | Sampled claims supported; price-unit ambiguity disclosed. |
| Goldman Sachs | 4 | — | — | — | — | Not covered by the native batches summarized here. |
| ING Wholesale Banking | 2 | 1 | 0/1 | 0/1 | 10-report | Target-label validation blocked publication; later offline recovery is excluded. |
| Intermonte Securities | 1 | 1 | 1/1 | 0/1 | 10-report | Full HTML saved before budget stop; no completed self-review. |
| JP Morgan | 4 | 1 | 1/1 | 1/1 | 10-report | Sampled claims supported; target-label repair needed. |
| Jefferies | 4 | 1 | 1/1 | 1/1 | Final regression | Final run completes; one quarterly comparison remains in prose only. |
| KBC Securities | 3 | 1 | 1/1 | 1/1 | 13-report | Takeaway highlight omits part of its claim context. |
| Kepler Cheuvreux | 4 | 1 | 1/1 | 1/1 | 10-report | Quarterly comparisons incomplete; source numerical tension missed. |
| Morgan Stanley | 3 | 1 | 1/1 | 1/1 | 13-report | Sampled values supported; takeaway needs benchmark qualification. |
| Nordea Equity Research | 2 | 1 | 1/1 | 1/1 | 10-report | Sampled claims supported; no prior estimates invented. |
| Oddo BHF Corporates & Markets | 5 | 1 | 1/1 | 1/1 | 13-report | Ambiguous amount overstated; forecasts/actuals framed as conflict. |
| Panmure Liberum | 3 | 1 | 1/1 | 1/1 | 13-report | Sampled values supported; draft may over-escalate revisions. |
| Pareto Securities | 6 | 1 | 1/1 | 0/1 | 13-report | Recovered after budget stop; structured target row omitted. |
| Rothschild & Co Redburn | 6 | 1 | 1/1 | 1/1 | 10-report | Reported bps misclassified; later offline correction is excluded. |
| Stifel Nicolaus | 4 | 2 | 2/2 | 1/2 | 13-report + Final regression | Earlier budget stop/draft mismatch; final run completes, with growth-direction wording error. |
| UBS | 7 | — | — | — | — | Not covered by the native batches summarized here. |
| Zurcher Kantonalbank | 7 | 1 | 1/1 | 1/1 | 13-report | Self-review corrected rating wording; share identity remains ambiguous. |

**Reading the totals:** the archived 10-report batch delivered 9/10 HTML files with 7/10 completed workflows; the 13-report batch delivered 13/13 with 10/13 completed workflows. The final regression delivered 2/2 with 2/2 completed workflows. HelloFresh appears in two batches, so 25 attempts represent 24 distinct PDFs. “—” means outside this table’s scope, not a failed test.

Four planned follow-ups are recorded separately: two in the 10-report batch and two in the final regression. The latter verified a cited answer without changing HTML and a compact rendering without changing research data.

**Cost and configuration:** Opus/high, recorded actual model `claude-opus-5`. Client list-cost estimates were USD22.016941 for the 10-report batch including follow-ups, USD32.256323 for the 13-report batch, and USD7.822414 for the final regression including follow-ups. These are recorded estimates, not subscription charges. Original outputs, failures, invocation settings and scoped source-review notes remain in the private evidence archive.

**Engineering checks:** 142 Python and 11 JavaScript tests pass. They verify application behavior using synthetic inputs, including citations, arithmetic, email decisions, follow-up and recovery. They do not establish research accuracy.

**Next evaluation, not run:** at most 30 distinct companies, one report per company, with broker coverage where the corpus allows. Freeze the selection and product version before starting.

[Submission contents](README.md) · [Review criteria](../evals/review-checklist.md)
