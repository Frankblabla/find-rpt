// Presentation only: keep every original row and its evidence, without merging definitions.
export function hasRevision(row) {
  return (
    row.reason === "stated" || row.reason === "not_stated" ||
    (row.reported_revision_pct != null && row.reported_revision_pct !== 0) ||
    (row.reported_revision_bps != null && row.reported_revision_bps !== 0) ||
    (row.old != null && row.new != null && row.old !== row.new)
  );
}

export function groupEstimates(rows) {
  const groups = new Map();
  rows.forEach((row, index) => {
    const key = JSON.stringify([
      row.metric.trim().toLowerCase(),
      row.units.trim().toLowerCase(),
    ]);
    if (!groups.has(key))
      groups.set(key, {
        metric: row.metric,
        units: row.units,
        rows: [],
        changed: false,
      });
    const group = groups.get(key);
    group.rows.push({ row, index });
    group.changed ||= hasRevision(row);
  });
  const all = [...groups.values()];
  const changed = all.filter((group) => group.changed);
  // A brief without revisions can still present the report's actual comparisons.
  const primary = changed.length
    ? changed
    : all.filter((group) =>
        group.rows.some(
          ({ row }) =>
            row.new != null && (row.old != null || row.consensus_after != null),
        ),
      );
  return {
    primary,
    additional: all.filter((group) => !primary.includes(group)),
  };
}

export function revisionDisplay(row, calculatedPercent) {
  if (row.reported_revision_bps != null) {
    const value = row.reported_revision_bps;
    return { text: `${value > 0 ? "+" : ""}${value} bps`, basis: "Reported basis-point change" };
  }
  if (row.old == null && row.new != null &&
      row.reported_revision_pct == null && calculatedPercent == null &&
      (row.reason === "stated" || row.reason === "not_stated")) {
    return { text: "Qualitative revision", basis: "Exact change unavailable" };
  }
  const percentageLevels =
    /^(?:%|percent(?:age)?(?: points)?)(?:$|[ ;,(])/i.test(row.units.trim());
  if (percentageLevels && row.old != null && row.new != null) {
    const delta = Math.round((row.new - row.old) * 1e9) / 1e9;
    return {
      text: `${delta > 0 ? "+" : ""}${delta.toLocaleString("en-GB", { maximumFractionDigits: 3 })} percentage points`,
      basis: "Calculated difference in percentage-valued levels",
    };
  }
  const value = row.reported_revision_pct ?? calculatedPercent;
  return {
    text:
      value == null
        ? "Not available"
        : `${value > 0 ? "+" : ""}${value.toFixed(1)}%`,
    basis:
      row.reported_revision_pct != null
        ? "Reported"
        : "Calculated relative change",
  };
}
