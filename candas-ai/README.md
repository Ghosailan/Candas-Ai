\# CANDAS AI



\*\*Agentic AI platform for marketing campaign orchestration, content generation, approval, scheduling, and publishing.\*\*



CANDAS AI turns a campaign brief into platform-ready content through a multi-stage agentic workflow, while keeping humans in control of approval and publication.



!\[Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python\\\&logoColor=white)

!\[FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi\\\&logoColor=white)

!\[React](https://img.shields.io/badge/React-18-61DAFB?logo=react\\\&logoColor=black)

!\[LangGraph](https://img.shields.io/badge/LangGraph-Agentic\_Workflow-1C3C3C)

!\[PostgreSQL](https://img.shields.io/badge/PostgreSQL-pgvector-4169E1?logo=postgresql\\\&logoColor=white)

!\[Redis](https://img.shields.io/badge/Redis-Workers\_%26\_Events-DC382D?logo=redis\\\&logoColor=white)

!\[Celery](https://img.shields.io/badge/Celery-Background\_Workers-37814A)

!\[Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker\\\&logoColor=white)

!\[License](https://img.shields.io/badge/License-MIT-yellow)



> \*\*Project status:\*\* Working academic/engineering prototype. Telegram is the currently implemented real publishing integration; other platform adapters are partial or mock-oriented extensions.



\---



\## Overview



CANDAS AI is an agentic marketing automation system designed to take a campaign from \*\*brief → research → content generation → reflection → human approval → scheduling → publishing → analytics\*\*.



Instead of treating content generation as a single LLM call, the system coordinates multiple specialized stages through a LangGraph workflow and supporting backend services.



The platform combines:



\* Multi-stage agent orchestration

\* Human-in-the-loop approval

\* LLM-powered content generation

\* Brand compliance and moderation

\* Image generation and media storage

\* Background scheduling and publishing

\* Campaign analytics

\* Role-based access control

\* Real-time workflow updates

\* Dockerized infrastructure

\* Automated CI and testing



\---



\## What It Does



A typical campaign moves through the following lifecycle:



```text

Campaign Brief

&#x20;     ↓

Memory

&#x20;     ↓

Planning

&#x20;     ↓

Research

&#x20;     ↓

Content Creation

&#x20;     ↓

Reflection \& Quality Check

&#x20;     ↓

Human Approval

&#x20;     ↓

Scheduling

&#x20;     ↓

Publishing

&#x20;     ↓

Analytics

```



The reflection stage can send generated content back to the creator when the quality score does not meet the configured threshold.



Human approval remains a required control point before scheduled publication.



\---



\## Key Features



\### Agentic Workflow



Specialized workflow stages handle different parts of campaign generation:



\* Memory

\* Planning

\* Research

\* Content creation

\* Reflection

\* Human approval

\* Scheduling

\* Publishing

\* Analytics



\### Human-in-the-Loop



Generated campaigns do not automatically become publishable.



Users can:



\* Review generated posts

\* Edit content

\* Review generated media

\* Approve or reject campaigns

\* Schedule approved content



\### AI-Powered Content Generation



The system uses Ollama for text generation and supports configurable image-generation providers.



The creator stage can combine:



\* LLM-generated copy

\* Image prompts

\* Brand compliance checks

\* Moderation

\* Media generation

\* Campaign memory



\### Background Processing



Celery and Redis handle asynchronous campaign execution, scheduled publishing, analytics tasks, and recurring jobs.



\### Real-Time Workflow Updates



Server-Sent Events (SSE) provide live campaign workflow progress to the frontend.



\### Platform Publishing



Telegram currently has a real publishing integration.



Additional platform adapters are present for:



\* Instagram

\* X / Twitter

\* LinkedIn

\* TikTok

\* Facebook

\* YouTube



These additional adapters are currently partial, scaffolded, or mock-oriented rather than production integrations.



\### Security \& Privacy



The backend includes:



\* JWT-based authentication

\* Role-based access control

\* Webhook HMAC verification

\* Rate limiting

\* PII redaction helpers

\* User data deletion endpoints

\* Configurable authentication providers



\---



\## Architecture



```mermaid

flowchart LR

&#x20;   User --> Frontend\[React + Vite]



&#x20;   Frontend --> API\[FastAPI]

&#x20;   API --> Graph\[LangGraph Workflow]



&#x20;   Graph --> LLM\[Ollama]

&#x20;   Graph --> PostgreSQL\[(PostgreSQL + pgvector)]

&#x20;   Graph --> Redis\[(Redis)]



&#x20;   API --> Workers\[Celery Workers]

&#x20;   Workers --> Redis

&#x20;   Workers --> PostgreSQL

&#x20;   Workers --> Storage\[MinIO / S3]

&#x20;   Workers --> Telegram\[Telegram Bot API]



&#x20;   API --> SSE\[Server-Sent Events]

&#x20;   SSE --> Frontend

```



\### Main system layers



| Layer               | Implementation                             |

| ------------------- | ------------------------------------------ |

| Frontend            | React 18, TypeScript, Vite                 |

| API                 | FastAPI                                    |

| Agent orchestration | LangGraph                                  |

| Database            | PostgreSQL + SQLAlchemy + Alembic          |

| Vector support      | pgvector schema support                    |

| Background jobs     | Celery + Redis                             |

| Object storage      | MinIO / S3-compatible storage              |

| Text generation     | Ollama                                     |

| Image generation    | OpenAI Images / Pollinations / placeholder |

| Authentication      | JWT, Auth0/Keycloak-ready                  |

| Observability       | structlog, OpenTelemetry                   |

| Testing             | pytest, pytest-asyncio, Locust             |

| Infrastructure      | Docker Compose                             |



\---



\## Agent Workflow



The main workflow is defined in `app/agents/graph.py`.



```mermaid

flowchart TD

&#x20;   A\[Memory] --> B\[Planner]

&#x20;   B --> C\[Researcher]

&#x20;   C --> D\[Creator]

&#x20;   D --> E\[Reflection]



&#x20;   E -->|Quality below threshold| D

&#x20;   E -->|Quality accepted| F\[Human Approval]



&#x20;   F --> G\[Scheduler]

&#x20;   G --> H\[Publisher]

&#x20;   H --> I\[Analyst]

```



\### Agent responsibilities



| Stage      | Responsibility                                                |

| ---------- | ------------------------------------------------------------- |

| Memory     | Loads brand and recent campaign context                       |

| Planner    | Derives campaign goals and audience                           |

| Researcher | Builds internal campaign context                              |

| Creator    | Generates posts, prompts, media, and validates content        |

| Reflection | Evaluates generated content and triggers revision when needed |

| Approval   | Provides human review and approval                            |

| Scheduler  | Suggests and manages publication timing                       |

| Publisher  | Queues and executes publishing tasks                          |

| Analyst    | Stores campaign memory and retrieves analytics                |



\---



\## Project Structure



```text

.

├── .github/

│   └── workflows/             # CI pipeline

│

├── app/

│   ├── agents/                # LangGraph workflow, nodes, and tools

│   ├── api/                   # FastAPI routes

│   ├── core/                  # Security, logging, telemetry

│   ├── models/                # Database models

│   ├── platforms/             # Publishing adapters

│   ├── schemas/               # API schemas

│   ├── services/              # Business logic

│   └── workers/               # Celery workers and tasks

│

├── alembic/                   # Database migrations

├── frontend/                  # React/Vite application

├── tests/

│   ├── unit/

│   ├── integration/

│   ├── evals/

│   └── load/

│

├── docker-compose.yml

├── docker-compose.test.yml

├── Dockerfile

├── pyproject.toml

└── README.md

```



\---



\## Technology Stack



\### Backend



\* Python 3.12+

\* FastAPI

\* Pydantic

\* SQLAlchemy

\* Alembic

\* PostgreSQL

\* pgvector



\### AI



\* LangGraph

\* LangChain Core

\* Ollama

\* Configurable image generation providers

\* Internal moderation and brand-compliance tooling



\### Infrastructure



\* Docker

\* Docker Compose

\* Redis

\* Celery

\* MinIO / S3-compatible storage



\### Frontend



\* React 18

\* TypeScript

\* Vite

\* React Router



\### Testing \& Observability



\* pytest

\* pytest-asyncio

\* Locust

\* structlog

\* OpenTelemetry



\---



\## Getting Started



\### Prerequisites



For Docker-based execution:



\* Docker

\* Docker Compose



For running services separately:



\* Python 3.12+

\* Node.js 20+

\* PostgreSQL

\* Redis

\* MinIO or another S3-compatible object store

\* Ollama



\### Clone



```bash

git clone https://github.com/Ghosailan/Candas-Ai.git

cd Candas-Ai

```



\### Configure environment



```bash

cp .env.example .env

```



On Windows CMD:



```cmd

copy .env.example .env

```



For a local development setup, the default configuration can use:



```env

ENVIRONMENT=local

DEBUG=true



DATABASE\_URL=postgresql+asyncpg://campaign:campaign@postgres:5432/campaign\_db

REDIS\_URL=redis://redis:6379/0



AUTH\_PROVIDER=local

JWT\_ALGORITHM=HS256

JWT\_SECRET=change-me



OLLAMA\_BASE\_URL=http://ollama:11434



IMAGE\_PROVIDER=placeholder



AWS\_ACCESS\_KEY\_ID=minioadmin

AWS\_SECRET\_ACCESS\_KEY=minioadmin

AWS\_S3\_BUCKET=campaign-assets

S3\_ENDPOINT\_URL=http://minio:9000



PLATFORM\_MOCK\_MODE=true

```



> Never commit real API keys, JWT secrets, bot tokens, or storage credentials.



\---



\## Run with Docker Compose



Start the complete development stack:



```bash

docker compose up --build

```



Main services:



| Service       | URL / Purpose                  |

| ------------- | ------------------------------ |

| Frontend      | `http://localhost:5173/app`    |

| API           | `http://localhost:8000`        |

| Swagger       | `http://localhost:8000/docs`   |

| ReDoc         | `http://localhost:8000/redoc`  |

| Health        | `http://localhost:8000/health` |

| MinIO Console | `http://localhost:9001`        |



If required, pull the configured Ollama model:



```bash

docker compose exec ollama ollama pull llama3.1:8b

```



Useful commands:



```bash

docker compose ps

docker compose logs -f api

docker compose logs -f worker

docker compose logs -f beat

docker compose down

```



\---



\## Using the Application



A typical demo flow is:



1\. Start the Docker Compose stack.

2\. Open the frontend.

3\. Authenticate using the local development authentication flow.

4\. Create a campaign from the campaign wizard.

5\. Watch the agent workflow through the live timeline.

6\. Review and edit generated posts.

7\. Approve the campaign.

8\. Schedule posts.

9\. Publish through Telegram when real credentials are configured.

10\. Review stored analytics.



\---



\## API



The backend exposes FastAPI documentation automatically.



```text

Swagger UI

http://localhost:8000/docs



ReDoc

http://localhost:8000/redoc



OpenAPI

http://localhost:8000/openapi.json

```



Main API groups include:



\* Authentication

\* Campaigns

\* Posts

\* Approvals

\* Analytics

\* Webhooks

\* Users



\---



\## Testing



Run the test suite:



```bash

pytest

```



Unit tests:



```bash

pytest tests/unit

```



Specific tests:



```bash

pytest tests/unit/test\_platform\_adapters.py

pytest tests/unit/test\_scheduler\_tool.py

pytest tests/unit/test\_brand\_compliance\_tool.py

```



Load testing:



```bash

locust -f tests/load/locustfile.py --host http://localhost:8000

```



The repository currently contains unit tests, integration scaffolding, evaluation scaffolding, and load-test configuration.



\---



\## Current Implementation Status



| Capability                           | Status               |

| ------------------------------------ | -------------------- |

| Agentic campaign workflow            | Implemented          |

| Human approval workflow              | Implemented          |

| React frontend                       | Implemented          |

| FastAPI backend                      | Implemented          |

| Background workers                   | Implemented          |

| Redis event streaming                | Implemented          |

| PostgreSQL persistence               | Implemented          |

| MinIO/S3 media storage               | Implemented          |

| Telegram publishing                  | Implemented          |

| Other social adapters                | Partial / scaffolded |

| Live web research                    | Not implemented      |

| Full vector similarity retrieval     | Planned              |

| Production social integrations       | Planned              |

| Production-grade identity management | Planned              |

| Expanded AI evaluation suite         | Planned              |



\---



\## Limitations



CANDAS AI is an engineering/academic prototype rather than a production SaaS platform.



Current limitations include:



\* Telegram is the only implemented real publishing integration.

\* Other social platform adapters are incomplete or mock-oriented.

\* Local authentication is intended for development/demo use.

\* The researcher stage does not perform live web search.

\* Vector similarity retrieval is not fully implemented in the current memory retrieval path.

\* Some integration and evaluation tests remain scaffolding.

\* Webhook-driven downstream automation is not fully implemented.



These limitations are intentionally documented rather than hidden.



\---



\## Roadmap



\* \[ ] Production integrations for Meta, LinkedIn, X, TikTok, and YouTube

\* \[ ] True vector similarity retrieval for campaign memory

\* \[ ] Platform-specific analytics collection

\* \[ ] Expanded AI evaluation benchmarks

\* \[ ] Richer approval and audit workflows

\* \[ ] Webhook-triggered campaign automation

\* \[ ] Production deployment and secrets management

\* \[ ] Expanded observability and monitoring



\---



\## License



Released under the \[MIT License](LICENSE).



