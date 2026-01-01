# API Monitor

## Overview
API Monitor is a backend service that validates API responses against a defined response contract.  
It detects breaking changes (schema drift, latency regressions, failures) before downstream systems are affected.

---

## Core Functionality
- Define API checks (endpoint + expectations)
- Execute checks on a schedule
- Validate responses for correctness
- Store execution history
- Surface failures early

---

## Tech Stack
- Python
- FastAPI
- Pydantic
- httpx
- PostgreSQL
- APScheduler
- Docker / docker-compose

---

## Key Endpoints
POST /checks
GET /checks
GET /checks/{id}/history

---

## Validation Logic
- Status code checks
- Required response field checks (dot-path notation)
- Latency thresholds
- Repeated failure detection

---

## Architecture (High-Level)
Scheduler → Test Runner → Comparator → Database → Alerts

## Next Steps
1. **Stabilize backend — done**
   - Clean structure
   - Error handling, retries, timeouts
   - Persist health, latency, history in DB

2. **Harden scheduler - done**
   - Single APScheduler instance
   - DB-backed job store
   - Jobs survive restarts

3. **Dockerize app - done**
   - Dockerfile
   - docker-compose for local dev
   - Env vars for config/secrets

4. **Set up cloud**
   - Choose provider (Render / Railway / Fly.io)
   - Managed Postgres
   - Configure env vars

5. **Add CI (Continuous Integration)**
   - Run tests & lint on every push
   - Build Docker image
   - Fail fast on errors

6. **Add CD (Continuous Deployment)**
   - Auto-deploy if CI passes
   - No manual redeploys

7. **Deploy backend**
   - Public HTTPS endpoint
   - Scheduler running in production
   - Verify DB + jobs

8. **Add basic frontend**
   - Status dashboard
   - Latency/history view

9. **Alerts & observability**
   - Email/Slack alerts
   - Logs & basic metrics