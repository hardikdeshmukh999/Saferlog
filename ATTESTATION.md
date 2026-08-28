# Project Identity & Provenance
- **Name:** Hardik Deshmukh
- **Email:** hardikdeshmukh999@gmail.com
- **Assignment:** Build an AI-Assisted Software Engineering System — Audit Log Service
- **Dates:** 2026-08-25 to 2026-08-27
- **Submission Date:** 2026-08-27
- **Private GitHub Repository URL:** https://github.com/hardikdeshmukh999/Saferlog
- **Repository branch:** `master`
- **Reviewed commit SHA (Version 2):** `89794afa5083a7d981cee615c9292f997a9edaa1`

I, Hardik Deshmukh, attest that this submission is my own individual work, completed on my own
machine and accounts, and that it honestly reflects my development process and use of AI.

## Feature Implementation Map
If you are reviewing this project, here is exactly where to look in the source code to verify the core architectural claims:

1. **Tamper-Evident Hash Chain** -> Core logic in `app/service.py`, proven by `tests/test_chain.py`
2. **Cryptographic Export Signatures** -> Core logic in `app/crypto.py` and `app/api.py`
3. **Database Encryption at Rest (AES-GCM)** -> Core logic in `app/storage.py`, proven by `tests/test_api.py`
4. **Role-Based Access Control (RBAC)** -> Core logic in `app/api.py`, proven by `tests/test_rbac.py`
5. **Structured Redaction (Cryptographic Erasure)** -> Core logic in `app/storage.py`, proven by `tests/scenario_b.py`
6. **Retention Policy (Archiving)** -> Core logic in `app/storage.py`, proven by `tests/scenario_b.py`
7. **Deterministic JSON Canonicalization** -> Core logic in `app/service.py`, proven by `tests/test_canonical.py`

## AI & Reuse Disclosure
For a detailed explanation of AI prompts used and the human input provided, please refer to AI_USAGE.md. 
I have not reused any prior work or third-party code without permission. All code in this repository was written originally for this assignment.

## Signature
By signing below, I confirm that the information provided in this document is accurate and true.

**Signature:** _Hardik Deshmukh_  
**Printed Name:** Hardik Deshmukh  
**Date:** 2026-08-27
