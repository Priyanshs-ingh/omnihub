from __future__ import annotations

import pytest

from app.generator import catalog
from app.generator.resolver import InvalidDomainError, normalize
from app.generator.rice import compute_rice_plus_plus


def test_rice_plus_plus_stripe_seed_lands_at_93_2() -> None:
    score = compute_rice_plus_plus(
        reach=92, impact=88, confidence=96, effort=18,
        urgency=91, strategy=84, risk_inv=77,
    )
    assert abs(score - 93.2) < 0.5


def test_rice_plus_plus_is_clamped() -> None:
    assert compute_rice_plus_plus(100, 100, 100, 0, 100, 100, 100) <= 99.9
    assert compute_rice_plus_plus(0, 0, 0, 100, 0, 0, 0) >= 0.0


def test_rice_plus_plus_one_decimal_place() -> None:
    score = compute_rice_plus_plus(70, 75, 80, 30, 60, 60, 60)
    # round() returns a float; assert no spurious precision.
    assert score == round(score, 1)


@pytest.mark.parametrize(
    "raw, expected_slug, expected_domain",
    [
        ("stripe.com", "stripe", "stripe.com"),
        ("https://www.stripe.com/atlas", "stripe", "stripe.com"),
        ("STRIPE", "stripe", "stripe.com"),
        ("  stripe  ", "stripe", "stripe.com"),
        ("https://github.com", "github", "github.com"),
        ("airbnb.co.uk", "airbnb", "airbnb.co.uk"),
    ],
)
def test_normalize_returns_consistent_slug(raw: str, expected_slug: str, expected_domain: str) -> None:
    n = normalize(raw)
    assert n.slug == expected_slug
    assert n.domain == expected_domain


@pytest.mark.parametrize("raw", ["", "   ", None])
def test_normalize_rejects_empty(raw: str | None) -> None:
    with pytest.raises(InvalidDomainError):
        normalize(raw)  # type: ignore[arg-type]


def test_catalog_loads_all_five_companies() -> None:
    expected = {"stripe", "shopify", "notion", "airbnb", "github"}
    tiles = {t.slug for t in catalog.tiles()}
    assert expected.issubset(tiles)


def test_catalog_lookup_by_slug_and_domain() -> None:
    by_slug = catalog.lookup("stripe")
    by_domain = catalog.lookup("stripe.com")
    assert by_slug is not None
    assert by_domain is not None
    assert by_slug.company.slug == by_domain.company.slug == "stripe"


def test_catalog_authored_composite_matches_formula() -> None:
    """Each catalog top-epic composite should be reachable by the RICE++ formula
    from its own RICE inputs (within rounding)."""
    for tile in catalog.tiles():
        run = catalog.lookup(tile.slug)
        assert run is not None
        rice = run.top_epic.rice
        recomputed = compute_rice_plus_plus(
            rice.reach, rice.impact, rice.confidence, rice.effort,
            rice.urgency, rice.strategy, rice.risk_inv,
        )
        assert abs(recomputed - rice.composite) < 0.5, (
            f"{tile.slug}: authored {rice.composite}, formula {recomputed}"
        )
