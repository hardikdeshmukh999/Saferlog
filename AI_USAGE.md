# AI Usage Traceability Log

This document tracks how AI was used to build the Audit Log Service, maintaining transparency for design decisions, generated code, and rationales.

## 2026-08-25: Project Setup and Event Model (Brick 1)
- **Prompt intent:** Understand the requirements document, outline a step-by-step TDD approach ("Lego Bricks"), and design the core Event model.
- **AI Contribution:** Proposed a `pydantic` model (`AuditEvent`) for data validation and a `pytest` framework for TDD. Recommended server-assigned timestamps instead of caller-provided timestamps for better security and hash chain integrity.
- **Human Decision:** Approved the TDD approach and server-assigned timestamps.
- **Outcome:** Created `app/canonical.py` and `tests/test_canonical.py`. Wrote passing tests.

## 2026-08-25: Refactoring Brick 1 and Designing Brick 2
- **Prompt intent:** Simplify the canonicalization logic and separate it from API payload validation. Define the hashing logic explicitly.
- **AI Contribution:** Initially proposed combining everything in `canonical.py` with Pydantic.
- **Human Decision:** Rejected the heavy OOP/Pydantic approach for core hashing. Directed the AI to refactor `canonical.py` into a simple pure function `canonical(value)` that returns deterministic JSON bytes, and `chain.py` for `content_hash` and `record_hash` functions.
- **Outcome:** Refactored `canonical.py` and created `chain.py` using pure functions. Tests pass.

## 2026-08-25: Storage Interface (Brick 3)
- **Prompt intent:** Define the storage layer for the audit events.
- **AI Contribution:** Proposed an in-memory Python list for simplicity.
- **Human Decision:** Overrode the AI's proposal, directing the use of `SQLite3` to provide a real, queryable, persistent database while still being lightweight enough for a prototype.
## 2026-08-25: Storage Optimization
- **Prompt intent:** Optimize the SQLite storage layer for querying.
- **AI Contribution:** Missed adding indexes for `event_type` and `timestamp` in the initial `SQLiteStorage` creation.
- **Human Decision:** Identified the missing indexes based on the requirement to query by `eventType` and filter by time range, and directed the AI to add them.
- **Outcome:** Added `idx_event_type` and `idx_timestamp` to `app/storage.py`.
## 2026-08-25: Audit Chain Logic (Brick 4)
- **Prompt intent:** Implement the coordinator service that ties together canonicalization, hashing, and storage.
- **AI Contribution:** Designed `AuditService` to automatically fetch the previous hash, assign a server timestamp, generate hashes, and save to SQLite.
- **Human Decision:** Approved the orchestration logic step-by-step.
- **Outcome:** Created `app/service.py` and `tests/test_service.py` with passing tests.
## 2026-08-25: Web APIs (Bricks 5 & 6)
- **Prompt intent:** Implement the Write and Query APIs to expose the service over HTTP.
- **AI Contribution:** Recommended using `FastAPI` for modern, fast API development and automatic documentation.
- **Human Decision:** Approved the use of FastAPI.
- **Outcome:** Created `app/api.py` with `POST /events` and `GET /events` endpoints. Wrote integration tests using FastAPI's `TestClient` in `tests/test_api.py`.
