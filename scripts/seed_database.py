import requests
import json
import time

API_URL = "http://127.0.0.1:8000"
# Or 8001 if using the alternate port
try:
    requests.get(f"{API_URL}/events", timeout=2)
except requests.exceptions.ConnectionError:
    API_URL = "http://127.0.0.1:8001"

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": "Bearer supersecret"
}

events_to_seed = [
    {
        "eventType": "USER_LOGIN",
        "actorId": "user-A",
        "resourceType": "System",
        "resourceId": "sys-01",
        "payload": {"ip_address": "192.168.1.100", "browser": "Chrome"}
    },
    {
        "eventType": "PAYMENT_INITIATED",
        "actorId": "user-A",
        "resourceType": "Account",
        "resourceId": "acc-999",
        "payload": {"amount": 500, "currency": "USD", "credit_card": "4111-2222-3333-4444"},
        "sensitiveFields": ["credit_card"]
    },
    {
        "eventType": "PROFILE_UPDATE",
        "actorId": "user-B",
        "resourceType": "Profile",
        "resourceId": "prof-555",
        "payload": {"email": "user-b@example.com", "ssn": "123-45-678"},
        "sensitiveFields": ["ssn"]
    },
    {
        "eventType": "FILE_DOWNLOAD",
        "actorId": "user-C",
        "resourceType": "Document",
        "resourceId": "doc-12",
        "payload": {"filename": "Q3_Report.pdf", "bytes": 1048576}
    },
    {
        "eventType": "ADMIN_OVERRIDE",
        "actorId": "admin-1",
        "resourceType": "System",
        "resourceId": "sys-01",
        "payload": {"reason": "Customer requested refund bypass"}
    }
]

def seed():
    print(f"[*] Seeding database via API at {API_URL}...")
    
    for idx, event in enumerate(events_to_seed):
        response = requests.post(f"{API_URL}/events", headers=HEADERS, json=event)
        if response.status_code == 201:
            data = response.json()
            print(f"  [+] Inserted event {idx+1}/{len(events_to_seed)}: {data['eventType']} -> Hash: {data['hash'][:12]}...")
        else:
            print(f"  [-] Failed to insert event: {response.text}")
            return
        
        # Slight delay to ensure distinct timestamps
        time.sleep(0.1)
        
    print("\n[*] Database seeding complete! You can now browse the data in Swagger UI.")

if __name__ == "__main__":
    seed()
