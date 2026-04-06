# Aegis API Documentation

## Overview

The Aegis REST API provides endpoints for content scanning, session management, and feedback collection.

**Base URL:** `http://your-host:8000`  
**Authentication:** `X-API-Key` header required on all `/v1/*` endpoints

---

## Authentication

All API endpoints require an `X-API-Key` header:

```http
X-API-Key: aegis_free_your_api_key_here
```

API key tiers determine rate limits:
- **Free**: 10 requests/minute
- **Pro**: 100 requests/minute
- **Enterprise**: 1000 requests/minute

---

## Endpoints

### Health Check

```http
GET /health
```

Returns server health and service status. No authentication required.

**Response:**
```json
{
  "status": "ok",
  "version": "0.1.0",
  "timestamp": "2024-01-01T00:00:00Z",
  "services": {
    "redis": "ok",
    "supabase": "ok"
  }
}
```

---

### Create Scan

```http
POST /v1/scan
```

Submit content for prompt injection analysis.

**Request Body:**
```json
{
  "content": "string (required)",
  "content_type": "text|html|pdf|image",
  "session_id": "uuid (optional)",
  "webhook_url": "https://... (optional)",
  "sync": false,
  "metadata": {}
}
```

**Notes:**
- `content` for PDF/image should be base64-encoded
- `sync: true` waits for result (max 30s)
- `webhook_url` receives result when async job completes

**Response (202 Accepted):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "created_at": "2024-01-01T00:00:00Z"
}
```

**Response (sync=true, 200 OK):**
```json
{
  "job_id": "...",
  "status": "completed",
  "result": {
    "job_id": "...",
    "risk_level": "high",
    "risk_score": 0.82,
    "is_injection": true,
    "confidence": 0.89,
    "findings": [...],
    "summary": "...",
    "content_type": "text",
    "processing_time_ms": 1250,
    "created_at": "..."
  }
}
```

---

### Get Scan Result

```http
GET /v1/scan/{job_id}
```

Retrieve the status and result of a scan job.

**Response:** Same as scan response above.

---

### Create Session

```http
POST /v1/sessions
```

Create a session to track related scans for behavioral analysis.

**Request Body:**
```json
{
  "user_id": "optional-user-id",
  "metadata": {}
}
```

**Response (201 Created):**
```json
{
  "session_id": "uuid",
  "user_id": "...",
  "created_at": "...",
  "scan_count": 0,
  "metadata": {}
}
```

---

### Get Session

```http
GET /v1/sessions/{session_id}
```

---

### Delete Session

```http
DELETE /v1/sessions/{session_id}
```

---

### Submit Feedback

```http
POST /v1/feedback
```

Provide feedback on a scan result to improve accuracy.

**Request Body:**
```json
{
  "job_id": "uuid (required)",
  "is_correct": true,
  "actual_risk_level": "safe|low|medium|high|critical",
  "notes": "optional notes"
}
```

**Response (201 Created):**
```json
{
  "feedback_id": "uuid",
  "job_id": "...",
  "accepted": true,
  "message": "Feedback recorded and memory updated"
}
```

---

## Risk Levels

| Level | Score Range | Description |
|-------|-------------|-------------|
| `safe` | 0.00-0.24 | No injection signals |
| `low` | 0.25-0.49 | Minor anomalies, likely benign |
| `medium` | 0.50-0.74 | Suspicious patterns, review recommended |
| `high` | 0.75-0.89 | High confidence injection attempt |
| `critical` | 0.90-1.00 | Definitive injection attack |

---

## Webhook Payload

When a webhook URL is provided, Aegis sends a signed POST request:

```json
{
  "event": "scan.completed",
  "job_id": "...",
  "timestamp": 1704067200.0,
  "result": { ... }
}
```

**Signature Verification:**
```python
import hmac, hashlib

def verify(payload_bytes, signature_header, secret):
    expected = hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature_header)
```

---

## Error Responses

All errors return structured JSON:

```json
{
  "error": "ErrorType",
  "message": "Human readable description",
  "details": {},
  "request_id": "uuid"
}
```

| Status | Error | Description |
|--------|-------|-------------|
| 400 | ValidationError | Invalid request data |
| 401 | AuthenticationError | Missing or invalid API key |
| 413 | FileTooLarge | Content exceeds size limit |
| 422 | UnprocessableEntity | Schema validation failed |
| 429 | RateLimitExceeded | Too many requests |
| 500 | InternalServerError | Unexpected server error |
