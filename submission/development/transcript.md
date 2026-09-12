# Selected English development transcript

These are genuine visible events from the English Codex development task, not a reconstruction and not product-agent example output. This selected excerpt shows an observed failure, the corrective work, tests, an independent review finding and the final outcome. It is explicitly an excerpt, not the complete development history. Omitted records include unrelated work, private report dumps, internal reasoning, system context and usage telemetry. The Chinese planning conversation is not included.

Record timestamps, original JSONL line numbers and SHA-256 digests are retained in the adjacent provenance files. Displayed tool arguments decode literal JSON string escapes for readability; source event fields in the JSONL export retain their original values. An end-of-message literal newline marker is rendered as a newline. No development event or successful result was invented.

## 2026-09-12T07:18:39.323Z - source record 2054

The fixes keep the existing evidence format. I’ve tightened the extraction guidance for note citations, contact details and policy exceptions, and added a check that follow-ups start from a completed result. I’m testing the draft and source-link paths with clearly labelled synthetic reports before using the fresh-call budget.


## 2026-09-12T07:25:53.919Z - source record 2185

Hexagon’s fresh run failed on a contract edge case: it identified a stated margin-forecast reduction, but the prior value is a range rather than an exact number. The validator rejected the row’s revision cause. I’ve preserved the failure and reported the blocker; Grenergy is now running.


## 2026-09-12T07:27:30.553Z - source record 2218

Actual tool call: exec

```diff
*** Begin Patch
*** Update File: /Users/macpp/workspace/agent_tool_test/tests/test_comparison_picture.py
@@
 def test_selected_api_preflight_never_opens_another_cover(corpus, monkeypatch):
@@
     assert response.status_code == 202 and opened
+
+
+@pytest.mark.parametrize("cause", ["stated", "not_stated"])
+def test_qualitative_revision_keeps_unknown_arithmetic_and_correct_email_semantics(cause):
+    from find_rpt.schema import comparisons
+
+    e = extracted_v3()
+    r = e.estimates[0]
+    e.estimates = [r]
+    e.estimate_picture.groups = []
+    r.metric = "EPS" if cause == "stated" else "Dividend per share"
+    r.old = r.consensus_after = r.reported_revision_pct = None
+    r.support.old = r.support.consensus_after = r.support.reported_revision_pct = []
+    r.reason = cause
+    r.reason_fact_ids = ["f4"] if cause == "stated" else []
+    r.note = f"FY26 {r.metric} rises from below EUR 1.00 to EUR 1.20; exact prior value unavailable."
+    lines = dict(LINES, p1l7=r.note)
+    e.quotes.append(Quote(line_id="p1l7", text=lines["p1l7"]))
+    r.note_sources = r.support.metric = r.support.fiscal_year = r.support.units = r.support.new = ["p1l7"]
+    original = e.model_dump_json()
+    b = compose(validate_extraction(e, lines), select_facts(e, REQUEST), REQUEST)
+    assert e.model_dump_json() == original
+    assert b.revisions_present and b.estimates[0].old is None
+    assert comparisons(b.estimates[0])["revision"] == {"absolute": None, "percent": None}
+    if cause == "stated":
+        assert b.rationale == "clear" and b.email_draft is None
+    else:
+        assert b.rationale == "unclear" and "Dividend per share (FY26)" in b.email_draft.body
+    r.note = ""
+    r.note_sources = []
+    with pytest.raises(ValueError, match="explicitly sourced note"):
+        validate_extraction(e, lines)
+
+
+@pytest.mark.parametrize("defect", ["equal_levels", "zero_rate", "no_current", "missing_cause", "bad_quote", "missing_year"])
+def test_qualitative_revision_does_not_bypass_numeric_or_source_gates(defect):
+    e = extracted_v3()
+    r = e.estimates[0]
+    r.old = r.reported_revision_pct = None
+    r.support.old = r.support.reported_revision_pct = []
+    r.note = "FY26 EPS rises to EUR 1.20 from below EUR 1.00."
+    lines = dict(LINES, p1l7=r.note)
+    e.quotes.append(Quote(line_id="p1l7", text=r.note))
+    r.note_sources = ["p1l7"]
+    if defect == "equal_levels":
+        r.old = r.new
+        r.support.old = ["p1l3"]
+    if defect == "zero_rate":
+        r.reported_revision_pct = 0
+        r.support.reported_revision_pct = ["p1l3"]
+    if defect == "no_current":
+        r.new = None
+        r.support.new = []
+    if defect == "missing_cause":
+        r.reason_fact_ids = []
+    if defect == "bad_quote":
+        e.quotes[-1].text = "Invented source text"
+    if defect == "missing_year":
+        r.support.fiscal_year = []
+    with pytest.raises(ValueError):
+        validate_extraction(e, lines)
*** Update File: /Users/macpp/workspace/agent_tool_test/tests/estimates.test.mjs
@@
 test("no-revision comparison stays visible; standalone consensus and distinct EPS definitions are not merged", () => {
@@
   assert.equal(groups.additional[1].rows[0].row.new, null);
 });
+
+test("source-assessed qualitative revision stays visible without invented arithmetic", () => {
+  const qualitative = row("Margin", "FY28", null, 29.9, { units: "%", reason: "stated" });
+  const currentOnly = row("Revenue", "FY28", null, 100, { reason: "not_a_revision" });
+  const frozen = JSON.stringify(qualitative);
+  assert.deepEqual(groupEstimates([currentOnly, qualitative]).primary.map(g => g.metric), ["Margin"]);
+  assert.deepEqual(revisionDisplay(qualitative, null), {
+    text: "Qualitative revision", basis: "Exact change unavailable",
+  });
+  assert.equal(revisionDisplay(currentOnly, null).text, "Not available");
+  assert.equal(JSON.stringify(qualitative), frozen);
+});
*** End Patch
```

