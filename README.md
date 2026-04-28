# OmniHub

OmniHub is the **AI-native Decision OS for product teams** — an intelligence layer that turns scattered customer signals into ranked, explainable product decisions. This repo is the **investor-pitch prototype**: a single, polished artifact that demonstrates the end-to-end pipeline in under 90 seconds, with zero external API calls and zero credentials.

## What's here

```
omnihub/
├── backend/        # Python FastAPI service — generates the run payload (this folder is complete)
└── frontend/       # React + Vite + Tailwind + Framer Motion — animated 5-stage demo (planned)
```

`backend/` is the canonical source for the run-object schema. `frontend/` reads it over HTTP and animates the pipeline.

## Two-command quickstart

```bash
# Terminal 1 — backend
cd backend
py -m venv .venv && source .venv/Scripts/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload

# Terminal 2 — frontend (when built)
cd frontend
npm install
npm run dev
```

Then open the frontend URL (`http://localhost:5173`) and paste any company URL.

## The five-stage pipeline

1. **Ingest** — pulls signals from external (X/Twitter, Reddit, App Store, Hacker News) and internal (Zendesk, Intercom, Slack, Jira, Datadog) channels into one stream.
2. **Cluster** — groups thousands of noisy signals into 5–7 coherent themes ("3DS auth failures on Safari" rather than 2,140 individual complaints).
3. **Score** — runs the top theme through a **RICE++** model (Reach, Impact, Confidence, Effort, plus Urgency, Strategy, Risk) and produces a 0–99.9 priority composite.
4. **Recommend** — surfaces the top epic with rationale, evidence quotes, and 4 acceptance criteria.
5. **Sync** — drops the recommendation into a Jira epic and a Confluence PRD draft (synthesized in this prototype).

## Hard constraints (prototype scope)

- No external APIs, no LLM calls, no web scraping.
- No credentials — runs cold on a fresh machine.
- No internet at runtime — works on a plane, on hotel WiFi, in a conference room with bad signal.
- Deterministic per domain — same input gives the same output, every time.

The backend covers all 25 hand-authored catalog companies (Stripe, Shopify, Notion, Airbnb, GitHub, Figma, Linear, Vercel, OpenAI, Anthropic, Slack, Canva, Duolingo, Spotify, DoorDash, Uber, Coinbase, Robinhood, Netflix, Discord, Zoom, Dropbox, Atlassian, HubSpot, Calendly) and a deterministic synthetic generator for any other domain.

## Where to read next

- [`backend/README.md`](backend/README.md) — API surface, deployment, layout.
- `backend/app/models.py` — the canonical run-object schema.
- `backend/app/data/companies/stripe.json` — the gold-standard reference example.
