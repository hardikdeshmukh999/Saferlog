import sys
sys.path.insert(0, ".")
import os
os.environ["API_TOKEN"] = "supersecret"
os.environ["RSA_PASSPHRASE"] = "test-passphrase"
os.environ["DATA_ENCRYPTION_KEY"] = "tG6jmLlzfdGkKF3Y0Qpb0wYUYSAc0jIo2smsT8_TxfQ="

from fastapi.testclient import TestClient
from app.api import app, storage

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
            # reset auto increment
            conn.execute("DELETE FROM sqlite_sequence WHERE name='events'")
            conn.commit()

clean_db()

client = TestClient(app)

def run_experiment():
    print("=========================================================")
    print("  SCENARIO A (GREENFIELD) - TAMPER DETECTION TEST")
    print("=========================================================\n")
    
    # 1. Create Multiple Events
    print("1. Injecting Events into the Audit Log...")
    events = [
        {"eventType": "LOGIN", "actorId": "user-A", "resourceType": "System", "resourceId": "sys-1", "payload": {"ip": "192.168.1.10"}},
        {"eventType": "UPLOAD", "actorId": "user-B", "resourceType": "File", "resourceId": "file-123", "payload": {"size": 1024}},
        {"eventType": "DELETE", "actorId": "user-A", "resourceType": "File", "resourceId": "file-123", "payload": {"reason": "cleanup"}}
    ]
    
    for event in events:
        client.post("/events", json=event, headers={"Authorization": "Bearer supersecret"})
        print(f"   Created Event | Type: {event['eventType']} | Actor: {event['actorId']}")

    # 2. Initial Chain Verification (Before Tampering)
    print("\n2. Initial Chain Verification...")
    response = client.get("/audit/verify")
    print(f"   Status: {'VALID' if response.json()['isValid'] else 'BROKEN'}")

    # 3. Simulate a Malicious Database Edit
    print("\n3. Malicious Actor directly modifies the database (Changing Event 2's payload)...")
    if hasattr(storage, "db_url"):  # Postgres
        with storage._get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("UPDATE events SET payload='{\"size\": 9999}' WHERE id=2")
            conn.commit()
    else:  # SQLite
        with storage._get_connection() as conn:
            conn.execute("UPDATE events SET payload='{\"size\": 9999}' WHERE id=2")
            conn.commit()
    print("   -> Tampering successful. Database edited behind the application's back.")

    # 4. Final Verification
    print("\n4. Final Chain Verification (After Tampering)...")
    response = client.get("/audit/verify")
    result = response.json()
    if not result['isValid']:
        print(f"   Status: BROKEN")
        print(f"   -> System successfully detected tampering! Reason: {result['message']}")
        print(f"   -> Broken Record Hash: {result['brokenRecordId']}")
    else:
        print("   Status: VALID (Uh oh, tampering went undetected!)")

if __name__ == "__main__":
    run_experiment()
