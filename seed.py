import httpx
import time

API_URL = "http://127.0.0.1:8000/events"

dummy_events = [
    {
        "eventType": "USER_LOGIN",
        "actorId": "admin-1",
        "resourceType": "System",
        "resourceId": "sys-01",
        "payload": {"ipAddress": "192.168.1.100", "browser": "Chrome", "os": "Windows"}
    },
    {
        "eventType": "FILE_UPLOAD",
        "actorId": "user-44",
        "resourceType": "Document",
        "resourceId": "doc-992",
        "payload": {"fileName": "financial_report_Q3.pdf", "fileSize_bytes": 4500000, "classification": "Confidential"}
    },
    {
        "eventType": "PERMISSION_CHANGE",
        "actorId": "admin-1",
        "resourceType": "Document",
        "resourceId": "doc-992",
        "payload": {"oldPermission": "READ", "newPermission": "WRITE", "targetUser": "user-44"}
    },
    {
        "eventType": "DATA_EXPORT",
        "actorId": "user-88",
        "resourceType": "Database",
        "resourceId": "db-users",
        "payload": {"recordsExported": 5000, "exportFormat": "CSV", "queryUsed": "SELECT * FROM users"}
    },
    {
        "eventType": "USER_LOGOUT",
        "actorId": "admin-1",
        "resourceType": "System",
        "resourceId": "sys-01",
        "payload": {"sessionDurationMinutes": 120}
    }
]

def seed_database():
    print("Seeding database with realistic dummy events...")
    try:
        with httpx.Client() as client:
            for event in dummy_events:
                response = client.post(API_URL, json=event)
                if response.status_code == 201:
                    print(f"[SUCCESS] Added {event['eventType']} event. Hash: {response.json()['hash'][:16]}...")
                else:
                    print(f"[ERROR] Failed to add event: {response.text}")
                
                # Sleep slightly so timestamps are spaced out
                time.sleep(0.5)

        print("\nVerifying chain integrity...")
        verify_response = httpx.get("http://127.0.0.1:8000/audit/verify")
        print(f"Verification status: {verify_response.json()}")
        
    except httpx.ConnectError:
        print("[ERROR] Could not connect to API. Is the Uvicorn server running?")

if __name__ == "__main__":
    seed_database()
