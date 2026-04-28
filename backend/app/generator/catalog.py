"""In-memory catalog of pre-authored company runs.

Loads every ``app/data/companies/*.json`` once at import and validates each
against the canonical ``RunResponse`` schema. Lookup is O(1) by slug or by
registered domain.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from ..models import CatalogTile, RunResponse

log = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "companies"

_BY_SLUG: dict[str, RunResponse] = {}
_BY_DOMAIN: dict[str, str] = {}


def _load() -> None:
    if _BY_SLUG:
        return
    if not _DATA_DIR.exists():
        log.warning("catalog data dir missing at %s", _DATA_DIR)
        return
    loaded = 0
    for path in sorted(_DATA_DIR.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            run = RunResponse.model_validate(payload)
        except Exception as exc:
            log.error("catalog load failed for %s: %s", path.name, exc)
            raise
        slug = run.company.slug
        if slug in _BY_SLUG:
            raise RuntimeError(f"duplicate catalog slug: {slug}")
        _BY_SLUG[slug] = run
        _BY_DOMAIN[run.company.domain.lower()] = slug
        loaded += 1
    log.info("catalog loaded: %d companies", loaded)


def lookup(slug_or_domain: str) -> RunResponse | None:
    """Resolve a slug or registered domain to a catalog run, if present."""
    _load()
    key = slug_or_domain.lower()
    if key in _BY_SLUG:
        return _BY_SLUG[key]
    domain_slug = _BY_DOMAIN.get(key)
    if domain_slug:
        return _BY_SLUG.get(domain_slug)
    return None


def tiles() -> list[CatalogTile]:
    """Picker-grid projection of the full catalog."""
    _load()
    return [
        CatalogTile(
            slug=run.company.slug,
            name=run.company.name,
            domain=run.company.domain,
            industry=run.company.industry,
            tagline=run.company.tagline,
            mark=run.company.mark,
            top_epic_preview=run.top_epic.title,
            top_score_preview=run.top_epic.rice.composite,
        )
        for run in _BY_SLUG.values()
    ]


def size() -> int:
    _load()
    return len(_BY_SLUG)
