# Evaluation by broker

**Current regression: 25/25 full HTML deliveries · 25/25 normal completions with full HTML · 25/25 final replies containing the latest link.**

The same 25 recorded report tasks were rerun on 13 September 2026 using one frozen
product version. Earlier development records delivered 24/25 full HTML files and
19/25 normally completed workflows. All six formerly incomplete workflows now
complete. These are reused development reports, not an unseen accuracy benchmark.
The [previous results](https://github.com/Frankblabla/find-rpt/blob/953736557b34404a8b0251dfabf322e22ff5f63f/submission/evaluation.md)
remain unchanged in their original record.

**Full HTML** means a saved full brief that passes source/structure checks.
**Completed** also requires normal native-client completion. **Final link** means
the last reply contains the latest saved URL; all 25 URLs were opened successfully.
These metrics do not establish complete extraction or correct interpretation.

| Broker | Attempts | Full HTML | Completed | Final link | Source spot-check and remaining limits |
| --- | ---: | ---: | ---: | ---: | --- |
| ABG Sundal Collier | 1 | 1/1 | 1/1 | 1/1 | Sampled values supported; image-only quarterly table remains unextracted. |
| Alantra Equities Sociedad de Valores, S.A. | 1 | 1/1 | 1/1 | 1/1 | Preview and sampled values supported; inferred quarterly units disclosed. |
| BNP Paribas | 1 | 1/1 | 1/1 | 1/1 | Cover supported; material image-table comparisons still omitted. |
| Berenberg | — | — | — | — | Outside this regression selection. |
| Bestinver Securities | 1 | 1/1 | 1/1 | 1/1 | Sampled company-section claims supported; target range retained outside scalar rows. |
| BofA Global Research | — | — | — | — | Outside this regression selection. |
| CIC Corporate & Institutional Banking | — | — | — | — | Outside this regression selection. |
| Citi | 1 | 1/1 | 1/1 | 1/1 | Sampled claims supported; listing identity explicitly ambiguous. |
| DNB Carnegie | 1 | 1/1 | 1/1 | 1/1 | Sampled revisions and consensus pair supported; source uncertainty retained. |
| Danske Bank Commissioned Research | 1 | 1/1 | 1/1 | 1/1 | Sourced valuation midpoint now included; image-table coverage remains incomplete. |
| Danske Bank Research | 1 | 1/1 | 1/1 | 1/1 | Target dividend qualifier still omitted; some table rows unextracted. |
| Degroof Petercam | 1 | 1/1 | 1/1 | 1/1 | Sampled values and target cause supported; source scale ambiguity disclosed. |
| Deutsche Bank Research | 1 | 1/1 | 1/1 | 1/1 | Sampled values supported; printed price/unit ambiguity disclosed. |
| Goldman Sachs | — | — | — | — | Outside this regression selection. |
| ING Wholesale Banking | 1 | 1/1 | 1/1 | 1/1 | Previously blocked target now publishes; full cover revision grid checked. |
| Intermonte Securities | 1 | 1/1 | 1/1 | 1/1 | Sampled values supported; 79 rows and 527 source lines saved. |
| JP Morgan | 1 | 1/1 | 1/1 | 1/1 | Dec-27 target qualifier publishes; sampled comparisons supported. |
| Jefferies | 1 | 1/1 | 1/1 | 1/1 | 2Q26 comparison now structured; no automatic draft; source disagreements disclosed. |
| KBC Securities | 1 | 1/1 | 1/1 | 1/1 | Sampled values supported; takeaway highlights omit some announcement context. |
| Kepler Cheuvreux | 1 | 1/1 | 1/1 | 1/1 | Sampled values supported; quarterly comparisons remain outside the forecast table. |
| Morgan Stanley | 1 | 1/1 | 1/1 | 1/1 | Market benchmark now explicit; sampled comparisons supported. |
| Nordea Equity Research | 1 | 1/1 | 1/1 | 1/1 | Sampled values supported; no prior estimates invented. |
| Oddo BHF Corporates & Markets | 1 | 1/1 | 1/1 | 1/1 | Material issue: ambiguous EUR14m parenthesis interpreted too confidently. |
| Panmure Liberum | 1 | 1/1 | 1/1 | 1/1 | Sampled values supported; draft may over-escalate outer-year revisions. |
| Pareto Securities | 1 | 1/1 | 1/1 | 1/1 | Sourced target now structured; adjusted-metric mapping remains qualified. |
| Rothschild & Co Redburn | 1 | 1/1 | 1/1 | 1/1 | All 15 forecast adjustments checked; nonzero bps preserved at equal rounded levels. |
| Stifel Nicolaus | 2 | 2/2 | 2/2 | 2/2 | Both runs deliver; mixed growth directions preserved; aggregation wording still needs care. |
| UBS | — | — | — | — | Outside this regression selection. |
| Zurcher Kantonalbank | 1 | 1/1 | 1/1 | 1/1 | Fresh submitted example; sampled values supported; identity remains ambiguous. |

**Selection and review scope:** 25 attempts represent 24 distinct PDFs; HelloFresh
appears twice to retain the earlier task set. Fifteen inputs retain a previously
confirmed file selection, so this is not a claim of universal automatic lookup.
“—” is untested here, not failed. Source spot-checks covered each takeaway, the
first driver when present, and first/middle/last estimate rows. Selected source
pages and complete revision grids received additional visual checks. The reviewer
was the development assistant, not a blinded human judge. “Supported” refers only
to that limited checked scope; the Soitec interpretation error and other omissions
are explicitly retained. No manual repair was counted as a fresh success.

**What changed:** inputs can cite original line IDs without transcribing quotes;
Python copies the exact source lines into saved evidence. Native Edit supports
small repairs. Word and item-count gates were removed, sourced valuation labels
were broadened, and up to three focused validation repairs are allowed. Source
identity, supplied-quote accuracy, field references and saved hashes remain checked.
Full links are shown promptly; a focused review and `deliver` finish the handoff.

**Configuration and cost:** Opus/high, actual recorded model `claude-opus-5`;
USD15 requested cap and 30-minute timeout per report, without a separate turn cap.
Four reports ran concurrently. No automatic batch retries or paid post-batch
repairs were used. There were **zero budget stops**. Total client list-cost estimate:
**USD61.46**, median **USD2.36/report**, highest **USD5.12/report**. Median elapsed
time was **4.98 minutes/report**, longest **14.29 minutes**. These cost estimates
are not subscription charges. The noninteractive permission profile still denied
46 optional helper commands; all clients continued through allowed tools. This
remains workflow friction, even though every session completed.

**Checks:** 154 Python and 11 JavaScript cases pass, including in a clean export
without source PDFs or private runtime data. All 25 HTML routes, 25 data routes,
50 source links and 25 mutually exclusive draft/no-draft outcomes were checked.
Every run left a same-agent review note; those notes are not independent accuracy
certificates. Inputs, frozen product hashes, raw events, first-attempt outcomes,
source spot-checks and link checks remain private under `local/evidence/`.

The next unseen evaluation, if requested, remains limited to at most 30 distinct
companies. This rerun did not expand to a new company sample.

[Submission contents](README.md) · [Run the evaluation](../tests/README.md#real-model-evaluations-are-separate) · [Review criteria](../evals/review-checklist.md)
