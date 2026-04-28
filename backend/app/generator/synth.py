"""Deterministic synthetic OmniHub run for any unknown domain.

Same domain in → byte-identical run out, every time. Seed comes from a stable
hash (md5) of the canonical domain so the synth is reproducible across processes
and machines.
"""

from __future__ import annotations

import hashlib
import random
from datetime import datetime, timezone

from ..models import (
    Cluster,
    Company,
    CompanyMark,
    ConfluenceDoc,
    Evidence,
    Ingest,
    JiraTicket,
    Meta,
    Rice,
    RunResponse,
    SentimentPct,
    Source,
    StreamSample,
    Sync,
    TopEpic,
)
from . import templates
from .industry_map import classify
from .rice import compute_rice_plus_plus

# Industry-realistic ranges. Synth never produces a "RICE 41" recommendation —
# investors don't want to see lukewarm output.
_SIGNAL_VOLUME_RANGE = (8_000, 60_000)
_TOP_RICE_RANGE = (78.0, 95.5)
_NAME_OVERRIDES = {
    "openai": "OpenAI",
    "youtube": "YouTube",
    "github": "GitHub",
    "tiktok": "TikTok",
    "doordash": "DoorDash",
    "linkedin": "LinkedIn",
    "ebay": "eBay",
    "ipad": "iPad",
    "iphone": "iPhone",
    "imessage": "iMessage",
    "icloud": "iCloud",
    "macbook": "MacBook",
    "airbnb": "Airbnb",
    "hubspot": "HubSpot",
}


def _seed_for(domain: str) -> int:
    """Stable across processes — the built-in ``hash()`` is salted per-process."""
    digest = hashlib.md5(domain.encode("utf-8")).hexdigest()
    return int(digest[:12], 16)


def _company_name(slug: str) -> str:
    if slug in _NAME_OVERRIDES:
        return _NAME_OVERRIDES[slug]
    # Title-case with hyphen handling: "ridge-wallet" → "Ridge Wallet"
    return " ".join(part.capitalize() for part in slug.replace("-", " ").split())


def _allocate_counts(total: int, weights: list[float], rng: random.Random) -> list[int]:
    """Distribute ``total`` across buckets per ``weights``, preserving sum exactly."""
    raw = [total * w for w in weights]
    counts = [int(r) for r in raw]
    leftover = total - sum(counts)
    # Distribute leftover by jittered remainder to avoid always loading bucket 0.
    fractions = sorted(
        ((raw[i] - counts[i]) + rng.random() * 1e-3, i) for i in range(len(weights))
    )
    for _, i in fractions[-leftover:] if leftover else ():
        counts[i] += 1
    return counts


def _split_sentiment(rng: random.Random) -> SentimentPct:
    pos = rng.randint(15, 25)
    neu = rng.randint(28, 38)
    neg = 100 - pos - neu
    return SentimentPct(positive=pos, neutral=neu, negative=neg)


def _pick_top_rice(seed: dict[str, int], rng: random.Random) -> Rice:
    """Jitter the template's RICE seed by ±3 until composite lands in target band."""
    for _ in range(80):
        jittered = {k: max(1, min(99, v + rng.randint(-3, 3))) for k, v in seed.items()}
        composite = compute_rice_plus_plus(
            jittered["reach"], jittered["impact"], jittered["confidence"],
            jittered["effort"], jittered["urgency"], jittered["strategy"],
            jittered["risk_inv"],
        )
        if _TOP_RICE_RANGE[0] <= composite <= _TOP_RICE_RANGE[1]:
            return Rice(**jittered, composite=composite)
    # Fallback: use the seed verbatim and accept whatever composite emerges.
    composite = compute_rice_plus_plus(
        seed["reach"], seed["impact"], seed["confidence"],
        seed["effort"], seed["urgency"], seed["strategy"], seed["risk_inv"],
    )
    return Rice(**seed, composite=composite)


