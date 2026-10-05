<div align="center">

# CANDAS AI

**Campaign Automation and Networked Design Agent System**

An agentic, human-in-the-loop platform that turns a campaign brief into platform-ready posts, generated images, schedules, and published content.

![Python](https://img.shields.io/badge/Python-3.12-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688)
![React](https://img.shields.io/badge/React-18-61DAFB)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-pgvector-336791)
![Celery](https://img.shields.io/badge/Celery-Workers-37814A)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED)
![Telegram](https://img.shields.io/badge/Publishing-Telegram-26A5E4)
![License](https://img.shields.io/badge/License-MIT-yellow)

</div>

> [!NOTE]
> This repository contains a working agentic marketing automation system with a React frontend, a FastAPI backend, LangGraph-based orchestration, PostgreSQL persistence, Redis-backed background workers, MinIO-compatible media storage, and Telegram publishing. Other social platform adapters exist in the codebase, but only Telegram is implemented as a real publishing integration. Several other adapters are scaffolded or mock-oriented future extensions.

## Table of Contents

- [1. Project Overview](#1-project-overview)
- [2. Key Features](#2-key-features)
- [3. System Architecture](#3-system-architecture)
- [4. Agentic Workflow](#4-agentic-workflow)
- [5. Technology Stack](#5-technology-stack)
- [6. Project Structure](#6-project-structure)
- [7. Prerequisites](#7-prerequisites)
- [8. Environment Variables](#8-environment-variables)
- [9. Installation and Setup](#9-installation-and-setup)
- [10. Running the System with Docker Compose](#10-running-the-system-with-docker-compose)
- [11. Running Frontend and Backend Separately](#11-running-frontend-and-backend-separately)
- [12. Using the Application](#12-using-the-application)
- [13. Demo Flow](#13-demo-flow)
- [14. API Documentation](#14-api-documentation)
- [15. Background Workers and Scheduling](#15-background-workers-and-scheduling)
- [16. Media Storage and Telegram Publishing](#16-media-storage-and-telegram-publishing)
- [17. Testing](#17-testing)
- [18. Troubleshooting](#18-troubleshooting)
- [19. Current Limitations](#19-current-limitations)
- [20. Future Work](#20-future-work)
- [21. Authors](#21-authors)
- [22. License](#22-license)

## 1. Project Overview

CANDAS AI is an agentic campaign automation system that accepts a campaign brief, generates platform-specific post drafts, produces or falls back to generated media, stores campaign data, routes drafts through human approval, schedules posts, and publishes approved content.

The implemented system combines:

- A React + Vite frontend in [`frontend/`](./frontend)
- A FastAPI backend in [`app/main.py`](./app/main.py)
- A LangGraph workflow in [`app/agents/`](./app/agents)
- Celery workers and Celery Beat in [`app/workers/`](./app/workers)
- PostgreSQL with pgvector-backed schema migrations in [`alembic/`](./alembic)
- Redis for rate limiting, pub/sub event streaming, and Celery broker/backend
- S3-compatible object storage via MinIO for generated campaign images
- Telegram publishing through [`app/platforms/telegram.py`](./app/platforms/telegram.py)
- Ollama for text generation through [`app/agents/tools/llm_tool.py`](./app/agents/tools/llm_tool.py)

## 2. Key Features

- Multi-stage agentic workflow for campaign generation and publishing
- Human-in-the-loop approval before scheduling and publication
- Role-based access control with `viewer`, `editor`, `approver`, and `admin`
- Local JWT issuance for development via `/v1/auth/local-token`
- Optional OIDC-ready token verification paths for Auth0 and Keycloak
- Server-Sent Events stream for live workflow progress
- Image generation with S3/MinIO upload and placeholder fallback
- Background scheduling and publication with Celery and Celery Beat
- Campaign analytics persistence and refresh endpoints
- Swagger UI and ReDoc exposed by FastAPI
- Webhook ingestion with HMAC signature verification
- GDPR-style user data deletion endpoint for admins

## 3. System Architecture

```mermaid
flowchart LR
    U[User] --> FE[React + Vite Frontend]
    FE --> API[FastAPI API]
    API --> PG[(PostgreSQL + pgvector)]
    API --> R[(Redis)]
    API --> M[(MinIO / S3-compatible Storage)]
    API --> O[Ollama]
    API --> CW[Celery Worker]
    API --> CB[Celery Beat]
    CW --> PG
    CW --> R
    CW --> M
    CW --> O
    CW --> TG[Telegram Bot API]
    CB --> CW
    API --> SSE[Server-Sent Events]
    SSE --> FE
```

### Implemented backend architecture

| Layer | Verified implementation |
| --- | --- |
| Frontend | React 18 + TypeScript + Vite in `frontend/` |
| Backend | FastAPI application factory in `app/main.py` |
| Database | PostgreSQL via SQLAlchemy async engine |
| Queue and cache | Redis for Celery, rate limiting, and SSE pub/sub |
| Workflow engine | LangGraph state graph |
| Workers | Celery worker and Celery Beat |
| Text generation | Ollama HTTP API |
| Image storage | MinIO/S3-compatible object storage via `boto3` |
| Real publishing target | Telegram |

## 4. Agentic Workflow

The main workflow is defined in [`app/agents/graph.py`](./app/agents/graph.py). The graph composes these stages:

1. `memory`
2. `planner`
3. `researcher`
4. `creator`
5. `reflection`
6. `approval`
7. `scheduler`
8. `publisher`
9. `analyst`

The `reflection` node can loop back to `creator` if the aggregate score is below threshold and retry count is below the configured limit. Approval is implemented as a human-interrupt stage in the graph, while the API-driven approval flow is enforced operationally through the approval endpoints and worker tasks.

```mermaid
flowchart TD
    A[Memory Node] --> B[Planner Node]
    B --> C[Researcher Node]
    C --> D[Creator Node]
    D --> E[Reflection Node]
    E -->|score < 0.75 and retries < 2| D
    E -->|otherwise| F[Human Approval]
    F --> G[Scheduler Node]
    G --> H[Publisher Node]
    H --> I[Analyst Node]
    I --> J[End]
```

### Verified stage behavior

| Stage | File | What it does |
| --- | --- | --- |
| Memory | `app/agents/nodes/memory.py` | Loads brand guidelines from Redis and recent campaign memory from PostgreSQL |
| Planner | `app/agents/nodes/planner.py` | Uses Ollama to derive goals and target audience |
| Researcher | `app/agents/nodes/researcher.py` | Builds internal research context from memory and audience data |
| Creator | `app/agents/nodes/creator.py` | Uses Ollama to generate post drafts and image prompts, moderates copy, checks brand compliance, generates images, and stores draft posts |
| Reflection | `app/agents/nodes/reflection.py` | Scores drafts with Ollama-as-judge and loops if quality is low |
| Approval | `app/agents/graph.py`, `app/api/v1/approvals.py` | Waits for human approval and stores approval decisions |
| Scheduler | `app/agents/nodes/scheduler.py` | Suggests draft schedule entries |
| Publisher | `app/agents/nodes/publisher.py`, `app/workers/campaign_tasks.py` | Queues or executes publication tasks |
| Analyst | `app/agents/nodes/analyst.py`, `app/workers/analytics_tasks.py` | Stores memory and fetches per-post analytics |

## 5. Technology Stack

| Area | Technologies confirmed in code |
| --- | --- |
| Frontend | React 18, TypeScript, React Router, Vite |
| Backend | FastAPI, Pydantic v2, Uvicorn |
| ORM and DB | SQLAlchemy async, asyncpg, Alembic, PostgreSQL, pgvector |
| Agents | LangGraph, LangChain Core tools |
| Background processing | Celery, Redis |
| Storage | MinIO/S3-compatible object storage via `boto3` |
| Text LLM | Ollama |
| Image generation | OpenAI Images API or Pollinations, with placeholder fallback |
| Auth | JWT via `python-jose`; local tokens and optional Auth0/Keycloak verification |
| Observability | structlog, OpenTelemetry |
| Moderation and privacy | internal moderation service, Presidio analyzer, PII redaction helpers |
| Testing | pytest, pytest-asyncio, locust |

## 6. Project Structure

```text
.
|-- .github/workflows/        # CI pipeline
|-- app/
|   |-- agents/               # LangGraph state, nodes, and tools
|   |-- api/                  # FastAPI routers and dependencies
|   |-- core/                 # Security, logging, telemetry, exceptions
|   |-- models/               # SQLAlchemy models and enums
|   |-- platforms/            # Platform publishing adapters
|   |-- schemas/              # Pydantic request/response schemas
|   |-- services/             # Business logic and integrations
|   |-- workers/              # Celery app and task modules
|   |-- config.py             # Environment-backed settings
|   |-- database.py           # Async engine and session management
|   `-- main.py               # FastAPI entry point
|-- alembic/                  # Database migrations
|-- frontend/                 # React/Vite frontend
|-- tests/
|   |-- unit/
|   |-- integration/
|   |-- evals/
|   `-- load/
|-- docker-compose.yml
|-- docker-compose.test.yml
|-- Dockerfile
`-- pyproject.toml
```

## 7. Prerequisites

### For Docker-based execution

- Docker
- Docker Compose

### For running services separately

- Python 3.12+
- Node.js 20+
- PostgreSQL 16-compatible database
- Redis 7+
- MinIO or another S3-compatible object store
- Ollama

Optional for real image generation and publishing:

- `OPENAI_API_KEY` for OpenAI image generation
- Telegram bot token and target chat/channel

## 8. Environment Variables

The backend settings are defined in [`app/config.py`](./app/config.py). The repository also includes [`.env.example`](./.env.example).

### Core application variables

| Variable | Purpose |
| --- | --- |
| `APP_NAME` | FastAPI application name |
| `API_VERSION` | API version string |
| `ENVIRONMENT` | `local`, `test`, `staging`, or `production` |
| `DEBUG` | Enables SQLAlchemy echo and debug behavior |
| `CORS_ALLOWED_ORIGINS` | Allowed browser origins |

### Database and Redis

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | SQLAlchemy async PostgreSQL connection string |
| `REDIS_URL` | Redis URL for Celery, rate limiting, and pub/sub |

### Authentication and JWT

| Variable | Purpose |
| --- | --- |
| `AUTH_PROVIDER` | `local`, `auth0`, or `keycloak` |
| `AUTH0_DOMAIN` | Auth0 issuer domain |
| `AUTH0_AUDIENCE` | Auth0 audience |
| `KEYCLOAK_ISSUER` | Keycloak issuer URL |
| `KEYCLOAK_AUDIENCE` | Keycloak audience |
| `JWT_ALGORITHM` | JWT algorithm |
| `JWT_SECRET` | Shared secret for local or HS-based JWT modes |
| `AUTH_DISABLED_FOR_LOCAL_DEV` | Local development bypass switch |

### LLM and media generation

| Variable | Purpose |
| --- | --- |
| `OLLAMA_BASE_URL` | Ollama API base URL |
| `OLLAMA_PRIMARY_MODEL` | Primary text model |
| `OLLAMA_FALLBACK_MODEL` | Fallback text model |
| `OPENAI_API_KEY` | Required for OpenAI image generation |
| `ANTHROPIC_API_KEY` | Present in settings but not currently used in the workflow |
| `RUNWAY_API_KEY` | Present in settings but not currently used in the workflow |
| `IMAGE_PROVIDER` | `placeholder`, `openai`, or `pollinations` |

### Object storage

| Variable | Purpose |
| --- | --- |
| `AWS_ACCESS_KEY_ID` | S3/MinIO access key |
| `AWS_SECRET_ACCESS_KEY` | S3/MinIO secret key |
| `AWS_S3_BUCKET` | Bucket used for generated media |
| `AWS_REGION` | Region name |
| `S3_ENDPOINT_URL` | S3-compatible endpoint, e.g. MinIO |
| `S3_PUBLIC_BASE_URL` | Public URL prefix used in generated asset URLs |

### Webhooks, moderation, and telemetry

| Variable | Purpose |
| --- | --- |
| `WEBHOOK_SIGNING_SECRET` | HMAC secret for `/v1/webhooks/ingest` |
| `MODERATION_PROVIDER` | `internal` or `openai` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OpenTelemetry exporter endpoint |
| `LOGFIRE_TOKEN` | Optional observability token |

### Platform publishing credentials

| Variable | Purpose |
| --- | --- |
| `PLATFORM_MOCK_MODE` | Global mock/safe publishing mode |
| `INSTAGRAM_ACCESS_TOKEN` | Instagram adapter credential |
| `TWITTER_BEARER_TOKEN` | Twitter/X adapter credential |
| `TWITTER_API_KEY` | Twitter/X adapter credential |
| `TWITTER_API_SECRET` | Twitter/X adapter credential |
| `LINKEDIN_ACCESS_TOKEN` | LinkedIn adapter credential |
| `TIKTOK_ACCESS_TOKEN` | TikTok adapter credential |
| `FACEBOOK_ACCESS_TOKEN` | Facebook adapter credential |
| `FACEBOOK_PAGE_ID` | Facebook page ID |
| `FACEBOOK_PAGE_ACCESS_TOKEN` | Facebook page access token |
| `META_GRAPH_VERSION` | Meta Graph API version |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token |
| `TELEGRAM_CHAT_ID` | Telegram target chat or channel |
| `YOUTUBE_ACCESS_TOKEN` | YouTube adapter credential |

### Other configured settings

| Variable | Purpose |
| --- | --- |
| `PINECONE_API_KEY` | Present in settings, not used by current workflow |
| `PINECONE_INDEX` | Present in settings, not used by current workflow |
| `RATE_LIMIT_AUTHENTICATED` | Default authenticated rate limit |
| `RATE_LIMIT_ANONYMOUS` | Default anonymous rate limit |

### Frontend variable

| Variable | Purpose |
| --- | --- |
| `VITE_API_BASE_URL` | Frontend API base URL override; defaults to `/v1` |

### `.env.example` guidance

The checked-in [`.env.example`](./.env.example) is aligned with the current code. A minimal local setup usually needs:

```env
ENVIRONMENT=local
DEBUG=true
DATABASE_URL=postgresql+asyncpg://campaign:campaign@postgres:5432/campaign_db
REDIS_URL=redis://redis:6379/0
AUTH_PROVIDER=local
JWT_ALGORITHM=HS256
JWT_SECRET=change-me
OLLAMA_BASE_URL=http://ollama:11434
IMAGE_PROVIDER=placeholder
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin
AWS_S3_BUCKET=campaign-assets
S3_ENDPOINT_URL=http://minio:9000
S3_PUBLIC_BASE_URL=http://localhost:9000/campaign-assets
PLATFORM_MOCK_MODE=true
```

Security note: do not commit real API keys, Telegram bot tokens, JWT secrets, or storage credentials. `.env` is listed in `.gitignore`; only `.env.example` is tracked.

## 9. Installation and Setup

### Clone and prepare

```bash
git clone https://github.com/<your-username>/candas-ai.git
cd candas-ai
cp .env.example .env
```

### Backend dependencies

```bash
python -m venv .venv
source .venv/bin/activate      # Linux / macOS
.venv\Scripts\activate         # Windows
pip install -U pip
pip install -e ".[dev]"
```

### Frontend dependencies

```bash
cd frontend
npm install
cd ..
```

### Database migrations

```bash
alembic upgrade head
```

## 10. Running the System with Docker Compose

The Compose file in [`docker-compose.yml`](./docker-compose.yml) defines these services:

| Service | Purpose |
| --- | --- |
| `postgres` | PostgreSQL with pgvector image |
| `redis` | Redis broker/backend/cache |
| `minio` | S3-compatible object storage |
| `ollama` | Local text-generation service |
| `api` | FastAPI backend |
| `frontend` | Vite development server |
| `worker` | Celery worker |
| `beat` | Celery Beat scheduler |

### Start everything

```bash
docker compose up --build
```

### Open the main endpoints

```text
Frontend (Vite dev): http://localhost:5173/app
Backend API:         http://localhost:8000
Swagger UI:          http://localhost:8000/docs
ReDoc:               http://localhost:8000/redoc
Health:              http://localhost:8000/health
MinIO console:       http://localhost:9001
```

### Pull the Ollama model if needed

```bash
docker compose exec ollama ollama pull llama3.1:8b
```

### Useful Docker commands

```bash
docker compose ps
docker compose logs -f api
docker compose logs -f worker
docker compose logs -f beat
docker compose down
```

## 11. Running Frontend and Backend Separately

Yes, the code supports this, with one caveat:

- The backend can run directly with Uvicorn.
- The frontend can run directly with Vite.
- If the frontend is run outside Docker, set `VITE_API_BASE_URL` to a reachable backend URL because the default Vite proxy targets `http://api:8000`.

### Run infrastructure only with Docker

```bash
docker compose up -d postgres redis minio ollama
```

### Run backend locally

```bash
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Run Celery worker locally

```bash
celery -A app.workers.celery_app.celery_app worker --loglevel=INFO
```

### Run Celery Beat locally

```bash
celery -A app.workers.celery_app.celery_app beat --loglevel=INFO
```

### Run frontend locally

```bash
cd frontend
export VITE_API_BASE_URL=http://localhost:8000/v1   # Linux / macOS
set VITE_API_BASE_URL=http://localhost:8000/v1      # Windows (cmd)
npm run dev -- --host 0.0.0.0
```

## 12. Using the Application

### Authentication

The frontend login page uses local JWT issuance through `/v1/auth/local-token`. This is not email/password authentication. The backend creates or updates a local organisation and user record, then returns a signed JWT. No password verification flow is implemented in local mode.

Supported auth modes in code:

- `local`
- `auth0`
- `keycloak`

Actual token verification behavior:

- `local` or any HS algorithm: verifies token with `JWT_SECRET`
- `auth0` and `keycloak`: fetches JWKS and validates bearer tokens

### Role-based access control

RBAC is implemented in [`app/api/deps.py`](./app/api/deps.py).

| Role | Meaning in current API |
| --- | --- |
| `viewer` | Can read protected data |
| `editor` | Can create campaigns, edit posts, schedule, and trigger publishing |
| `approver` | Can approve or reject campaigns |
| `admin` | Can access all role-protected endpoints and delete user data |

### Frontend pages

| Route | Purpose |
| --- | --- |
| `/login` | Local JWT login |
| `/` | Home dashboard |
| `/campaigns` | Campaign list |
| `/campaigns/new` | Campaign creation wizard |
| `/campaigns/:campaignId` | Campaign detail, trace stream, editing, scheduling, approval |
| `/approvals` | Pending approval queue |
| `/analytics` | Campaign analytics view |
| `/api-console` | OpenAPI-driven API explorer |
| `/settings` | Settings page |

## 13. Demo Flow

```mermaid
flowchart TD
    A[Open /app or Vite frontend] --> B[Generate local JWT]
    B --> C[Create campaign]
    C --> D[Backend queues graph task]
    D --> E[Watch SSE timeline]
    E --> F[Review generated posts]
    F --> G[Edit copy/image or accept]
    G --> H[Select publish times]
    H --> I[Approver approves campaign]
    I --> J[Celery schedules and publishes due posts]
    J --> K[Telegram receives published content]
    K --> L[Analytics refresh persists metrics]
```

### Suggested demo steps

1. Start the stack with `docker compose up --build`.
2. Open `http://localhost:5173/app`.
3. Log in with a local role such as `editor` or `approver`.
4. Create a campaign from the wizard.
5. Open the campaign detail page and watch the agent trace.
6. Review or edit draft posts and assign schedules.
7. Approve the campaign with an `approver` or `admin` account.
8. Wait for due-time publication or trigger publish manually.
9. Check Telegram output if real Telegram credentials are configured.

## 14. API Documentation

### FastAPI docs

- Swagger UI: `GET /docs`
- ReDoc: `GET /redoc`
- OpenAPI JSON: `GET /openapi.json`

### Main API route structure

Base prefix: `/v1`

| Group | Endpoints verified in code |
| --- | --- |
| Health | `GET /health`, `GET /v1/health`, `GET /v2/health` |
| Auth | `POST /v1/auth/local-token` |
| Campaigns | `POST /v1/campaigns`, `GET /v1/campaigns`, `GET /v1/campaigns/{campaign_id}`, `GET /v1/campaigns/{campaign_id}/dashboard`, `POST /v1/campaigns/{campaign_id}/schedule-suggestions`, `PATCH /v1/campaigns/{campaign_id}`, `DELETE /v1/campaigns/{campaign_id}`, `GET /v1/campaigns/{campaign_id}/stream` |
| Posts | `POST /v1/posts/{post_id}/schedule`, `POST /v1/posts/{post_id}/publish`, `PATCH /v1/posts/{post_id}`, `GET /v1/posts/scheduled`, `GET /v1/posts` |
| Approvals | `POST /v1/approvals/{approval_id}/decision`, `GET /v1/approvals/pending`, `GET /v1/approvals/campaign/{campaign_id}` |
| Analytics | `GET /v1/analytics/{campaign_id}`, `POST /v1/analytics/{campaign_id}/refresh` |
| Webhooks | `POST /v1/webhooks/ingest` |
| Users | `DELETE /v1/users/{user_id}/data` |

### Example: issue a local token

```bash
curl -X POST http://localhost:8000/v1/auth/local-token \
  -H "Content-Type: application/json" \
  -d '{
    "email": "editor@example.com",
    "name": "Local Editor",
    "role": "editor",
    "org_name": "Demo Org"
  }'
```

### Example: create a campaign

```bash
curl -X POST http://localhost:8000/v1/campaigns \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <JWT>" \
  -d '{
    "title": "Telegram Launch Campaign",
    "brief": "Promote a new AI productivity tool for small teams.",
    "platforms": ["telegram", "linkedin"],
    "goals": ["awareness", "engagement"],
    "target_audience": {"segment": "small business teams"}
  }'
```

### Example: stream workflow events

```bash
curl -N "http://localhost:8000/v1/campaigns/<campaign_id>/stream?token=<JWT>"
```

## 15. Background Workers and Scheduling

Celery is configured in [`app/workers/celery_app.py`](./app/workers/celery_app.py) with Redis as both broker and result backend.

### Implemented tasks

| Task | File | Purpose |
| --- | --- | --- |
| `run_campaign_graph_task` | `app/workers/campaign_tasks.py` | Runs the LangGraph workflow |
| `run_post_approval_task` | `app/workers/campaign_tasks.py` | Transitions approved posts into scheduled flow |
| `publish_post_task` | `app/workers/campaign_tasks.py` | Schedules or immediately publishes a single post |
| `publish_due_posts_task` | `app/workers/campaign_tasks.py` | Publishes all due scheduled posts |
| `ingest_webhook_task` | `app/workers/campaign_tasks.py` | Stubbed webhook background consumer |
| `fetch_analytics_task` | `app/workers/analytics_tasks.py` | Refreshes analytics for a campaign or post |

### Beat schedule

Celery Beat currently schedules one recurring job:

- `publish-due-posts-every-minute`
- Cron: every minute
- Task name: `publish_due_posts_task`

```mermaid
flowchart TD
    Beat[Celery Beat] --> MinuteJob[publish_due_posts_task]
    MinuteJob --> Worker[Celery Worker]
    Worker --> DB[(PostgreSQL)]
    Worker --> Due[Find scheduled posts with scheduled_at <= now]
    Due --> Publish[Publish via platform adapter]
    Publish --> Analytics[Fetch analytics for published posts]
    Analytics --> DB
```

## 16. Media Storage and Telegram Publishing

### Media generation

Image generation is implemented in [`app/agents/tools/media_gen_tool.py`](./app/agents/tools/media_gen_tool.py).

Verified provider behavior:

- `IMAGE_PROVIDER=placeholder`
  - Generates a local placeholder image using Pillow
  - Uploads the result to S3/MinIO
- `IMAGE_PROVIDER=openai`
  - Calls `https://api.openai.com/v1/images/generations`
  - Uses model `gpt-image-1`
  - Falls back to placeholder if the API key is missing, the API returns an error, or the generated image cannot be downloaded
- `IMAGE_PROVIDER=pollinations`
  - Fetches an image from Pollinations
  - Falls back to placeholder on failure

### Storage behavior

- Images are uploaded with `boto3`
- Bucket creation is attempted automatically if missing
- Default local object storage endpoint is MinIO
- Public URLs are built from `S3_PUBLIC_BASE_URL`

### Telegram publishing

Telegram is the only publishing adapter in this repository that contains a real API integration path.

Verified Telegram behavior:

- Uses `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`
- Sends `sendPhoto` if an image URL is present
- If the image is stored in MinIO/S3 and matches the configured base URL, the adapter downloads the object and uploads image bytes to Telegram
- Falls back to `sendMessage` if image upload fails
- Returns Telegram message IDs and a public `t.me/...` link when publishing to a channel handle

```mermaid
flowchart LR
    Creator[Creator Node] --> ImageGen[Image Provider]
    ImageGen --> Upload[Upload to MinIO / S3]
    Upload --> Post[Post row stores image_url]
    Post --> Worker[Celery publish task]
    Worker --> TG[Telegram Adapter]
    TG --> API[Telegram Bot API]
    API --> Msg[Telegram message / channel post]
    Worker --> Log[Publishing log + analytics refresh]
```

### Other platform adapters

Adapters exist for:

- Instagram
- Twitter/X
- LinkedIn
- TikTok
- Facebook
- YouTube

However, the code shows these are not production-ready implementations. They rely on generic placeholder endpoints or mock-safe behavior and should be described as partial or future extension points, not finished integrations.

## 17. Testing

The test suite structure is present and configured in [`pyproject.toml`](./pyproject.toml).

### Test folders

| Folder | Current status |
| --- | --- |
| `tests/unit` | Real unit tests for selected tools and adapters |
| `tests/integration` | Placeholder integration test scaffold |
| `tests/evals` | Placeholder evaluation threshold test |
| `tests/load` | Locust load-test scenario |

### Available commands

Run all pytest tests:

```bash
pytest
```

Run unit tests only:

```bash
pytest tests/unit
```

Run a specific unit test file:

```bash
pytest tests/unit/test_platform_adapters.py
pytest tests/unit/test_scheduler_tool.py
pytest tests/unit/test_brand_compliance_tool.py
```

Run load testing:

```bash
locust -f tests/load/locustfile.py --host http://localhost:8000
```

Start test infrastructure from Compose:

```bash
docker compose -f docker-compose.test.yml up -d
```

### Verified test coverage examples

- Telegram adapter S3-download publish path
- Telegram adapter photo-to-message fallback
- Mock publish path for a platform adapter

## 18. Troubleshooting

### Backend does not start

```bash
docker compose logs -f api
```

Check:

- PostgreSQL is healthy
- `DATABASE_URL` is correct
- Alembic migrations succeeded

### Frontend cannot reach backend

If running the frontend locally outside Docker, set:

```bash
export VITE_API_BASE_URL=http://localhost:8000/v1   # Linux / macOS
set VITE_API_BASE_URL=http://localhost:8000/v1      # Windows (cmd)
```

### Campaign generation fails

Check:

- Ollama container is running
- The configured Ollama model has been pulled
- `OLLAMA_BASE_URL` is reachable from the API container

### Images are placeholders

This is expected when:

- `IMAGE_PROVIDER=placeholder`
- `IMAGE_PROVIDER=openai` but `OPENAI_API_KEY` is missing
- OpenAI or Pollinations generation fails

### Telegram publishing fails

Check:

- `PLATFORM_MOCK_MODE=false`
- `TELEGRAM_BOT_TOKEN` is set
- `TELEGRAM_CHAT_ID` is set
- The bot is allowed to post in the target chat or channel

### Scheduled posts do not publish

Check:

- Celery worker is running
- Celery Beat is running
- Redis is available
- Every post has a `publish_at` set before approval

### SSE stream is not updating

Check:

- Redis pub/sub is available
- The frontend has a valid JWT token
- The campaign stream endpoint is reachable

## 19. Current Limitations

- Telegram is the implemented real publishing platform; other platform adapters are scaffolded or mock-oriented.
- Local auth issues JWTs without password verification; this is suitable for local or controlled demo environments, not a full identity system.
- The `researcher` node does not perform live web search.
- Campaign memory retrieval currently falls back to recent stored content; the code comments indicate pgvector similarity search is intended but not fully implemented in the retrieval path.
- Pinecone settings exist but are not used by the current workflow.
- `ANTHROPIC_API_KEY` and `RUNWAY_API_KEY` are defined in settings but not used by the current implemented pipeline.
- Integration tests and eval tests are mostly placeholders.
- The webhook background consumer currently returns `None` and does not yet implement downstream automation logic.
- The `/v2` API is only a reserved health stub.

## 20. Future Work

- Replace placeholder or generic social adapters with real production API flows for Meta, LinkedIn, X/Twitter, TikTok, and YouTube
- Implement true vector similarity retrieval over campaign embeddings
- Expand analytics collection with platform-specific real metrics
- Replace placeholder evaluation tests with live benchmark datasets
- Add richer approval workflows and audit trails
- Expand webhook-triggered automation
- Harden deployment settings for production OIDC, secrets management, and observability backends

## 21. Authors

Course project for **AI483**, College of Computer and Cyber Sciences, Department of Artificial Intelligence.

- Sana Mouazen
- Ghaidaa Osailan

Instructor: Dr. Sayed Bukhari

## 22. License

Released under the [MIT License](LICENSE).
