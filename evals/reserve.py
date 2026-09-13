"""Reserve whole broker groups using filenames and byte hashes, without parsing PDFs."""

import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
files = sorted((ROOT / "corpus").glob("*.pdf"))
rows = []
for path in files:
    date, broker, _ = path.stem.split("_", 2)
    rows.append(
        dict(
            file=path.name,
            date=date,
            broker=broker,
            sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        )
    )
# Whole brokers keep same-house revisions/near-duplicates together across dates.
brokers = sorted(
    {r["broker"] for r in rows},
    key=lambda b: hashlib.sha256(("find-rpt-iteration-01:" + b).encode()).hexdigest(),
)
held = set()
for broker in brokers:
    count = sum(r["broker"] == broker for r in rows)
    if len(held) + count <= 15:
        held.update(r["file"] for r in rows if r["broker"] == broker)
    if len(held) >= 12:
        break
# Also co-locate exact byte duplicates across broker labels.
hashes = {r["sha256"] for r in rows if r["file"] in held}
held.update(r["file"] for r in rows if r["sha256"] in hashes)
for row in rows:
    row["split"] = "acceptance" if row["file"] in held else "development"
result = dict(
    method="Filename-only whole-broker holdout; SHA256 exact duplicates co-located. Seed find-rpt-iteration-01. No report text read.",
    isolation="Application excludes acceptance; no OS-level isolation from developer. Cross-broker near-duplicates remain unverified.",
    reports=rows,
)
out = ROOT / "local/split.json"
if out.exists():
    raise SystemExit("Split already exists; refusing to replace it.")
out.write_text(json.dumps(result, indent=2) + "\n")
print(
    json.dumps(
        dict(
            total=len(rows),
            dates=Counter(r["date"] for r in rows),
            brokers=len(brokers),
            acceptance=len(held),
            development=len(rows) - len(held),
            exact_duplicate_groups=sum(
                n > 1 for n in Counter(r["sha256"] for r in rows).values()
            ),
        ),
        indent=2,
    )
)
