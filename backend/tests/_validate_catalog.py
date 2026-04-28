"""Ad-hoc validator for catalog JSONs. Not a pytest file. Run via: py tests/_validate_catalog.py [slug...]"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from app.generator.rice import compute_rice_plus_plus as rice_fn
from app.models import RunResponse


def validate(slug: str) -> bool:
    path = Path("app/data/companies") / f"{slug}.json"
    if not path.exists():
        print(f"{slug}: MISSING")
        return False
    payload = json.loads(path.read_text(encoding="utf-8"))
    try:
        run = RunResponse.model_validate(payload)
    except Exception as exc:
        print(f"{slug}: SCHEMA FAIL — {exc}")
        return False
    rice = run.top_epic.rice
    recomputed = rice_fn(
        rice.reach, rice.impact, rice.confidence, rice.effort,
        rice.urgency, rice.strategy, rice.risk_inv,
    )
    src_total = sum(s.count for s in run.ingest.sources)
    sent_sum = (
        run.ingest.sentiment_pct.positive
        + run.ingest.sentiment_pct.neutral
        + run.ingest.sentiment_pct.negative
    )
    streams = len(run.ingest.stream_samples)
    clusters = len(run.clusters)
    tops = sum(1 for c in run.clusters if c.is_top)
    ac = len(run.top_epic.acceptance_criteria)
    ev = len(run.top_epic.evidence)
    composite_ok = abs(recomputed - rice.composite) < 0.5

    issues: list[str] = []
    if not composite_ok:
        issues.append(f"composite drift {rice.composite} vs {recomputed}")
    if src_total != run.ingest.signal_count:
        issues.append(f"sources_sum {src_total} != signal_count {run.ingest.signal_count}")
    if sent_sum != 100:
        issues.append(f"sentiment sum {sent_sum} != 100")
    if not (12 <= streams <= 15):
        issues.append(f"streams {streams} not in [12,15]")
    if not (5 <= clusters <= 7):
        issues.append(f"clusters {clusters} not in [5,7]")
    if tops != 1:
        issues.append(f"is_top count {tops} != 1")
    if ac != 4:
        issues.append(f"acceptance_criteria {ac} != 4")
    if ev != 3:
        issues.append(f"evidence {ev} != 3")

    status = "OK" if not issues else "FAIL: " + "; ".join(issues)
    print(
        f"{slug}: composite={rice.composite}/{recomputed} "
        f"src={src_total}/{run.ingest.signal_count} sent={sent_sum} "
        f"streams={streams} clusters={clusters} ac={ac} ev={ev} -> {status}"
    )
    return not issues


if __name__ == "__main__":
    slugs = sys.argv[1:] or [
        p.stem for p in sorted(Path("app/data/companies").glob("*.json"))
    ]
    failed = [s for s in slugs if not validate(s)]
    print(f"\n{len(slugs) - len(failed)}/{len(slugs)} passed")
    sys.exit(1 if failed else 0)
