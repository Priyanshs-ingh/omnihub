"""RICE++ composite scoring.

Tuned so the canonical Stripe catalog seed
``(reach=92, impact=88, confidence=96, effort=18, urgency=91, strategy=84, risk_inv=77)``
lands at ``93.2`` (matches the authored composite in spec section 4.3).

Formula:
    base      = mean(reach, impact, confidence)
    effort    = base * (1 - 0.07 * effort/100)         # mild effort discount
    modifier  = 1 + 0.025 * (urgency + strategy + risk_inv - 150) / 100
    composite = clamp(effort * modifier, 0, 99.9)
"""

from __future__ import annotations


def compute_rice_plus_plus(
    reach: int,
    impact: int,
    confidence: int,
    effort: int,
    urgency: int,
    strategy: int,
    risk_inv: int,
) -> float:
    """Composite RICE++ score in [0, 99.9], one decimal place.

    All inputs are 0-100. ``effort`` is positively oriented (higher = harder).
    ``risk_inv`` is inverse risk (higher = lower risk).
    """
    base = (reach + impact + confidence) / 3
    effort_adjusted = base * (1 - 0.07 * effort / 100)
    modifier = 1.0 + 0.025 * (urgency + strategy + risk_inv - 150) / 100
    composite = effort_adjusted * modifier
    return round(max(0.0, min(composite, 99.9)), 1)
