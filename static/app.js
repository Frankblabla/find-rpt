import { groupEstimates, revisionDisplay } from "./estimates.mjs";
const $ = (id) => document.getElementById(id);
const escape = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
let current = null,
  busy = false,
  searchGeneration = 0;
const number = (n) =>
  n == null
    ? "Not reported"
    : Number(n).toLocaleString("en-GB", { maximumFractionDigits: 3 });
const pct = (n) =>
  n == null ? "Not available" : `${n > 0 ? "+" : ""}${n.toFixed(1)}%`;
async function api(path, data) {
  const response = await fetch(
    path,
    data === undefined
      ? {}
      : {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(data),
        },
  );
  const result = await response.json();
  if (!response.ok)
    throw new Error(result.error || `Request failed (${response.status})`);
  return result;
}
function status(text, error = false) {
  $("status").textContent = text;
  $("status").className = error ? "error" : "";
}
function sourceLink(refs, label = "Source") {
  if (!refs?.length) return "";
  const url = `/source/${current.report.id}?refs=${encodeURIComponent(refs.join(","))}`;
  return ` <a class="cite" href="${url}" target="source" data-source="${url}">${escape(label)} ↗</a>`;
}
function inlineClaim(c, main = true) {
  return `${c.kind === "inference" ? '<span class="tag">Inference</span> ' : ""}${main ? "<span data-main-prose>" : "<span>"}${escape(c.text)}</span>${sourceLink(c.sources)}`;
}
function claim(c, main = true) {
  return `<p>${inlineClaim(c, main)}</p>`;
}
function section(title, content) {
  return `<section class="brief-section"><h3>${title}</h3>${content}</section>`;
}
function chart(e) {
  const points = [
    ["Old", e.old, "old"],
    ["New", e.new, "new"],
    ["Consensus", e.consensus_after, "consensus"],
  ].filter((p) => p[1] != null);
  if (points.length < 2) return "";
  const min = Math.min(0, ...points.map((p) => p[1])),
    max = Math.max(0, ...points.map((p) => p[1]));
  const span = max - min || 1,
    x = (v) => 95 + ((v - min) / span) * 340;
  return `<figure><figcaption>${escape(e.metric)} · ${escape(e.fiscal_year)} · ${escape(e.units)}${sourceLink(e.sources)}</figcaption><svg class="chart" viewBox="0 0 525 ${points.length * 30 + 15}" role="img" aria-label="${escape(points.map((p) => p[0] + " " + number(p[1])).join(", "))}"><line x1="${x(0)}" x2="${x(0)}" y1="5" y2="${points.length * 30}" stroke="#bcc8c8"/>${points.map(([label, value, cls], i) => `<text x="0" y="${i * 30 + 23}">${label}</text><rect class="${cls}" x="${Math.min(x(0), x(value))}" y="${i * 30 + 8}" width="${Math.max(Math.abs(x(value) - x(0)), 1)}" height="19" rx="3"/><text x="${x(value) + 6}" y="${i * 30 + 23}">${number(value)}</text>`).join("")}</svg></figure>`;
}
function render(result) {
  current = result;
  const b = result.brief;
  const manual = result.request.selection?.method === "user_confirmed";
  const selectionNotice = manual
    ? '<p class="small"><strong>User-confirmed file selection; cover ticker unverified.</strong> This is not source confirmation of the requested ticker.</p>' : "";
  const header = `<div class="brief-head"><div class="eyebrow">${escape(result.request.ticker)} · ${escape(result.report.broker)} · File date ${escape(result.request.lookup_date)}</div><h2>${escape(b.title)}</h2><div class="small">Printed report date: ${escape(b.report_date)} · Report identity assessment: ${escape(b.subject_match)}${sourceLink(b.identity.sources, "Identity")}</div>${selectionNotice}</div>`;
  if (b.subject_match !== "confirmed" && !(manual && b.subject_match === "ambiguous")) {
    $("result").innerHTML =
      header + section("Review the report identity", claim(b.identity));
    status(
      "The skill could not confirm this is the requested subject. Review the source before using the analysis.",
      true,
    );
    return;
  }
  const groups = groupEstimates(b.estimates.map((row, index) => ({
    ...row,
    reason: result.evidence?.schema_version === 3
      ? result.evidence.estimates[index]?.reason : undefined,
  })));
  function estimateTable(selectedGroups) {
    return `<div class="table-wrap"><table><thead><tr><th>Year / units / evidence</th><th>Old</th><th>New</th><th>Revision</th><th>Before vs consensus</th><th>After vs consensus</th></tr></thead><tbody>${selectedGroups
      .map(
        (group) =>
          `<tr class="estimate-group"><th colspan="6">${escape(group.metric)}</th></tr>` +
          group.rows
            .map(({ row: e, index: i }) => {
              const c = result.comparisons[i],
                revision = revisionDisplay(e, c.revision.percent);
              return `<tr><th>${escape(e.fiscal_year)}<small>${escape(e.units)}</small>${sourceLink(e.sources)}${e.note ? `<details><summary>Row note</summary><p>${escape(e.note)}</p></details>` : ""}${e.new == null && e.consensus_after != null ? "<small>Standalone consensus: no paired broker estimate in this saved row.</small>" : ""}</th><td>${number(e.old)}</td><td>${number(e.new)}</td><td>${escape(revision.text)}<small>${escape(revision.basis)}</small></td><td>${pct(c.before_consensus.percent)}<small>Δ ${number(c.before_consensus.absolute)}</small></td><td>${pct(c.after_consensus.percent)}<small>Δ ${number(c.after_consensus.absolute)}</small></td></tr>`;
            })
            .join(""),
      )
      .join("")}</tbody></table></div>`;
  }
  const estimates = b.estimates.length
    ? `<p class="small">Presentation: all changed metric groups and their years appear first. Other estimates remain below; definitions are not merged.</p>${estimateTable(groups.primary)}${groups.additional.length ? `<details><summary>Additional estimates and comparisons (${groups.additional.reduce((n, g) => n + g.rows.length, 0)} rows)</summary>${estimateTable(groups.additional)}</details>` : ""}<details><summary>Calculation basis and row notes</summary><p>Percentage-valued levels use percentage-point differences. Other calculated revisions use (new − old) / |old|. Relative changes remain below. Consensus differences use the respective reported prior/current values; missing values remain unavailable. Reported rates can differ from rounded-level arithmetic.</p>${b.estimates.map((e, i) => `<p><strong>${escape(e.metric)} ${escape(e.fiscal_year)}</strong>: ${escape(e.note)} Old/new calculated relative revision: ${pct(result.comparisons[i].revision.percent)}. Prior consensus: ${number(e.consensus_before)}; current consensus: ${number(e.consensus_after)}.${sourceLink(e.sources)}</p>`).join("")}</details>`
    : "<p>No comparable estimate levels reported.</p>";
  let content =
    header + claim(b.takeaway) +
    section(
      "What changed",
      b.changes.map((c) => claim(c)).join("") + estimates,
    ) +
    section(
      "Why it changed, and why now",
      (b.drivers.length ? `<p>${b.drivers.map((c) => inlineClaim(c)).join(" ")}</p>` : "") + claim(b.context),
    ) +
    section(
      "The estimate picture",
      claim(b.estimate_picture) +
        '<p class="small">Charts show up to three available comparisons; the tables retain every row.</p>' +
        b.estimates
          .filter(
            (e) =>
              [e.old, e.new, e.consensus_after].filter((v) => v != null)
                .length >= 2,
          )
          .slice(0, 3)
          .map(chart)
          .join(""),
    );
  if (b.material.length)
    content += section(
      "Also worth reading",
      b.material.map((c) => claim(c)).join(""),
    );
  if (b.email_draft) {
    const d = b.email_draft;
    content += section(
      "Email draft",
      '<p>Draft only — never sent.</p>' +
      `<div class="draft"><p><strong>To:</strong> ${escape(d.analyst)} &lt;${escape(d.to)}&gt;${sourceLink(d.sources, "Analyst and revisions")}</p><p><strong>Subject:</strong> ${escape(d.subject)}</p><pre>${escape(d.body)}</pre></div>`,
    );
  } else {
    const reason = !b.revisions_present
      ? "No email drafted: no estimate revisions were identified in this report."
      : b.rationale === "clear"
        ? "No email drafted: the report explains the identified estimate revisions."
        : "Email draft unavailable: some revisions remain unexplained. The clarification step is incomplete.";
    content += section("Email", `<p>${reason}</p>`);
  }
  if (b.answer.length)
    content += section(
      "Follow-up answer",
      `<p class="question">${escape(result.request.question)}</p>` +
        b.answer.map((c) => claim(c, false)).join(""),
    );
  content += section(
    "Ask about this report",
    `<form id="followup"><label class="sr-only" for="question">Follow-up question</label><textarea id="question" required maxlength="3000" placeholder="What supports the margin change? Did the broker speak to management?"></textarea><button>Ask a follow-up</button></form><p class="small">Each follow-up re-reads the selected report. Previous questions are retained.</p>`,
  );
  if (result.evidence) {
    const e = result.evidence;
    const details = [
      e.identity,
      e.takeaway,
      ...e.changes,
      ...e.drivers,
      e.event,
      ...(e.schema_version === 3
        ? e.estimate_picture.scenario
          ? [e.estimate_picture.scenario]
          : []
        : [e.estimate_picture]),
      ...e.material,
      ...e.conflicts,
      ...e.answer,
    ];
    content += `<details><summary>Evidence detail (${details.length} facts; ${result.main_word_count} main-prose words)</summary>
      <p>Exact source quotations and field references are checked locally. This does not prove every interpretation or establish complete extraction.</p>
      ${details.map((f) => `<p><strong>${escape(f.id)}</strong> ${escape(f.text)}${sourceLink(f.sources)}</p>`).join("")}
      ${result.comparison_provenance?.length ? `<details><summary>Comparison coverage</summary>${result.comparison_provenance.map((g) => `<p><strong>${escape(g.metric)}</strong> · ${escape(g.basis)} · ${escape(g.fiscal_years.join(", "))} · rows ${escape(g.row_ids.join(", "))}${sourceLink(g.sources)}</p>`).join("")}</details>` : ""}
      <details><summary>Original line quotations</summary>${e.quotes.map((q) => `<p><strong>${escape(q.line_id)}</strong> ${escape(q.text)}${sourceLink([q.line_id])}</p>`).join("")}</details>
      </details>`;
  }
  if (b.limitations.length)
    content += `<details><summary>Limitations (${b.limitations.length})</summary>${b.limitations.map((x) => `<p>${escape(x)}</p>`).join("")}</details>`;
  content += result.offline_revalidation
    ? `<p class="small">Saved run ${escape(result.run_id)} · Offline revalidation · No new model call · Source run ${escape(result.source_run_id)}. Original extraction preserved; checked and composed locally.</p>`
    : `<p class="small">Saved run ${escape(result.run_id)} · Analysis generated by ${escape(result.runtime?.harness || "Codex (saved baseline)")}${result.runtime ? " · " + escape(result.runtime.configured_model) + " · " + escape(result.runtime.effort) + " effort" : ""}. Source links validate locations; interpretation still needs review.</p>`;

  $("result").innerHTML = content;
  $("followup").onsubmit = (event) => {
    event.preventDefault();
    start(
      result.report.id,
      result.request.ticker,
      $("question").value,
      result.run_id,
    );
  };
}
function showSource(url) {
  $("source-empty").hidden = true;
  $("source").hidden = false;
  $("source").src = url;
  $("source-open").hidden = false;
  $("source-open").href = url;
}
document.addEventListener("click", (event) => {
  const link = event.target.closest("[data-source]");
  if (link) {
    event.preventDefault();
    showSource(link.dataset.source);
  }
});
async function refreshHistory() {
  const runs = await api("/api/runs");
  $("history").innerHTML = runs.length
    ? runs
        .map(
          (r) =>
            `<button class="history-item" data-run="${r.id}"><strong>${escape(r.request.ticker)} · ${escape(r.request.broker)}</strong><span>${escape(r.offline_revalidation ? "Offline revalidation" : r.request.question || "Research brief")} · ${escape(r.status)} · ${r.elapsed_seconds ?? "…"}s</span></button>`,
        )
        .join("")
    : '<p class="small">Completed and failed attempts will appear here.</p>';
  $("history")
    .querySelectorAll("[data-run]")
    .forEach(
      (button) =>
        (button.onclick = async () => {
          if (busy)
            return status(
              "A run is in progress. Wait for it to finish before opening another.",
            );
          try {
            const r = await api("/api/runs/" + button.dataset.run);
            if (r.result) {
              render(r.result);
              status(`Loaded saved run (${r.elapsed_seconds}s).`);
            } else
              status(
                r.error ||
                  `Run is ${r.status}${r.active_stage ? " (" + r.active_stage + ")" : ""}.`,
                true,
              );
          } catch (e) {
            status(e.message, true);
          }
        }),
    );
}
async function start(id, ticker, question = "", parent_id = null, confirm_selection = false) {
  if (busy) return;
  busy = true;
  current = null;
  $("result").innerHTML = "";
  document.querySelectorAll("button").forEach((b) => (b.disabled = true));
  const started = Date.now();
  try {
    status(
      "Claude Code is reading the selected report and running the skill. This can take several minutes.",
    );
    const job = await api("/api/runs", {
      report_id: id,
      ticker,
      question,
      parent_id,
      confirm_selection,
      model: $("model").value,
      effort: $("effort").value,
    });
    while (true) {
      await new Promise((resolve) => setTimeout(resolve, 2000));
      const r = await api("/api/runs/" + job.id);
      if (r.status === "complete") {
        render(r.result);
        status(
          `Completed in ${r.elapsed_seconds}s. The run and source references are saved locally.`,
        );
        break;
      }
      if (r.status === "failed") throw new Error(r.error);
      status(
        `Claude Code ${r.status} · ${Math.round((Date.now() - started) / 1000)}s elapsed. You can inspect source pages while it works.`,
      );
    }
  } catch (e) {
    status(e.message, true);
  } finally {
    busy = false;
    document.querySelectorAll("button").forEach((b) => (b.disabled = false));
    document.querySelectorAll("[data-manual]").forEach((b) => {
      b.disabled = !$("confirm-" + b.dataset.report)?.checked;
    });
    await refreshHistory();
  }
}
$("search").onsubmit = async (event) => {
  event.preventDefault();
  if (busy) return;
  const generation = ++searchGeneration;
  const searchTicker = $("ticker").value;
  $("matches").innerHTML = "";
  try {
    status("Checking cover identifiers within the selected date and broker.");
    const r = await api("/api/lookup", {
      ticker: searchTicker,
      date: $("date").value,
      broker: $("broker").value,
    });
    if (generation !== searchGeneration) return;
    $("matches").innerHTML = r.candidates
      .map(
        (c) =>
          `<div class="match"><div><strong>${escape(c.file)}</strong><p>${escape(c.evidence.map((e) => e.text).join(" · "))}${c.alias_used ? " · GY/GR alias applied" : ""}</p><a href="/source/${c.id}?refs=${c.evidence.map((e) => e.id).join(",")}" data-source="/source/${c.id}?refs=${c.evidence.map((e) => e.id).join(",")}">Inspect identity ↗</a></div><button data-report="${c.id}">Create brief</button></div>`,
      )
      .join("") + (r.review_candidates?.length ? '<h3>Other files to review — ticker unverified</h3>' + r.review_candidates.map(c =>
        `<div class="match"><div><strong>${escape(c.file)}</strong><p>No supported cover match for ${escape(searchTicker)}.</p><a href="/source/${c.id}" data-source="/source/${c.id}">Review original PDF ↗</a><label><input type="checkbox" id="confirm-${c.id}"> I reviewed this file and confirm it is the report I want analysed for ${escape(searchTicker)}.</label></div><button data-report="${c.id}" data-manual disabled>Analyse my confirmed selection</button></div>`
      ).join("") : "");
    status(
      r.status === "no_match"
        ? (r.review_candidates?.length ? "No verified cover match. Review the filtered PDFs and explicitly confirm a file to analyse." : "No files for this date and broker. Check the inputs.")
        : r.status === "ambiguous"
          ? "Multiple plausible reports found. Inspect their covers and choose one."
          : "One report found. Inspect it or create the brief.",
    );
    $("matches")
      .querySelectorAll("[data-report]")
      .forEach(
        (button) =>
          (button.onclick = () => {
            const manual = button.hasAttribute("data-manual");
            const confirmed = manual && $("confirm-" + button.dataset.report).checked;
            if (manual && !confirmed) return status("Confirm the reviewed file before analysis.", true);
            start(button.dataset.report, searchTicker, "", null, confirmed);
          }),
      );
    $("matches").querySelectorAll('[id^="confirm-"]').forEach(input => {
      input.onchange = () => {
        $("matches").querySelector(`[data-report="${input.id.slice(8)}"]`).disabled = !input.checked;
      };
    });
  } catch (e) {
    if (generation === searchGeneration) status(e.message, true);
  }
};
(async () => {
  try {
    const c = await api("/api/catalog");
    for (const [id, values, selected] of [
      ["model", c.models, c.default_model],
      ["effort", c.efforts, c.default_effort],
    ]) {
      $(id).innerHTML = values
        .map(
          (value) =>
            `<option value="${escape(value)}" ${value === selected ? "selected" : ""}>${escape(value)}</option>`,
        )
        .join("");
    }
    $("broker").innerHTML = c.brokers
      .map(
        (b) =>
          `<option ${b === "Kepler Cheuvreux" ? "selected" : ""}>${escape(b)}</option>`,
      )
      .join("");
    $("coverage").textContent =
      c.total
        ? `${c.total} reports available · File dates can differ from printed release dates`
        : 'Place research PDFs in corpus/ using YYYYMMDD_Broker_hash.pdf filenames, then reload.';
    await refreshHistory();
  } catch (e) {
    status(e.message, true);
  }
})();
