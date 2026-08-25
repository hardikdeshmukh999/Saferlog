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
## 2026-08-25: API Time Range Filter
- **Prompt intent:** Add missing time range filter to the Query API based on the Requirement Document.
- **AI Contribution:** Missed the `from` and `to` time range query parameters in the initial API build.
- **Human Decision:** Corrected the AI by pointing out the requirement in `Requirement Document.txt`.
- **Outcome:** Added `from_time` and `to_time` parameters to `GET /events` in `api.py` and implemented the logic in `app/storage.py`.
## 2026-08-25: Chain Verification (Brick 7)
- **Prompt intent:** Implement the final Verification API.
- **AI Contribution:** Added `get_all_events` to storage, `verify_chain` to the service, and a `GET /audit/verify` endpoint in the API. Created an integration test that manually tampers with the SQLite database to prove the API correctly catches it.
- **Human Decision:** Approved the verification strategy.
- **Outcome:** Completed Scenario A requirements.

## 2026-08-25: Manual Tampering Experiment (Scenario A Wrap-up)
- **Prompt intent:** Investigate why manual tampering using a database GUI resulted in a persistent validation failure even after reverting the change.
- **AI Contribution:** Created `experiment.py` to programmatically demonstrate that the API correctly rejects tampered records and correctly validates restored records when changes are properly written to disk. Explained the "Write Changes" lock mechanism in SQLite GUI tools.
- **Human Decision:** Conducted manual tampering experiments on the database to rigorously test the chain's integrity.
- **Outcome:** Proven that the tamper-evident cryptographic logic works flawlessly when database changes are correctly saved. Scenario A is officially complete.

## 2026-08-25: Retention Policy (Scenario B - Topic 1)
- **Prompt intent:** Implement the archiving (soft-delete) feature without breaking chain verification.
- **AI Contribution:** Designed a scheme where `content_hash` is explicitly stored in the database. When an event is archived, its payload is set to NULL to save space/privacy, but `content_hash` remains. The verification endpoint uses the stored `content_hash` to prove the chain mathematically instead of hashing the (now deleted) payload. Added `POST /events/{hash}/archive`.
- **Human Decision:** Approved the design to ensure chain integrity persists even after payload deletion.
- **Outcome:** Successfully implemented and tested the Retention Policy.
