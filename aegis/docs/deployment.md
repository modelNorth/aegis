# Aegis Deployment Guide

## Prerequisites

- Python 3.11+
- Redis 7+
- Supabase project with pgvector enabled
- OpenAI API key
- Tesseract OCR (for image scanning)

---

## Local Development

```bash
# 1. Clone and install
git clone https://github.com/modelNorth/aegis.git
cd aegis
pip install -e ".[dev]"

# 2. Configure environment
cp .env.example .env
# Edit .env with your credentials

# 3. Start Redis
docker run -d -p 6379:6379 redis:7-alpine

# 4. Apply database migrations
psql $DATABASE_URL -f supabase/migrations/001_initial_schema.sql
psql $DATABASE_URL -f supabase/migrations/002_enable_vector.sql

# 5. Start API server
aegis serve --reload

# 6. Start worker (separate terminal)
aegis worker
```

---

## Docker Compose Deployment

```bash
cp .env.example .env
# Edit .env

docker-compose up -d
docker-compose logs -f api
```

Services started:
- `redis`: Redis 7 with persistence
- `api`: FastAPI server on port 8000 (2 workers)
- `worker`: BullMQ job processor

---

## Production Deployment

### Environment Variables

Set these in your deployment environment:

```bash
AEGIS_ENV=production
AEGIS_DEBUG=false
AEGIS_SECRET_KEY=<64-char random string>
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=<service role key>
REDIS_URL=rediss://:<password>@your-redis:6380/0
OPENAI_API_KEY=sk-...
MEM0_API_KEY=<mem0 key>
```

### Scaling

- API: Scale horizontally behind a load balancer
- Worker: Scale independently based on queue depth
- Redis: Use Redis Cluster or managed Redis (AWS ElastiCache, Upstash)

### Health Checks

```bash
curl http://your-host:8000/health
```

Returns HTTP 200 when all services are healthy.

---

## Supabase Setup

### 1. Create Project

Create a new Supabase project at https://supabase.com.

### 2. Enable pgvector

In the Supabase SQL editor, run:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### 3. Run Migrations

```bash
# Using Supabase CLI
supabase db push

# Or manually
psql $DATABASE_URL -f supabase/migrations/001_initial_schema.sql
psql $DATABASE_URL -f supabase/migrations/002_enable_vector.sql
```

### 4. Create API Key

```sql
INSERT INTO api_keys (key_hash, tier, user_id, description)
VALUES (
  encode(sha256('your-api-key'::bytea), 'hex'),
  'pro',
  'your-user-id',
  'Production API key'
);
```

---

## Monitoring

### Structured Logs

Aegis uses `structlog` for JSON-formatted logs:

```json
{"event": "request_completed", "method": "POST", "path": "/v1/scan", "status_code": 202, "duration_ms": 45}
{"event": "scan_job_completed", "job_id": "...", "risk_level": "high", "is_injection": true}
```

### Key Metrics to Monitor

- Queue depth: Number of pending jobs in BullMQ
- Processing time: `processing_time_ms` in scan results
- Error rate: Failed jobs vs completed jobs
- Detection rate: `is_injection=true` percentage

---

## PyPI Distribution

```bash
# Build package
python -m build

# Publish to PyPI
pip install twine
twine upload dist/*

# Install from PyPI
pip install aegis-guard
```
