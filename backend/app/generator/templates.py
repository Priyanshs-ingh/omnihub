"""Typed accessor over ``app/data/industry_phrases.json``."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from .industry_map import Industry

_PATH = Path(__file__).resolve().parent.parent / "data" / "industry_phrases.json"


@dataclass(frozen=True)
class SourceTemplate:
    name: str
    category: str   # "external" | "internal"
    weight: float


@dataclass(frozen=True)
class SignalTemplate:
    sentiment: str  # "positive" | "neutral" | "negative"
    text: str
    source_pool: tuple[str, ...]


@dataclass(frozen=True)
class EvidenceTemplate:
    quote: str
    source_template: str


@dataclass(frozen=True)
class TopEpicTemplate:
    title_template: str
    rationale_template: str
    verdict: str
    recommendation: str
    rice: dict[str, int]
    acceptance_criteria: tuple[str, ...]
    evidence_templates: tuple[EvidenceTemplate, ...]


@dataclass(frozen=True)
class IndustryBank:
    industry_label: str
    tagline_options: tuple[str, ...]
    mark_palette: tuple[str, ...]
    jira_keys: tuple[str, ...]
    sources: tuple[SourceTemplate, ...]
    signal_templates: tuple[SignalTemplate, ...]
    cluster_templates: tuple[str, ...]
    top_epic_templates: tuple[TopEpicTemplate, ...]


@lru_cache(maxsize=1)
def _load_raw() -> dict[str, dict]:
    return json.loads(_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=None)
def get(industry: Industry) -> IndustryBank:
    raw = _load_raw()[industry]
    return IndustryBank(
        industry_label=raw["industry_label"],
        tagline_options=tuple(raw["tagline_options"]),
        mark_palette=tuple(raw["mark_palette"]),
        jira_keys=tuple(raw["jira_keys"]),
        sources=tuple(
            SourceTemplate(name=s["name"], category=s["category"], weight=s["weight"])
            for s in raw["sources"]
        ),
        signal_templates=tuple(
            SignalTemplate(
                sentiment=s["sentiment"],
                text=s["text"],
                source_pool=tuple(s["source_pool"]),
            )
            for s in raw["signal_templates"]
        ),
        cluster_templates=tuple(raw["cluster_templates"]),
        top_epic_templates=tuple(
            TopEpicTemplate(
                title_template=t["title_template"],
                rationale_template=t["rationale_template"],
                verdict=t["verdict"],
                recommendation=t["recommendation"],
                rice=dict(t["rice"]),
                acceptance_criteria=tuple(t["acceptance_criteria"]),
                evidence_templates=tuple(
                    EvidenceTemplate(quote=e["quote"], source_template=e["source_template"])
                    for e in t["evidence_templates"]
                ),
            )
            for t in raw["top_epic_templates"]
        ),
    )
