import sys
sys.path.insert(0, ".")
import os
import sqlite3
from fastapi.testclient import TestClient
from app.api import app, storage

# Force a clean DB for the experiment
storage.db_path = 'saferlog_scenario_a.db'
try:
    if os.path.exists(storage.db_path):
        os.remove(storage.db_path)
except:
    pass

storage._conn = sqlite3.connect(storage.db_path, check_same_thread=False)
storage._conn.row_factory = sqlite3.Row
storage._init_db()

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
        client.post("/events", json=event)
        print(f"   Created Event | Type: {event['eventType']} | Actor: {event['actorId']}")

    # 2. Initial Chain Verification (Before Tampering)
    print("\n2. Initial Chain Verification...")
    response = client.get("/audit/verify")
    print(f"   Status: {'VALID' if response.json()['isValid'] else 'BROKEN'}")

    # 3. Simulate a Malicious Database Edit
    print("\n3. Malicious Actor directly modifies the SQLite database (Changing Event 2's payload)...")
    conn = sqlite3.connect(storage.db_path)
    conn.execute("UPDATE events SET payload='{\"size\": 9999}' WHERE id=2")
    conn.commit()
    conn.close()
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