def synthesize(slug: str, domain: str) -> RunResponse:
    rng = random.Random(_seed_for(domain))
    industry = classify(slug, domain)
    bank = templates.get(industry)
    name = _company_name(slug)

    # Mark
    mark = CompanyMark(
        bg=rng.choice(bank.mark_palette),
        char=name[0].upper(),
    )

    # Volumes
    signal_count = rng.randint(*_SIGNAL_VOLUME_RANGE)
    runtime_seconds = rng.randint(28, 52)
    sentiment_pct = _split_sentiment(rng)

    # Sources — preserve relative weights, but jitter slightly so the same industry
    # doesn't produce identical breakdowns for every domain.
    raw_weights = [s.weight * rng.uniform(0.85, 1.15) for s in bank.sources]
    norm = sum(raw_weights)
    weights = [w / norm for w in raw_weights]
    counts = _allocate_counts(signal_count, weights, rng)
    sources = [
        Source(name=tpl.name, category=tpl.category, count=counts[i])
        for i, tpl in enumerate(bank.sources)
    ]

    # Stream samples — pick 14 templates without replacement (or with, if pool small).
    sample_pool = list(bank.signal_templates)
    if len(sample_pool) >= 14:
        chosen = rng.sample(sample_pool, 14)
    else:
        chosen = sample_pool + rng.choices(sample_pool, k=14 - len(sample_pool))
    rng.shuffle(chosen)
    stream_samples = [
        StreamSample(
            source=rng.choice(t.source_pool),
            sentiment=t.sentiment,
            text=t.text.replace("{company}", name),
            is_simulated=False,
        )
        for t in chosen
    ]

    # Clusters
    cluster_titles = list(bank.cluster_templates)
    rng.shuffle(cluster_titles)
    n_clusters = rng.randint(5, min(7, len(cluster_titles)))
    cluster_titles = cluster_titles[:n_clusters]

    # Top epic — pick a template, jitter RICE, render strings.
    top_epic_tpl = rng.choice(bank.top_epic_templates)
    rice = _pick_top_rice(top_epic_tpl.rice, rng)
    top_epic = TopEpic(
        title=top_epic_tpl.title_template.replace("{company}", name),
        rationale=top_epic_tpl.rationale_template.replace("{company}", name),
        verdict=top_epic_tpl.verdict,
        recommendation=top_epic_tpl.recommendation.replace("{company}", name),
        rice=rice,
        acceptance_criteria=[ac.replace("{company}", name) for ac in top_epic_tpl.acceptance_criteria],
        evidence=[
            Evidence(
                quote=ev.quote.replace("{company}", name),
                source=ev.source_template.replace("{company}", name).replace("{company_l}", slug),
            )
            for ev in top_epic_tpl.evidence_templates
        ],
    )

    # The top cluster takes the recommended epic's title and score; the rest get
    # decreasing rice-scores so the visualization has a clear gradient.
    cluster_models = [
        Cluster(
            title=top_epic.title.replace(f"{name} ", "").replace(f"Stabilize {name}", "Stabilize"),
            signal_count=int(signal_count * rng.uniform(0.04, 0.07)),
            rice_score=rice.composite,
            is_top=True,
        )
    ]
    remaining_score = rice.composite - 6
    for title in cluster_titles[1:] if len(cluster_titles) > 1 else cluster_titles:
        cluster_models.append(Cluster(
            title=title.replace("{company}", name),
            signal_count=int(signal_count * rng.uniform(0.012, 0.04)),
            rice_score=round(max(35.0, remaining_score), 1),
            is_top=False,
        ))
        remaining_score -= rng.uniform(5.0, 9.5)

    # Sync — Jira project key + ID + Confluence space deterministically chosen.
    project_key = rng.choice(bank.jira_keys)
    ticket_num = rng.randint(1100, 5400)
    jira_id = f"{project_key}-{ticket_num}"
    sync = Sync(
        jira=JiraTicket(
            id=jira_id,
            project=bank.industry_label,
            type="Epic",
            story_points=rng.choice([13, 16, 18, 21, 24, 26]),
            status="Created",
        ),
        confluence=ConfluenceDoc(
            space=project_key,
            title=f"PRD · {top_epic.title}",
            linked_jira=jira_id,
            status="Draft published",
        ),
    )

    company = Company(
        slug=slug,
        name=name,
        domain=domain,
        industry=bank.industry_label,
        tagline=rng.choice(bank.tagline_options),
        mark=mark,
        tier="synth",
    )

    return RunResponse(
        company=company,
        ingest=Ingest(
            signal_count=signal_count,
            runtime_seconds=runtime_seconds,
            sentiment_pct=sentiment_pct,
            sources=sources,
            stream_samples=stream_samples,
        ),
        clusters=cluster_models,
        top_epic=top_epic,
        sync=sync,
        meta=Meta(
            generated_at=datetime(2026, 4, 26, 12, 34, 56, tzinfo=timezone.utc),
            generator="synth",
            seed=domain,
        ),
    )
