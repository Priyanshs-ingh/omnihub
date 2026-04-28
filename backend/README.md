# OmniHub Backend

FastAPI service that powers the OmniHub investor-pitch prototype. It returns synthetic-but-believable product-intelligence runs for any company domain, in the canonical shape consumed by the frontend.

This service has **zero external dependencies at runtime** — no LLMs, no scraping, no third-party APIs, no database, no credentials of any kind. Output is deterministic per domain: same input in, byte-identical output out, every time.

## Quickstart (Windows / Git Bash)

```bash
cd e:/omnihub/backend
py -m venv .venv
source .venv/Scripts/activate         # PowerShell:  .\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

Then visit:

- <http://localhost:8000/api/health>
- <http://localhost:8000/api/catalog>
- <http://localhost:8000/api/run?domain=stripe.com>
- <http://localhost:8000/api/run?domain=cal.com> (synthetic fallback)
- <http://localhost:8000/api/run/stream?domain=stripe.com> (Server-Sent Events, ~22s)

## API surface

| Method | Path | Purpose |
| --- | --- | --- |
| `GET`  | `/api/health` | Liveness check. Returns `{"status":"ok","version":"…"}`. |
| `GET`  | `/api/catalog` | All 25 pre-built company tiles for the picker grid. |
| `GET`  | `/api/run?domain=...` | Full canonical run payload — catalog hit if the domain is in the catalog, deterministic synthetic run otherwise. |
| `GET`  | `/api/run/stream?domain=...` | Same payload as a 7-event SSE stream paced over ~22s, matching the frontend animation budget. |

Domain input is forgiving: `stripe.com`, `https://www.stripe.com/atlas`, `STRIPE`, and `  stripe  ` all resolve to the same run.

### Errors

Every error response uses the same shape:

```json
{ "error": "Could not parse company from input: '/'", "code": "invalid_domain", "hint": "Try a domain like example.com" }
```

| Status | When |
| --- | --- |
| 400 | Domain input cannot be parsed (`invalid_domain`). |
| 422 | Standard FastAPI validation error (e.g. missing `domain` query param). |

## How it works

Three resolution tiers run in order:

1. **Catalog** (`app/data/companies/*.json`) — 25 pre-authored, hand-tuned company runs. Stripe, Shopify, Notion, Airbnb, GitHub, Figma, Linear, Vercel, OpenAI, Anthropic, Slack, Canva, Duolingo, Spotify, DoorDash, Uber, Coinbase, Robinhood, Netflix, Discord, Zoom, Dropbox, Atlassian, HubSpot, Calendly. Loaded into memory at import.
2. **Synth** (`app/generator/synth.py`) — for any other domain, an industry-keyed template engine generates a plausible run. Seeded from `md5(domain)` so output is deterministic across processes.
3. **Reject** — input that cannot be parsed at all surfaces a 400 with a friendly hint.

The RICE++ scoring lives in `app/generator/rice.py`. It is real math on synthetic inputs; you can read it to verify the formula.

## Tests

```bash
pytest
```

Covers: route shapes for all 25 catalog slugs, synth determinism, SSE content-type, RICE++ formula, industry classifier heuristics, input normalization. ~50 tests, runs in ~25 seconds (the SSE stream test contributes most of the wall time).

## Production

### Docker

```bash
docker build -t omnihub-backend .
docker run -p 8000:8000 -e FRONTEND_ORIGINS=https://yourapp.vercel.app omnihub-backend
```

### Render

`render.yaml` is committed. Push to a Git remote, click "Deploy from Blueprint" in Render, set `FRONTEND_ORIGINS` in the dashboard.

### Railway

`railway.toml` is committed. `railway up` deploys it.

### Generic ASGI host

```bash
gunicorn app.main:app -w 2 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT
```

## Configuration

| Env var | Default | Purpose |
| --- | --- | --- |
| `FRONTEND_ORIGINS` | `http://localhost:5173,http://localhost:4173,http://127.0.0.1:5173` | Comma-separated list of CORS origins for the frontend. |
| `PORT` | `8000` (Docker) | Server bind port (set by Render/Railway/Fly automatically). |

Copy `.env.example` to `.env` for local overrides.

## Layout

```
backend/
├── pyproject.toml
├── Dockerfile, render.yaml, railway.toml
├── app/
│   ├── main.py                    # FastAPI app, CORS, exception handlers, lifespan
│   ├── config.py                  # Pydantic settings
│   ├── models.py                  # Canonical run-payload schema
│   ├── routes/
│   │   ├── run.py                 # /api/run + /api/run/stream
│   │   └── catalog.py             # /api/catalog
│   ├── generator/
│   │   ├── catalog.py             # JSON loader, O(1) lookup by slug or domain
│   │   ├── industry_map.py        # Domain → industry classifier
│   │   ├── synth.py               # Tier-2 deterministic generator
│   │   ├── templates.py           # Typed accessor over industry_phrases.json
│   │   ├── resolver.py            # tldextract + slugify normalization
│   │   └── rice.py                # RICE++ composite scoring
│   └── data/
│       ├── companies/*.json       # 25 catalog companies
│       └── industry_phrases.json  # Per-industry signal/cluster/epic templates
└── tests/
    ├── test_routes.py
    ├── test_generator.py
    └── test_synth.py
```

## What this isn't

Per the prototype scope (see top-level `README.md`):

- No real LLM calls, no web scraping, no third-party APIs at runtime.
- No database — state lives in JSON files and in-memory dicts.
- No auth, no rate limiting, no analytics. Single-tenant, anonymous, internal demo.
- No tests beyond smoke + invariant coverage. We optimize for demo polish, not coverage %.

These are deliberate constraints; lift them when graduating to MVP.
