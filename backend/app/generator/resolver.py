"""Domain normalization shared by catalog lookup, synth, and SSE handler."""

from __future__ import annotations

from dataclasses import dataclass

import tldextract
from slugify import slugify

# Don't fetch the public-suffix list at runtime — bake it into the package via
# the bundled snapshot. This keeps the demo runnable on a plane.
_extract = tldextract.TLDExtract(suffix_list_urls=(), fallback_to_snapshot=True)


class InvalidDomainError(ValueError):
    """Raised when input cannot be parsed into a registered domain."""


@dataclass(frozen=True)
class NormalizedDomain:
    slug: str           # e.g. "stripe"
    domain: str         # e.g. "stripe.com"
    raw: str            # original user input


def normalize(raw: str) -> NormalizedDomain:
    """Turn arbitrary user input into a canonical (slug, domain) pair.

    Accepts: ``stripe.com``, ``https://www.stripe.com/atlas``, ``STRIPE``,
    ``stripe``. Rejects empty input or anything tldextract can't parse.
    """
    if raw is None:
        raise InvalidDomainError("Domain is required")
    cleaned = raw.strip().lower()
    if not cleaned:
        raise InvalidDomainError("Domain is required")

    extracted = _extract(cleaned)

    # Bare-name input (e.g. "stripe", "STRIPE") — tldextract returns no domain;
    # fall back to slugifying the raw input and assume `.com` for the canonical
    # domain. This is the demo-friendly behavior the spec calls for.
    if not extracted.domain:
        slug = slugify(cleaned)
        if not slug:
            raise InvalidDomainError(f"Could not parse company from input: {raw!r}")
        return NormalizedDomain(slug=slug, domain=f"{slug}.com", raw=raw)

    slug = slugify(extracted.domain)
    if not slug:
        raise InvalidDomainError(f"Could not parse company from input: {raw!r}")

    if extracted.suffix:
        domain = f"{extracted.domain}.{extracted.suffix}"
    else:
        # No public suffix on the input — happens for things like "stripe" alone
        # after odd cleanup; default to .com so the rest of the pipeline has
        # something stable to key on.
        domain = f"{extracted.domain}.com"

    return NormalizedDomain(slug=slug, domain=domain, raw=raw)
