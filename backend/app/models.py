"""Canonical OmniHub run-payload schema.

These models are the immutable contract between backend and frontend. The shape
mirrors spec section 4.3 exactly. Catalog JSONs and the synth generator both
produce instances that round-trip through these models.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


SourceCategory = Literal["external", "internal"]
Sentiment = Literal["positive", "neutral", "negative"]
Tier = Literal["catalog", "synth"]


class CompanyMark(_Strict):
    bg: str = Field(..., description="Hex color string, e.g. '#635BFF'.")
    char: str = Field(..., min_length=1, max_length=2)


class Company(_Strict):
    slug: str
    name: str
    domain: str
    industry: str
    tagline: str
    mark: CompanyMark
    tier: Tier


class Source(_Strict):
    name: str
    category: SourceCategory
    count: int = Field(..., ge=0)


class StreamSample(_Strict):
    source: str
    sentiment: Sentiment
    text: str
    is_simulated: bool = False


class SentimentPct(_Strict):
    positive: int = Field(..., ge=0, le=100)
    neutral: int = Field(..., ge=0, le=100)
    negative: int = Field(..., ge=0, le=100)


class Ingest(_Strict):
    signal_count: int = Field(..., ge=0)
    runtime_seconds: int = Field(..., ge=0)
    sentiment_pct: SentimentPct
    sources: list[Source]
    stream_samples: list[StreamSample]


class Cluster(_Strict):
    title: str
    signal_count: int = Field(..., ge=0)
    rice_score: float = Field(..., ge=0, le=100)
    is_top: bool = False


class Rice(_Strict):
    reach: int = Field(..., ge=0, le=100)
    impact: int = Field(..., ge=0, le=100)
    confidence: int = Field(..., ge=0, le=100)
    effort: int = Field(..., ge=0, le=100)
    urgency: int = Field(..., ge=0, le=100)
    strategy: int = Field(..., ge=0, le=100)
    risk_inv: int = Field(..., ge=0, le=100)
    composite: float = Field(..., ge=0, le=100)


class Evidence(_Strict):
    quote: str
    source: str


class TopEpic(_Strict):
    title: str
    rationale: str
    verdict: str
    recommendation: str
    rice: Rice
    acceptance_criteria: list[str]
    evidence: list[Evidence]


class JiraTicket(_Strict):
    id: str
    project: str
    type: str = "Epic"
    story_points: int = Field(..., ge=0)
    status: str = "Created"


class ConfluenceDoc(_Strict):
    space: str
    title: str
    linked_jira: str
    status: str = "Draft published"


class Sync(_Strict):
    jira: JiraTicket
    confluence: ConfluenceDoc


class Meta(_Strict):
    generated_at: datetime
    generator: Tier
    seed: str


class RunResponse(_Strict):
    company: Company
    ingest: Ingest
    clusters: list[Cluster]
    top_epic: TopEpic
    sync: Sync
    meta: Meta


class CatalogTile(_Strict):
    slug: str
    name: str
    domain: str
    industry: str
    tagline: str
    mark: CompanyMark
    top_epic_preview: str
    top_score_preview: float = Field(..., ge=0, le=100)


class CatalogResponse(_Strict):
    companies: list[CatalogTile]


class ErrorResponse(_Strict):
    error: str
    code: str
    hint: str | None = None