```text
uv run pytest --basetemp=local/test-temp -q
node --test tests/estimates.test.mjs
node --check static/app.js
```

## 2026-09-12T07:27:31.420Z - source record 2222

```text
Script completed
Wall time 0.9 seconds
Output:

Exit code: 0
........................................................................ [ 87%]
..........                                                               [100%]
=============================== warnings summary ===============================
<frozen importlib._bootstrap>:491
<frozen importlib._bootstrap>:491
  <frozen importlib._bootstrap>:491: DeprecationWarning: builtin type SwigPyPacked has no __module__ attribute

<frozen importlib._bootstrap>:491
<frozen importlib._bootstrap>:491
  <frozen importlib._bootstrap>:491: DeprecationWarning: builtin type SwigPyObject has no __module__ attribute

<frozen importlib._bootstrap>:491
  <frozen importlib._bootstrap>:491: DeprecationWarning: builtin type swigvarlink has no __module__ attribute

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
82 passed, 5 warnings in 0.42s
<sys>:0: DeprecationWarning: builtin type swigvarlink has no __module__ attribute
TAP version 13
# Subtest: margin changes display percentage points; relative changes stay distinct
ok 1 - margin changes display percentage points; relative changes stay distinct
  ---
  duration_ms: 21.0025
  ...
# Subtest: all changed groups and their years stay visible after repeated contextual EPS rows
ok 2 - all changed groups and their years stay visible after repeated contextual EPS rows
  ---
  duration_ms: 0.684042
  ...
# Subtest: reported nonzero revisions count even when printed levels round equal; zero is no revision
ok 3 - reported nonzero revisions count even when printed levels round equal; zero is no revision
  ---
  duration_ms: 0.061292
  ...
# Subtest: no-revision comparison stays visible; standalone consensus and distinct EPS definitions are not merged
ok 4 - no-revision comparison stays visible; standalone consensus and distinct EPS definitions are not merged
  ---
  duration_ms: 0.0615
  ...
# Subtest: source-assessed qualitative revision stays visible without invented arithmetic
ok 5 - source-assessed qualitative revision stays visible without invented arithmetic
  ---
  duration_ms: 0.167792
  ...
1..5
# tests 5
# suites 0
# pass 5
# fail 0
# cancelled 0
# skipped 0
# todo 0
# duration_ms 59.953084

```

## 2026-09-12T07:28:02.610Z - source record 2234

The correction now treats a sourced qualitative revision separately from a calculable change. Hexagon’s unchanged extraction revalidates offline at 215 words, with the exact change still unavailable. Tests cover both stated and missing causes; the original fresh attempt remains a failure.


## 2026-09-12T07:36:29.609Z - source record 2449

Review caught a display bug: a move from 0% to 5% was labelled qualitative because its relative percentage change is undefined. I’ll fix it to show the exact five-percentage-point change and test the zero-denominator cases. No additional model call is needed.


