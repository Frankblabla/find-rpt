# Submission contents

Start with the repository [README](../README.md) to run the agent, then use the
[implementation walkthrough](../docs/implementation.md) to understand its design.
The [deliverable checklist](../docs/deliverables.md) maps the candidate brief to
the implementation. This folder packages selected examples and development logs
so a repository checkout does not depend on an ignored local evidence index.

| Requested item | Included material |
| --- | --- |
| Working implementation | `find_rpt/`, `app.py`, `.claude/skills/find-rpt/`, `templates/`, `static/` in the repository |
| Short README and run instructions | Root README, configuration example and [test guide](../tests/README.md) |
| A few actual examples | [Swatch HTML](examples/swatch-v3.html), [native conversation](examples/native-conversation.md), and the baseline examples below |
| Genuine AI development logs | [Readable development excerpt](development/transcript.md), [original selected visible events](development/visible-events.jsonl), and [later recovery development events](development/recovery-visible-events.jsonl) |

## Examples and their scope

- **Swatch version 3** is a saved output from the latest thirteen-broker evaluation.
  Its same-agent review corrected an unsupported unchanged-rating inference. The
  selected source spot-check found no unsupported final claim within its limited
  scope. Share-class/exchange identity remains ambiguous.
- **Native conversation** contains six actual product-use turns demonstrating
  source Q&A, presentation changes, content amendment and resume. It preserves
  two reviewer corrections. It is a development example, not a blind holdout or
  a development transcript. Historical case/version links require the original
  local case archive; its text remains readable in this checkout.
- [Hexagon](examples/hexagon-brief.md), [Grenergy](examples/grenergy-brief.md) and
  [Grenergy follow-up](examples/grenergy-followup.md) are faithful earlier baseline
  exports. They demonstrate revisions, comparisons, source conflicts and a real
  attached follow-up; they are not tests of the latest native product.

Source links open the local viewer on port 8765 and require the authorized corpus
and manifest described in the root README. The standalone HTML and Markdown are
readable without the viewer; historical version-navigation links require the
original case archive. Original PDFs are not included. The bundled [corpus manifest](corpus-manifest.json)
contains filenames, hashes and historical split labels only. Its isolation wording
is historical; the current application allows ordinary access to all 101 entries.

[Evaluation summary](evaluation.md) records test counts, actual broker attempts,
client costs and known limitations. Full private audits remain in `local/` and are
not necessary to read the included summary or examples.

## Log provenance and sharing boundary

The development excerpts are selected genuine English events, not reconstructed
chat. The earlier readable excerpt has nine events; the recovery excerpt has
eight actual tool-call/result events. Product conversations are labelled
separately. Chinese planning, hidden reasoning, full private logs, source PDFs and
credentials are excluded.

[Copy provenance](provenance.json) records each included artifact's original
local path and SHA-256. The adjacent development provenance files retain original
line numbers and source hashes. These selected artifacts are exact copies; old
claims, failed attempts and review corrections were not rewritten to look better.
Absolute paths in genuine logs describe the original development workspace and
are not fresh-checkout run instructions.

This repository publishes only the selected submission package. The original
private development archive remains local. Email drafts have never been sent.
