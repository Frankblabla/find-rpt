// Synthetic display regression cases. These tests do not call a model or read PDFs.
import test from "node:test";
import assert from "node:assert/strict";
import { groupEstimates, revisionDisplay } from "../static/estimates.mjs";
const row = (metric, year, old, current, extra = {}) => ({
  metric,
  fiscal_year: year,
  units: "EUR",
  old,
  new: current,
  reported_revision_pct: null,
  consensus_after: null,
  ...extra,
});

test("margin changes display percentage points; relative changes stay distinct", () => {
  assert.equal(
    revisionDisplay(
      row("Margin", "FY26", 4.3, 4.5, { units: "%; fiscal year" }),
      4.65116,
    ).text,
    "+0.2 percentage points",
  );
  assert.equal(
    revisionDisplay(row("Margin", "FY27", 1, 0, { units: "percent" }), -100)
      .text,
    "-1 percentage points",
  );
  assert.equal(
    revisionDisplay(row("Margin", "FY28", null, 4.5, { units: "%" }), null)
      .text,
    "Not available",
  );
  assert.equal(
    revisionDisplay(
      row("EPS", "FY26", 3.52, 3.5, { reported_revision_pct: -0.8 }),
      -0.568,
    ).text,
    "-0.8%",
  );
});

test("all changed groups and their years stay visible after repeated contextual EPS rows", () => {
  const rows = Array.from({ length: 8 }, (_, i) =>
    row(`EPS context variant ${i}`, "FY26", null, 0.55),
  );
  rows.push(
    row("Operating profit", "FY26", 100, 110),
    row("Free cash flow", "FY26", 40, 45),
    row("Operating profit", "FY27", 120, 135),
    row("Dividend per share", "FY26", 1, 0.99),
    row("Dividend per share", "FY27", 1.11, 1.1),
  );
  const frozen = JSON.stringify(rows),
    groups = groupEstimates(rows);
  assert.deepEqual(
    groups.primary.map((g) => g.metric),
    ["Operating profit", "Free cash flow", "Dividend per share"],
  );
  assert.deepEqual(
    groups.primary[0].rows.map((r) => r.row.fiscal_year),
    ["FY26", "FY27"],
  );
  assert.equal(groups.primary[2].rows.length, 2);
  assert.equal(groups.additional.length, 8);
  assert.equal(JSON.stringify(rows), frozen);
});

test("reported nonzero revisions count even when printed levels round equal; zero is no revision", () => {
  const groups = groupEstimates([
    row("EPS", "FY26", 1, 1, { reported_revision_pct: 0.2 }),
    row("Sales", "FY26", 100, 100, { reported_revision_pct: 0 }),
  ]);
  assert.deepEqual(
    groups.primary.map((g) => g.metric),
    ["EPS"],
  );
  assert.deepEqual(
    groups.additional.map((g) => g.metric),
    ["Sales"],
  );
});

test("no-revision comparison stays visible; standalone consensus and distinct EPS definitions are not merged", () => {
  const groups = groupEstimates([
    row("Adjusted EPS", "FY26", null, 0.55, { consensus_after: 0.38 }),
    row("Reported EPS", "FY26", null, 0.33),
    row("Consensus EPS", "FY26", null, null, { consensus_after: 0.38 }),
  ]);
  assert.equal(groups.primary.length, 1);
  assert.equal(groups.primary[0].rows[0].row.consensus_after, 0.38);
  assert.equal(groups.additional.length, 2);
  assert.equal(groups.additional[1].rows[0].row.new, null);
});

test("source-assessed qualitative revision stays visible without invented arithmetic", () => {
  const qualitative = row("Margin", "FY28", null, 29.9, { units: "%", reason: "stated" });
  const currentOnly = row("Revenue", "FY28", null, 100, { reason: "not_a_revision" });
  const frozen = JSON.stringify(qualitative);
  assert.deepEqual(groupEstimates([currentOnly, qualitative]).primary.map(g => g.metric), ["Margin"]);
  assert.deepEqual(revisionDisplay(qualitative, null), {
    text: "Qualitative revision", basis: "Exact change unavailable",
  });
  assert.equal(revisionDisplay(currentOnly, null).text, "Not available");
  assert.equal(JSON.stringify(qualitative), frozen);
});

test("a numeric zero baseline is not mistaken for an unavailable prior forecast", () => {
  assert.deepEqual(
    revisionDisplay(row("Margin", "FY28", 0, 5, { units: "%", reason: "stated" }), null),
    { text: "+5 percentage points", basis: "Calculated difference in percentage-valued levels" },
  );
  const eps = revisionDisplay(row("EPS", "FY28", 0, 5, { reason: "stated" }), null);
  assert.equal(eps.text, "Not available");
  assert.notEqual(eps.basis, "Exact change unavailable");
});

test("reported basis points take precedence over equal rounded levels", () => {
  const margin = row("Margin", "FY28", 16, 16, { units: "%", reported_revision_bps: 2 });
  assert.equal(groupEstimates([margin]).primary[0].changed, true);
  assert.deepEqual(revisionDisplay(margin, 0), {
    text: "+2 bps", basis: "Reported basis-point change",
  });
});
