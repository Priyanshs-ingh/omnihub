from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import AsyncIterator

from fastapi import APIRouter, Query
from sse_starlette.sse import EventSourceResponse

from ..generator import catalog, synth
from ..generator.resolver import normalize
from ..models import RunResponse

router = APIRouter(tags=["run"])
log = logging.getLogger(__name__)


def _resolve(domain: str) -> RunResponse:
    """Normalize input → catalog hit → synth fallback. May raise InvalidDomainError."""
    n = normalize(domain)
    catalog_hit = catalog.lookup(n.slug) or catalog.lookup(n.domain)
    if catalog_hit is not None:
        return catalog_hit
    return synth.synthesize(n.slug, n.domain)


@router.get("/run", response_model=RunResponse)
def get_run(domain: str = Query(..., min_length=1)) -> RunResponse:
    started = time.perf_counter()
    run = _resolve(domain)
    log.info(
        "run resolved: tier=%s slug=%s domain=%s ms=%.1f",
        run.company.tier,
        run.company.slug,
        run.company.domain,
        (time.perf_counter() - started) * 1000,
    )
    return run


# Spec section 4.3 / 5.4: stream pacing matches the frontend animation budget.
_STAGE_DELAYS_S: list[tuple[str, float]] = [
    ("company",   0.0),
    ("ingest",    0.5),
    ("cluster",   6.0),
    ("score",     5.0),
    ("recommend", 4.0),
    ("sync",      4.0),
    ("done",      2.5),
]


def _stage_payload(run: RunResponse, event: str) -> dict | list:
    if event == "company":
        return run.company.model_dump(mode="json")
    if event == "ingest":
        return run.ingest.model_dump(mode="json")
    if event == "cluster":
        return [c.model_dump(mode="json") for c in run.clusters]
    if event == "score":
        return run.top_epic.rice.model_dump(mode="json")
    if event == "recommend":
        return run.top_epic.model_dump(mode="json")
    if event == "sync":
        return run.sync.model_dump(mode="json")
    if event == "done":
        return run.meta.model_dump(mode="json")
    raise ValueError(event)


@router.get("/run/stream")
async def stream_run(domain: str = Query(..., min_length=1)) -> EventSourceResponse:
    """Server-Sent Events stream — 7 stage events over ~22 seconds total."""
    run = _resolve(domain)

    async def gen() -> AsyncIterator[dict]:
        for event, delay in _STAGE_DELAYS_S:
            if delay:
                await asyncio.sleep(delay)
            # sse-starlette stringifies whatever's in `data`; pass a JSON
            # string explicitly so the browser EventSource can JSON.parse it.
            yield {"event": event, "data": json.dumps(_stage_payload(run, event))}

    log.info("stream start: tier=%s slug=%s", run.company.tier, run.company.slug)
    return EventSourceResponse(gen())
