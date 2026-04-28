from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .generator.resolver import InvalidDomainError
from .models import ErrorResponse
from .routes import catalog as catalog_route
from .routes import run as run_route

logging.basicConfig(
    level=logging.INFO,
    format='{"ts":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","msg":"%(message)s"}',
)
log = logging.getLogger("omnihub")


@asynccontextmanager
async def _lifespan(_: FastAPI) -> AsyncIterator[None]:
    log.info(
        "omnihub backend %s up; allowed origins=%s",
        settings.app_version,
        settings.frontend_origins,
    )
    yield


# TODO(MVP): add auth + rate limiting before exposing this beyond the demo founder.
app = FastAPI(
    title="OmniHub Backend",
    version=settings.app_version,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    lifespan=_lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origins,
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": settings.app_version}


# Register API routers BEFORE the static mount so /api/* always wins over the
# catch-all StaticFiles handler.
app.include_router(run_route.router, prefix="/api")
app.include_router(catalog_route.router, prefix="/api")


# Mount the static demo at the root: `http://localhost:8000/` serves the demo,
# `/api/*` serves the JSON API, all on the same origin (no CORS, no redirect).
_DEMO_DIR = Path(__file__).resolve().parent.parent / "demo_frontend"
if _DEMO_DIR.exists():
    app.mount("/", StaticFiles(directory=_DEMO_DIR, html=True), name="demo")


@app.exception_handler(InvalidDomainError)
async def _on_invalid_domain(request: Request, exc: InvalidDomainError) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content=ErrorResponse(
            error=str(exc) or "Could not parse company from input",
            code="invalid_domain",
            hint="Try a domain like example.com",
        ).model_dump(),
    )
