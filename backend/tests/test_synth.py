from __future__ import annotations

import pytest

from app.generator import synth
from app.generator.industry_map import classify
from app.generator.rice import compute_rice_plus_plus


def test_synth_deterministic_across_calls() -> None:
    a = synth.synthesize("randomyc", "randomyc.io")
    b = synth.synthesize("randomyc", "randomyc.io")
    assert a.model_dump(mode="json") == b.model_dump(mode="json")


def test_synth_distinct_outputs_for_distinct_domains() -> None:
    a = synth.synthesize("alpha", "alpha.io")
    b = synth.synthesize("beta", "beta.io")
    # Different seeds → at least the seed/domain differs, and likely RICE numbers too.
    assert a.meta.seed != b.meta.seed
    assert a.company.domain != b.company.domain


def test_synth_top_rice_in_target_band() -> None:
    for slug, domain in [
        ("webflow", "webflow.com"),
        ("supabase", "supabase.com"),
        ("posthog", "posthog.com"),
        ("retool", "retool.com"),
        ("warp", "warp.dev"),
    ]:
        run = synth.synthesize(slug, domain)
        assert 78.0 <= run.top_epic.rice.composite <= 95.5, (
            f"{slug}: composite {run.top_epic.rice.composite} out of synth band"
        )


def test_synth_composite_matches_formula() -> None:
    for slug, domain in [("foo", "foo.com"), ("bar", "bar.io"), ("baz", "baz.dev")]:
        run = synth.synthesize(slug, domain)
        rice = run.top_epic.rice
        recomputed = compute_rice_plus_plus(
            rice.reach, rice.impact, rice.confidence, rice.effort,
            rice.urgency, rice.strategy, rice.risk_inv,
        )
        assert abs(recomputed - rice.composite) < 0.2, slug


def test_synth_output_shape_invariants() -> None:
    run = synth.synthesize("acmecloud", "acmecloud.dev")
    assert run.company.tier == "synth"
    assert run.meta.generator == "synth"
    assert 12 <= len(run.ingest.stream_samples) <= 15
    assert 5 <= len(run.clusters) <= 7
    assert sum(1 for c in run.clusters if c.is_top) == 1
    s = run.ingest.sentiment_pct
    assert s.positive + s.neutral + s.negative == 100
    assert sum(src.count for src in run.ingest.sources) == run.ingest.signal_count
    assert len(run.top_epic.acceptance_criteria) >= 3
    assert len(run.top_epic.evidence) >= 3


@pytest.mark.parametrize(
    "slug, domain, expected",
    [
        ("acmebank",   "acmebank.com",   "fintech"),
        ("acmestore",  "acmestore.shop", "commerce"),
        ("acmecloud",  "acmecloud.dev",  "developer"),
        ("acmeai",     "acmeai.ai",      "ai"),
        ("acmehealth", "acmehealth.com", "healthtech"),
        ("acmelearn",  "acmelearn.com",  "edtech"),
        ("randomthing","randomthing.io", "saas"),
        ("webflow",    "webflow.com",    "developer"),
    ],
)
def test_industry_classifier_routing(slug: str, domain: str, expected: str) -> None:
    assert classify(slug, domain) == expected
