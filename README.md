# 🔐 Crypto Operations & Risk Automation Platform

AI-powered internal operations platform for crypto exchange event management, fraud detection, and team routing.

---

## Architecture Overview

```
POST /api/v1/tickets
        ↓
  FastAPI (validation + persist)
        ↓ 202 Accepted
  Redis Task Queue
        ↓
  Celery Worker 1: AI Classification (Claude API)
        ↓
  Celery Worker 2: Fraud Detection (rule-based engine)
        ↓
  Celery Worker 3: Routing Engine (deterministic rules)
        ↓
  PostgreSQL (fully processed ticket)
        ↓
  Streamlit Dashboard (monitoring)
```

**Ticket status flow:**
`pending → classifying → classified → fraud_checking → fraud_checked → routed → resolved`

---

## Quick Start

### Prerequisites
- Docker & Docker Compose
- An Anthropic API key

### 1. Configure environment
```bash
cp .env.example .env
# Edit .env and set OPENAI_API_KEY=sk-your-openai-key-here
```

### 2. Start all services
```bash
docker-compose up --build -d
```

This starts:
| Service | URL |
|---|---|
| FastAPI Backend | http://localhost:8000 |
| API Documentation | http://localhost:8000/docs |
| Streamlit Dashboard | http://localhost:8501 |
| Celery Flower (task monitor) | http://localhost:5555 |
| PostgreSQL | localhost:5432 |
| Redis | localhost:6379 |

### 3. Verify everything is running
```bash
curl http://localhost:8000/health
```

---

## API Usage

### Submit a ticket
```bash
curl -X POST http://localhost:8000/api/v1/tickets \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "48291",
    "wallet_address": "0x82fa4b3e2a9dc99d21aa0000f8c7e8b192837465",
    "transaction_id": "TX192838",
    "message": "My withdrawal has been pending for 8 hours and I cannot access my funds"
  }'
```

**Response (202 Accepted):**
```json
{
  "ticket_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "message": "Ticket received and queued for processing"
}
```

### Check ticket status
```bash
curl http://localhost:8000/api/v1/tickets/550e8400-e29b-41d4-a716-446655440000
```

### Get fraud profile for a wallet
```bash
curl http://localhost:8000/api/v1/fraud/wallet/0x82fa4b3e2a9dc99d21aa0000f8c7e8b192837465
```

### Dashboard stats
```bash
curl http://localhost:8000/api/v1/dashboard/stats
```

### Mark ticket resolved
```bash
curl -X PATCH http://localhost:8000/api/v1/tickets/{ticket_id}/resolve
```

---

## Project Structure

```
crypto-ops-platform/
├── app/
│   ├── main.py                    # FastAPI app factory
│   ├── config.py                  # Settings (env-driven)
│   ├── api/v1/
│   │   ├── tickets.py             # Ticket ingestion + retrieval
│   │   ├── fraud.py               # Fraud intelligence endpoints
│   │   └── dashboard.py           # Dashboard stats API
│   ├── models/                    # SQLAlchemy ORM models
│   ├── schemas/                   # Pydantic request/response schemas
│   ├── db/
│   │   ├── session.py             # Async engine + session factory
│   │   └── migrations/            # Alembic migrations
│   ├── services/
│   │   └── ticket_service.py      # Ticket business logic
│   ├── ai/
│   │   ├── client.py              # Anthropic API client
│   │   ├── prompts.py             # Prompt templates
│   │   ├── classifier.py          # Classification engine + retry
│   │   └── schemas.py             # AI output validation schemas
│   ├── fraud/
│   │   ├── rules.py               # Individual fraud detection rules
│   │   ├── scorer.py              # Composite risk score computation
│   │   └── engine.py              # Fraud detection orchestrator
│   ├── routing/
│   │   ├── rules.py               # Routing decision rules
│   │   └── engine.py              # Routing orchestrator
│   ├── workers/
│   │   ├── celery_app.py          # Celery factory + configuration
│   │   └── tasks.py               # classify → fraud → route pipeline
│   └── utils/
│       ├── logging.py             # Structured JSON logging (structlog)
│       └── retry.py               # Retry decorators (tenacity)
├── dashboard/
│   └── app.py                     # Streamlit monitoring dashboard
├── tests/
│   ├── conftest.py                # Shared fixtures + test DB
│   ├── test_api/test_tickets.py   # API endpoint tests
│   ├── test_fraud/test_rules.py   # Fraud rule unit tests
│   ├── test_ai/test_classifier.py # AI engine tests (mocked)
│   └── test_services/test_routing.py # Routing rule tests
├── Dockerfile                     # API container
├── Dockerfile.worker              # Celery worker container
├── docker-compose.yml             # Full stack orchestration
├── alembic.ini                    # Migration configuration
└── pyproject.toml                 # Dependencies
```

