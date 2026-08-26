# Saferlog: Tamper-Evident Audit Log Service

**Charles Schwab & Co., Inc.** — Interview Assignment Submission  
**Candidate:** Hardik Deshmukh  
**Date:** 2026-08-26

## Overview

Saferlog is a prototype microservice designed to ingest, store, and cryptographically verify audit log events. It implements a deterministic hash chain to guarantee non-repudiation and tamper-evidence, ensuring that once an event is recorded, it cannot be modified or reordered without breaking the mathematical integrity of the chain.

This project was built iteratively using an AI-Assisted Software Engineering System, covering three distinct scenarios:
- **Scenario A (Greenfield):** Core Audit Log Service
- **Scenario B (Extend Your Own System):** Retention (Archiving) and Redaction (Cryptographic Erasure)
- **Scenario C (Ambiguous Requirement):** Compliance Reporting via Cryptographically Signed Bulk Exports

---

## Setup Instructions

### Prerequisites
- Python 3.11+
- Windows/macOS/Linux

### 1. Installation
Clone the repository and navigate into the project root. Create a virtual environment and install the dependencies:
```bash
python -m venv venv
# Windows:
.\venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
```
*(If `requirements.txt` is missing, run: `pip install fastapi uvicorn sqlite3 cryptography pytest requests`)*

### 2. Running the API Server
Start the FastAPI server using Uvicorn:
```bash
uvicorn app.api:app --reload --port 8000
```
You can interact with the API directly through the automatically generated Swagger UI at:  
👉 **http://127.0.0.1:8000/docs**

> [!IMPORTANT]
> The API endpoints use **Zero-Trust HTTP Bearer Authentication**. To use the Swagger UI, click the green **"Authorize"** button and enter the default token: `supersecret`.

### 3. Running the Database (SQLite vs PostgreSQL)
By default, the application runs on **SQLite** so you can test it instantly without setting up a database server. 

If you want to test the enterprise **PostgreSQL** integration, spin up a local container:
```bash
docker run --name saferlog-pg -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=saferlog -p 5432:5432 -d postgres:latest
```
Then, set the environment variable before running the server or tests:
```bash
# Windows PowerShell
$env:DATABASE_URL="postgresql://postgres:postgres@localhost:5432/saferlog"

# macOS/Linux
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/saferlog"
```

### 4. Testing the Application

#### Option A: Automated Programmatic Tests
I have provided automated programmatic experiments that walk through all three scenarios from end-to-end. Leave the server running in one terminal, and in another terminal, run:
```bash
# Run Scenario A (Tamper Detection)
python scripts/scenario_a.py

# Run Scenario B (Retention Policy & Redaction)
python scripts/scenario_b.py

# Run Scenario C (Compliance Reporting Bulk Export)
python scripts/scenario_c.py
```

#### Option B: Interactive Swagger UI Guide
You can also manually test the API using the Swagger UI (`http://127.0.0.1:8000/docs`).

**Optional: Seed the Database**
If you want to instantly populate the database with a dataset of 5 events (including some sensitive data like credit cards and SSNs) so you don't have to type them out yourself, run this command:
```bash
python scripts/seed_database.py
```

**Step 1: Authenticate**
1. Click the green **Authorize** button at the top right.
2. In the "Value" box, type exactly: `supersecret`, click **Authorize**, then **Close**.

**Step 2: Create an Event (`POST /events`)**
1. Expand `POST /events`, click **Try it out**, and paste this JSON:
   ```json
   {
     "eventType": "PAYMENT",
     "actorId": "user-A",
     "resourceType": "Account",
     "resourceId": "acc-999",
     "payload": {
       "amount": 500,
       "credit_card": "4111-2222-3333-4444"
     },
     "sensitiveFields": ["credit_card"]
   }
   ```
2. Click **Execute**. Copy the `hash` value from the Server Response.

**Step 3: Redact the Credit Card (`POST /events/{event_hash}/redact/{field_name}`)**
1. Expand the redact route and click **Try it out**.
2. Paste the `hash` into the `event_hash` box.
3. Type `credit_card` in the `field_name` box and click **Execute**.
4. (Optional) Run `GET /events` to see that the credit card is now permanently `REDACTED:salt:hash`.

**Step 4: Archive an Event (`POST /events/{event_hash}/archive`)**
1. Expand the archive route, paste your `hash`, and click **Execute**.
2. (Optional) Run `GET /events` to verify the event is no longer returned in queries.

**Step 5: Verify the Chain (`GET /audit/verify`)**
1. Expand `GET /audit/verify`, click **Try it out**, and **Execute**.
2. Even though you deleted the sensitive payload (redaction) and archived the record, the response will be `"isValid": true` because the hash chain is mathematically intact!

**Step 6: Export & Verify the Signed Bundle (`GET /events/export`)**
1. Expand `GET /events/export` and **Execute**.
2. Copy the entire JSON response (which contains `"events"`, `"signature"`, and `"public_key"`).
3. Save it to a file named `test_export.json` in the project root.
4. Open a terminal and run the cryptographic verification script:
   ```bash
   python scripts/verify_export.py test_export.json
   ```
5. It will print `[+] SUCCESS: The export bundle signature is VALID.` proving the data wasn't tampered with outside the database!

---

### Architecture Overview

### Data Model & Storage Factory
The system uses a **Storage Factory Pattern** (`get_storage()`). By default, it runs seamlessly on **SQLite** to allow reviewers to run the prototype instantly. However, if the `DATABASE_URL` environment variable is detected, it automatically spins up a **PostgreSQL** connection using `psycopg2`, allowing for high-concurrency production deployments.

