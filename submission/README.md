# Submission contents

**[View results by broker](evaluation.md)** · **[How to open the brief and follow up](../README.md#read-the-brief-and-follow-up)**

Enter `/find-rpt` with the ticker, date and broker in Claude Code's terminal
conversation. **Open the HTML link in the agent's reply** to read the result in a
browser. Click a citation to inspect the highlighted original PDF. Then return to
the **same terminal conversation** to ask questions or request a new HTML version.
Email is draft-only.

Start with the repository [README](../README.md) to run the agent, then use the
[implementation walkthrough](../docs/implementation.md) to understand its design.
The [deliverable checklist](../docs/deliverables.md) maps the candidate brief to
the implementation. This folder packages selected examples and development logs
so a repository checkout does not depend on an ignored local evidence index.

| Requested item | Included material |
| --- | --- |
| Working implementation | `find_rpt/`, `app.py`, `.claude/skills/find-rpt/`, `templates/`, `static/` in the repository |
| Short README and run instructions | Root README, configuration example and [test guide](../tests/README.md) |
| A few actual examples | [Swatch HTML](examples/swatch-brief.html), [native conversation](examples/native-conversation.md), and the baseline examples below |
| Genuine AI development logs | [Readable development excerpt](development/transcript.md), [original selected visible events](development/visible-events.jsonl), and [later recovery development events](development/recovery-visible-events.jsonl) |

## Examples and their scope

- **Swatch brief** is a fresh output from the current workflow regression. It
  completed normally and returned its saved full link. A source spot-check covered
  the takeaway and selected estimate rows; it is not a full accuracy certificate.
  Share-class/exchange identity remains explicitly ambiguous. No semantic edits
  were made to the submitted copy.
- **Native conversation** contains six actual product-use turns demonstrating
  source Q&A, presentation changes, content amendment and resume. It preserves
  two reviewer corrections. It is a development example, not a blind holdout or
  a development transcript. Historical case/version links require the original
  local case archive; its text remains readable in this checkout.
- [Hexagon](examples/hexagon-brief.md), [Grenergy](examples/grenergy-brief.md) and
  [Grenergy follow-up](examples/grenergy-followup.md) are faithful earlier baseline
  exports. They demonstrate revisions, comparisons, source conflicts and a real
  attached follow-up; they are not tests of the latest native product.

Source links open the local viewer on port 8765 and require the authorized PDFs
in `corpus/`, as described in the root README. The standalone HTML and Markdown are
readable without the viewer. Example case/version links require the original
private case state; generate your own brief using the root README for a new local
case. Exact historical versions remain in the private evidence archive. Original PDFs are not included.

[Results by broker](evaluation.md) shows recorded deliveries, completed workflows,
and source-review findings in one table. Necessary private audits are consolidated in `local/evidence/` and are
not necessary to read the included summary or examples.

## Log provenance and sharing boundary

The development excerpts are selected genuine English events, not reconstructed
chat. The earlier readable excerpt has nine events; the recovery excerpt has
eight actual tool-call/result events. Product conversations are labelled
separately. Chinese planning, hidden reasoning, full private logs, source PDFs and
credentials are excluded.

[Copy provenance](provenance.json) records each included artifact's original
local path and SHA-256. The adjacent development provenance files retain original
line numbers and source hashes. Development excerpts are exact copies. The fresh Swatch HTML has only
whitespace-only lines normalized, as recorded in provenance. Earlier failures and
review corrections remain in their original records.
Absolute paths in genuine logs describe the original development workspace and
are not fresh-checkout run instructions.

This repository publishes only the selected submission package. The original
necessary evidence archive remains local. Email drafts have never been sent.
