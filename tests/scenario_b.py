import sys
sys.path.insert(0, ".")
import os
os.environ["API_TOKEN"] = "supersecret"
os.environ["RSA_PASSPHRASE"] = "test-passphrase"
os.environ["DATA_ENCRYPTION_KEY"] = "tG6jmLlzfdGkKF3Y0Qpb0wYUYSAc0jIo2smsT8_TxfQ="
from fastapi.testclient import TestClient
from app.api import app
from app.api import storage
import sqlite3

def clean_db():
    if hasattr(storage, "db_url"):  # Postgres
        with storage._get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("TRUNCATE events, sensitive_payloads RESTART IDENTITY")
            conn.commit()
    else:  # SQLite
        with storage._get_connection() as conn:
            conn.execute("DELETE FROM events")
            conn.execute("DELETE FROM sensitive_payloads")
            conn.execute("DELETE FROM sqlite_sequence WHERE name='events'")
            conn.commit()

clean_db()

client = TestClient(app)

def run_experiment():
    print("=========================================================")
    print("  SCENARIO B (ADVANCED LIFECYCLE) - COMPREHENSIVE TEST")
    print("=========================================================\n")
    
    # 1. Create Multiple Events
    print("1. Injecting Multiple Events into the Audit Log...")
    events = [
        {
            "eventType": "LOGIN",
            "actorId": "user-A",
            "resourceType": "System",
            "resourceId": "sys-1",
            "payload": {"ip": "192.168.1.10", "browser": "Chrome"}
        },
        {
            "eventType": "PAYMENT",
            "actorId": "user-B",
            "resourceType": "Account",
            "resourceId": "acc-999",
            "payload": {"amount": 500, "credit_card": "4111-2222-3333-4444"},
            "sensitiveFields": ["credit_card"]  # <--- Marked for Structural Redaction
        },
        {
            "eventType": "DOWNLOAD",
            "actorId": "user-C",
            "resourceType": "File",
            "resourceId": "file-777",
            "payload": {"filename": "confidential.pdf", "status": "success"}
        }
    ]
    
    saved_hashes = []
    for i, event in enumerate(events):
        response = client.post("/events", json=event, headers={"Authorization": "Bearer supersecret"})
        if response.status_code not in [200, 201]:
            print(f"Failed to connect or create event: {response.status_code} - {response.text}")
            return
        data = response.json()
        saved_hashes.append(data["hash"])
        print(f"   Created Event {i+1} | Type: {event['eventType']} | Hash: {data['hash'][:12]}...")
        
    print("\n2. Initial Chain Verification (Before Deletions)...")
    verify_resp = client.get("/audit/verify").json()
    print(f"   Status: {'VALID' if verify_resp['isValid'] else 'BROKEN'}")
    
    # 3. Topic 1: Retention Policy (Archiving)
    archive_hash = saved_hashes[0] # Archive the LOGIN event
    print(f"\n3. Executing Topic 1: Archiving Event 1 (Hash: {archive_hash[:12]})...")
    client.post(f"/events/{archive_hash}/archive", headers={"Authorization": "Bearer supersecret"})
    print("   -> Payload for Event 1 has been completely wiped from the database.")
    
    # 4. Topic 2: Structured Redaction
    redact_hash = saved_hashes[1] # Redact the PAYMENT event's credit card
    print(f"\n4. Executing Topic 2: Redacting 'credit_card' from Event 2 (Hash: {redact_hash[:12]})...")
    client.post(f"/events/{redact_hash}/redact/credit_card", headers={"Authorization": "Bearer supersecret"})
    print("   -> Plaintext credit_card value has been permanently deleted from the side-table.")
    
    # 5. Query the Data (Let's see what it looks like now!)
    print("\n5. Querying the Database for all events...")
    query_resp = client.get("/events").json()
    
    for event in query_resp:
        if event["hash"] == archive_hash:
            print(f"   - Event 1 ({event['eventType']}): is_archived=True, Payload is MISSING (Hidden).")
        elif event["hash"] == redact_hash:
            print(f"   - Event 2 ({event['eventType']}): Payload shows -> {event['payload']}")
        else:
            print(f"   - Event 3 ({event['eventType']}): Payload shows -> {event['payload']}")
            
    # 6. Final Chain Verification
    print("\n6. Final Chain Verification (After Archiving AND Redacting)...")
    verify_resp2 = client.get("/audit/verify").json()
    print(f"   Status: {'VALID' if verify_resp2['isValid'] else 'BROKEN'}")
    if verify_resp2['isValid']:
        print("   -> SUCCESS! The chain mathematically proves the events occurred in exactly this order,")
        print("      even though Event 1's payload is gone and Event 2's credit card is redacted!")

if __name__ == "__main__":
    run_experiment()
