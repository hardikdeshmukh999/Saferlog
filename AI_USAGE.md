# AI Usage Traceability Log

This document tracks how AI was used to build the Audit Log Service, maintaining transparency for design decisions, generated code, and rationales.

## 2026-08-25: Project Setup and Event Model (Brick 1)
- **Prompt intent:** Understand the requirements document, outline a step-by-step TDD approach ("Lego Bricks"), and design the core Event model.
- **AI Contribution:** Proposed a `pydantic` model (`AuditEvent`) for data validation and a `pytest` framework for TDD. Recommended server-assigned timestamps instead of caller-provided timestamps for better security and hash chain integrity.
- **Human Decision:** Approved the TDD approach and server-assigned timestamps.
- **Outcome:** Created `app/canonical.py` and `tests/test_canonical.py`. Wrote passing tests.
