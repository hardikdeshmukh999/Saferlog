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
- **Outcome:** Pending rewrite of `canonical.py` and creation of `chain.py` using pure functions.