## 2026-09-12T07:36:38.884Z - source record 2450

Actual tool call: exec

```diff
*** Begin Patch
*** Update File: /Users/macpp/workspace/agent_tool_test/static/estimates.mjs
@@
-  if (row.reported_revision_pct == null && calculatedPercent == null &&
+  if (row.old == null && row.new != null &&
+      row.reported_revision_pct == null && calculatedPercent == null &&
*** Update File: /Users/macpp/workspace/agent_tool_test/tests/estimates.test.mjs
@@
 test("source-assessed qualitative revision stays visible without invented arithmetic", () => {
@@
   assert.equal(JSON.stringify(qualitative), frozen);
 });
+
+test("a numeric zero baseline is not mistaken for an unavailable prior forecast", () => {
+  assert.deepEqual(
+    revisionDisplay(row("Margin", "FY28", 0, 5, { units: "%", reason: "stated" }), null),
+    { text: "+5 percentage points", basis: "Calculated difference in percentage-valued levels" },
+  );
+  const eps = revisionDisplay(row("EPS", "FY28", 0, 5, { reason: "stated" }), null);
+  assert.equal(eps.text, "Not available");
+  assert.notEqual(eps.basis, "Exact change unavailable");
+});
*** End Patch
```

```text
node --test tests/estimates.test.mjs
node --check static/app.js
git diff --check
uv run python - <<'PY'
import json,hashlib
from pathlib import Path
p=Path('local/iteration-04-development/checks.json');d=json.loads(p.read_text());d['javascript_tests']=6;d['final_code_sha256']['static/estimates.mjs']=hashlib.sha256(Path('static/estimates.mjs').read_bytes()).hexdigest();d['zero_baseline_display_fix']='Qualitative display requires unavailable old value and present new value; numeric 0% to5% renders +5 percentage points, EPS zero denominator is unavailable relative arithmetic, not a qualitative revision.';p.write_text(json.dumps(d,indent=2)+'\n')
s=json.loads(Path('local/runs/3620a1dbd1c544bbbd60ec2f21112537/status.json').read_text());print('Final Hexagon',{k:s.get(k) for k in ['status','elapsed_seconds','error','main_word_count','estimated_cost_usd']})
PY
```

## 2026-09-12T07:36:39.142Z - source record 2454

```text
Script completed
Wall time 0.3 seconds
Output:

Exit code: 0
TAP version 13
# Subtest: margin changes display percentage points; relative changes stay distinct
ok 1 - margin changes display percentage points; relative changes stay distinct
  ---
  duration_ms: 27.491416
  ...
# Subtest: all changed groups and their years stay visible after repeated contextual EPS rows
ok 2 - all changed groups and their years stay visible after repeated contextual EPS rows
  ---
  duration_ms: 0.866708
  ...
# Subtest: reported nonzero revisions count even when printed levels round equal; zero is no revision
ok 3 - reported nonzero revisions count even when printed levels round equal; zero is no revision
  ---
  duration_ms: 0.059416
  ...
# Subtest: no-revision comparison stays visible; standalone consensus and distinct EPS definitions are not merged
ok 4 - no-revision comparison stays visible; standalone consensus and distinct EPS definitions are not merged
  ---
  duration_ms: 0.419834
  ...
# Subtest: source-assessed qualitative revision stays visible without invented arithmetic
ok 5 - source-assessed qualitative revision stays visible without invented arithmetic
  ---
  duration_ms: 0.161041
  ...
# Subtest: a numeric zero baseline is not mistaken for an unavailable prior forecast
ok 6 - a numeric zero baseline is not mistaken for an unavailable prior forecast
  ---
  duration_ms: 0.087084
  ...
1..6
# tests 6
# suites 0
# pass 6
# fail 0
# cancelled 0
# skipped 0
# todo 0
# duration_ms 68.053667
Final Hexagon {'status': 'running', 'elapsed_seconds': None, 'error': None, 'main_word_count': None, 'estimated_cost_usd': None}

```

## 2026-09-12T07:37:40.455Z - source record 2475

The final fresh Hexagon run passed the independent targeted review at 216 words, including the qualitative margin revision, all nine core revised metric-years and the row notes. The synthetic draft test also passed independent review. I’m recording the final results and refreshing the development snapshot.

