"""Heuristic industry classifier for the synth fallback.

Resolution order (first hit wins):

    1. Known-domain table (~150 entries) — highest signal.
    2. Strong-TLD rules (.shop, .ai, .dev, .io fintech subtlety etc.).
    3. Slug-keyword rules — substrings like "pay" → fintech.
    4. Default to "saas".
"""

from __future__ import annotations

from typing import Literal

Industry = Literal[
    "fintech",
    "commerce",
    "developer",
    "design",
    "ai",
    "productivity",
    "marketplace",
    "consumer",
    "healthtech",
    "edtech",
    "saas",
]


# ---------------------------------------------------------------------------
# Known domains (catalog-adjacent — enough to make any random YC URL plausible)
# ---------------------------------------------------------------------------

_KNOWN_DOMAINS: dict[str, Industry] = {
    # fintech
    "venmo.com": "fintech", "wise.com": "fintech", "plaid.com": "fintech",
    "ramp.com": "fintech", "brex.com": "fintech", "mercury.com": "fintech",
    "klarna.com": "fintech", "affirm.com": "fintech", "square.com": "fintech",
    "block.xyz": "fintech", "revolut.com": "fintech", "monzo.com": "fintech",
    "chime.com": "fintech", "kraken.com": "fintech", "binance.com": "fintech",
    "circle.com": "fintech", "paypal.com": "fintech",

    # commerce
    "etsy.com": "commerce", "amazon.com": "commerce", "ebay.com": "commerce",
    "wayfair.com": "commerce", "wish.com": "commerce", "alibaba.com": "commerce",
    "target.com": "commerce", "walmart.com": "commerce", "bigcommerce.com": "commerce",
    "wix.com": "commerce", "squarespace.com": "commerce", "shopify.com": "commerce",

    # developer / infra
    "webflow.com": "developer", "supabase.com": "developer", "render.com": "developer",
    "fly.io": "developer", "railway.app": "developer", "netlify.com": "developer",
    "cloudflare.com": "developer", "datadog.com": "developer", "sentry.io": "developer",
    "retool.com": "developer", "heroku.com": "developer", "circleci.com": "developer",
    "gitlab.com": "developer", "bitbucket.org": "developer", "warp.dev": "developer",
    "cursor.com": "developer", "stackblitz.com": "developer", "codesandbox.io": "developer",
    "posthog.com": "developer", "huggingface.co": "developer",

    # design
    "framer.com": "design", "sketch.com": "design", "miro.com": "design",
    "invisionapp.com": "design", "adobe.com": "design", "abstract.com": "design",
    "zeplin.io": "design",

    # ai
    "perplexity.ai": "ai", "midjourney.com": "ai", "runwayml.com": "ai",
    "stability.ai": "ai", "elevenlabs.io": "ai", "cohere.com": "ai",
    "groq.com": "ai", "mistral.ai": "ai", "x.ai": "ai", "deepmind.com": "ai",

    # productivity
    "asana.com": "productivity", "trello.com": "productivity", "monday.com": "productivity",
    "clickup.com": "productivity", "evernote.com": "productivity", "todoist.com": "productivity",
    "loom.com": "productivity", "obsidian.md": "productivity", "coda.io": "productivity",
    "airtable.com": "productivity", "fathom.video": "productivity",

    # marketplace
    "instacart.com": "marketplace", "lyft.com": "marketplace", "grubhub.com": "marketplace",
    "ubereats.com": "marketplace", "fiverr.com": "marketplace", "upwork.com": "marketplace",
    "tripadvisor.com": "marketplace", "vrbo.com": "marketplace", "booking.com": "marketplace",
    "expedia.com": "marketplace", "kayak.com": "marketplace", "thumbtack.com": "marketplace",

    # consumer
    "tiktok.com": "consumer", "instagram.com": "consumer", "snap.com": "consumer",
    "pinterest.com": "consumer", "twitch.tv": "consumer", "reddit.com": "consumer",
    "youtube.com": "consumer", "x.com": "consumer", "twitter.com": "consumer",
    "hbo.com": "consumer", "max.com": "consumer", "hulu.com": "consumer",
    "primevideo.com": "consumer",

    # healthtech
    "onemedical.com": "healthtech", "teladoc.com": "healthtech", "ro.co": "healthtech",
    "hims.com": "healthtech", "tempus.com": "healthtech", "oscar.com": "healthtech",
    "headspace.com": "healthtech", "calm.com": "healthtech",

    # edtech
    "coursera.org": "edtech", "udemy.com": "edtech", "khanacademy.org": "edtech",
    "brilliant.org": "edtech", "skillshare.com": "edtech", "edx.org": "edtech",
    "quizlet.com": "edtech", "chegg.com": "edtech",

    # saas
    "salesforce.com": "saas", "intercom.com": "saas", "zendesk.com": "saas",
    "front.com": "saas", "mailchimp.com": "saas", "klaviyo.com": "saas",
    "segment.com": "saas", "amplitude.com": "saas", "mixpanel.com": "saas",
    "twilio.com": "saas", "okta.com": "saas", "auth0.com": "saas",
    "cal.com": "saas", "linear.app": "developer",
}


# ---------------------------------------------------------------------------
# TLD-based rules (strong signals)
# ---------------------------------------------------------------------------

_TLD_RULES: dict[str, Industry] = {
    "shop": "commerce",
    "store": "commerce",
    "ai": "ai",
    "dev": "developer",
}


# ---------------------------------------------------------------------------
# Slug-keyword rules (ordered; first match wins)
# ---------------------------------------------------------------------------

_KEYWORD_RULES: list[tuple[tuple[str, ...], Industry]] = [
    (("ai", "gpt", "ml", "neural", "llm", "intel", "agentic"),                  "ai"),
    (("pay", "bank", "coin", "wallet", "credit", "fin", "invest", "trade"),     "fintech"),
    (("shop", "store", "cart", "buy", "commerce", "retail", "checkout"),        "commerce"),
    (("design", "studio", "brand", "ux", "ui", "figma", "canvas"),              "design"),
    (("dev", "code", "build", "deploy", "infra", "stack", "ops", "lab", "ci"),  "developer"),
    (("doc", "note", "wiki", "task", "todo", "project", "team"),                "productivity"),
    (("market", "place", "ride", "stay", "food", "deliver", "hire"),            "marketplace"),
    (("stream", "music", "video", "watch", "social", "chat", "feed"),           "consumer"),
    (("health", "med", "care", "wellness", "fit", "clinic", "rx"),              "healthtech"),
    (("learn", "edu", "school", "class", "course", "study", "tutor"),           "edtech"),
]


def classify(slug: str, domain: str) -> Industry:
    """Best-effort industry from (slug, domain). Never raises; falls back to 'saas'."""
    domain_l = domain.lower()
    if domain_l in _KNOWN_DOMAINS:
        return _KNOWN_DOMAINS[domain_l]

    parts = domain_l.split(".")
    tld = parts[-1] if len(parts) >= 2 else ""
    if tld in _TLD_RULES:
        return _TLD_RULES[tld]

    slug_l = slug.lower()
    for keywords, industry in _KEYWORD_RULES:
        if any(kw in slug_l for kw in keywords):
            return industry

    return "saas"