---

## Fraud Detection Rules

| Rule | Trigger Condition | Base Score |
|---|---|---|
| `repeated_complaints` | ≥3 complaints for same wallet in 24h | 0.5+ |
| `high_tx_failure_rate` | ≥5 failed transactions in 24h | 0.4+ |
| `multi_account_wallet` | Wallet referenced by 2+ user accounts | 0.3–0.85 |
| `linked_flagged_wallet` | Previously flagged wallet history | 0.4–0.85 |
| `ai_high_fraud_score` | AI classifier returns score ≥ 0.4 | Mirrors AI score |

**Composite scoring:** Highest single rule score dominates. Each additional triggered rule adds 10% of its score (capped at 1.0).

---

## Routing Rules (Priority Order)

| Priority | Rule | Condition | Team |
|---|---|---|---|
| 1 | `RULE_001` | Composite fraud score ≥ 0.7 | Compliance Team |
| 2 | `RULE_002` | Category = `fraud_report` | Compliance Team |
| 3 | `RULE_003` | Category = `suspicious_transaction` | Fraud Investigation |
| 4 | `RULE_004` | Category = `wallet_access` or `account_access` | Security Team |
| 5 | `RULE_005` | Category = `withdrawal_issue` + priority critical/high | Technical Operations |
| 6 | `RULE_006` | Category = `transaction_failure` | Technical Operations |
| 7 | `RULE_007` | Fraud score ≥ 0.4 (medium) | Fraud Investigation |
| 8 | `RULE_008` | Category = `withdrawal_issue` + priority low | Customer Support |
| Default | `RULE_DEFAULT` | Everything else | Customer Support |

---

## Running Tests

```bash
# Install dev dependencies
pip install pytest pytest-asyncio pytest-cov httpx aiosqlite

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=app --cov-report=term-missing

# Run specific test file
pytest tests/test_fraud/test_rules.py -v
```

---

## Database Migrations

```bash
# Apply migrations
alembic upgrade head

# Create new migration (after model changes)
alembic revision --autogenerate -m "description_of_change"

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history
```

---

## Production Deployment (Railway / Render / Fly.io)

### Environment variables to configure:
```
APP_ENV=production
DATABASE_URL=postgresql+asyncpg://...
DATABASE_URL_SYNC=postgresql://...
REDIS_URL=redis://...
OPENAI_API_KEY=sk-your-openai-key-here
SECRET_KEY=<random-32-char-hex>
```

### Deploy to Railway:
```bash
railway init
railway up
```

### Scale workers independently:
```bash
# Classification workers (AI-bound, scale based on ticket volume)
celery -A app.workers.celery_app worker --queues=classification --concurrency=2

# Fraud + routing workers (DB-bound, faster)
celery -A app.workers.celery_app worker --queues=fraud,routing --concurrency=8
```

---

## Monitoring

- **API health:** `GET /health`
- **Celery tasks:** Flower UI at `:5555`
- **Operations dashboard:** Streamlit at `:8501`
- **Structured logs:** JSON format in production, readable in development

---

## Security Considerations

- All secrets via environment variables — never in code
- Non-root Docker users in all containers
- CORS restricted to internal domains in production
- API docs disabled in production (`docs_url=None`)
- Idempotency on ticket ingestion prevents duplicate processing
- All AI decisions include reasoning for audit trail
- Routing rule IDs stored for compliance review