The schema contains two core tables:
1. `events`: The immutable, append-only log. It stores the `hash`, `previousHash`, and `content_hash` of each event, along with the `payload` (if not archived) and metadata.
2. `sensitive_payloads`: A mutable side-table used for **Cryptographic Erasure**. When sensitive fields are ingested, they are stored here in plaintext, while their dynamically salted hashes are saved in the `events` table. 

### Security & Authentication
The API enforces **Zero Trust** architecture. Write actions (creating events, redacting, archiving) are protected by a FastAPI `Depends` dependency that validates an `Authorization: Bearer <API_TOKEN>` header.

### Cryptographic Chain Design
- **Hashing Algorithm:** `SHA-256` (via Python's `hashlib`). Chosen for its industry-standard security, speed, and collision resistance.
- **Canonicalization:** To ensure the JSON `payload` consistently produces the exact same hash across different machines or languages, the payload is serialized deterministically (sorted keys, stripped whitespace) before hashing.
- **The Chain:** Every event calculates its hash as: `SHA256( previousHash + content_hash )`. This perfectly links every event to the history of the entire database, and the `content_hash` mathematically protects the metadata (including the `timestamp`) and the `payload`.

---

## Scenarios Completed

### Scenario A: Greenfield (Core Service)
- **Goal:** Build the append-only log and a `/audit/verify` API to detect tampering.
- **Execution:** Implemented deterministic JSON hashing and a verification loop that recalculates the chain from Genesis to the latest event.
- **Validation:** Proved via `scripts/scenario_a.py`, which manually edits a row in the database and successfully triggers a `TAMPERED_PAYLOAD` detection alert.

### Scenario B: Extend Your Own System
- **Topic 1 - Retention Policy (Archiving):** The `POST /events/{hash}/archive` API sets `payload = NULL` to save disk space. Verification holds because the `content_hash` remains stored intact.
- **Topic 2 - Structured Redaction:** To comply with privacy laws (e.g., GDPR), the system supports structural redaction. Specific fields (e.g., `credit_card`) are saved as hashes in the primary log, and plaintexts in a side-table. The `POST /events/{hash}/redact/{field}` API permanently deletes the plaintext side-table row.
- **Validation:** Both features were proven mathematically sound by `scripts/scenario_b.py`, which validates the chain before and after data deletion.

### Scenario C: Ambiguous Compliance Reporting
- **Requirement:** *"Regulators need to be able to audit access to client account data."*
- **Clarification & Design:** Exporting a non-contiguous subset of events from a linear hash chain breaks the mathematical proof. To solve this, I designed a **Cryptographically Signed JSON Bundle** feature.
- **Execution:** The `GET /events/export` API extracts the filtered data and signs it using an internal system RSA private key. The regulator is provided a standalone offline script (`scripts/verify_export.py`) to mathematically prove the bundle originated from Saferlog.

---

## Testing Approach, Limitations, and Trade-offs

### Testing Approach
- **Unit Testing:** Used `pytest` to test low-level deterministic JSON canonicalization and hash generation logic (`tests/test_service.py`).
- **Integration/E2E Testing:** Relied on programmatic python scripts (`scripts/scenario_*.py`) mimicking a live client interacting with the FastAPI endpoints (`TestClient` and `requests`), ensuring the entire lifecycle works continuously while passing the required `Bearer` authentication headers.

### Limitations & Trade-offs
- **Linear Hash Chain vs. Merkle Tree:** I chose a simple linear hash chain. It is easier to implement and perfectly tamper-evident. The trade-off is that you cannot mathematically verify a subset of data (like a Merkle Proof allows). We mitigated this limitation in Scenario C by using RSA signatures for exports instead.
- **Relational vs. NoSQL:** Using a relational database (PostgreSQL) is excellent for relational indexing, but NoSQL (like MongoDB) might offer faster pure-append throughput for logs. However, the requirement to do complex queries (Scenario C) made SQL the better choice.

### Production-Grade Upgrades
If this were deployed to production tomorrow, the following upgrades (which were built into this prototype) are crucial:
1. **PostgreSQL Fallback:** SQLite is replaced by PostgreSQL to prevent "database is locked" errors during highly concurrent writes.
2. **Streaming Generators:** The `/audit/verify` API uses server-side cursors (`yield`) to stream the hash chain into memory in chunks of 1,000, preventing Out-Of-Memory (OOM) crashes on multi-gigabyte databases.
3. **Dynamic Cryptographic Salting:** Redaction does not use a global static pepper. Instead, a unique 16-byte cryptographic salt (`os.urandom(16).hex()`) is generated for *every single sensitive field* and embedded in the deterministic JSON payload to thwart Rainbow Table attacks.

---

## Final Engineering Summary

Building Saferlog was an exercise in balancing immutable cryptographic non-repudiation with the very real business needs of data deletion (retention and privacy compliance). 

By strictly adhering to a modular architecture (separating `api.py`, `service.py`, `storage.py`, and `crypto.py`), the system proved highly extensible. When the requirement to structurally redact data was introduced in Scenario B, the separation of concerns allowed us to cleanly implement a side-table lookup strategy without rewriting the core hashing engine.

**AI Collaboration:** The AI was instrumental in identifying cryptographic edge cases early—specifically, recognizing that exporting non-contiguous blocks of a linear hash chain (Scenario C) is impossible to verify without intermediary hashes. The AI proposed the RSA Signed Bundle workaround, which I approved, resulting in a highly scalable and practical compliance solution.

All requirements have been met, documented, and proven through executable code. Thank you for the opportunity!
