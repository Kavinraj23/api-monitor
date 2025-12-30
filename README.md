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