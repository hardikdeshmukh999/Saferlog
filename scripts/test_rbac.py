import requests
import json
import time

API_URL = "http://127.0.0.1:8001"

def wait_for_server():
    print(f"[*] Waiting for API at {API_URL}...")
    for _ in range(10):
        try:
            requests.get(f"{API_URL}/docs", timeout=1)
            return True
        except:
            time.sleep(1)
    return False

def test_rbac():
    # 1. Admin creates event for user-A
    print("[*] Admin creating event for user-A...")
    res = requests.post(f"{API_URL}/events", headers={"Authorization": "Bearer supersecret"}, json={
        "eventType": "LOGIN",
        "actorId": "user-A",
        "resourceType": "System",
        "resourceId": "sys-1"
    })
    assert res.status_code == 201
    
    # 2. Admin creates event for user-B
    print("[*] Admin creating event for user-B...")
    res = requests.post(f"{API_URL}/events", headers={"Authorization": "Bearer supersecret"}, json={
        "eventType": "LOGIN",
        "actorId": "user-B",
        "resourceType": "System",
        "resourceId": "sys-1"
    })
    assert res.status_code == 201

    # 3. Admin querying all events (should see both)
    print("[*] Admin querying events...")
    res = requests.get(f"{API_URL}/events", headers={"Authorization": "Bearer supersecret"})
    assert res.status_code == 200
    events = res.json()
    assert len(events) >= 2
    
    # 4. user-A querying events (should only see user-A)
    print("[*] user-A querying events...")
    res = requests.get(f"{API_URL}/events", headers={"Authorization": "Bearer user-A-token"})
    assert res.status_code == 200
    events = res.json()
    assert all(e["actorId"] == "user-A" for e in events)
    assert len(events) > 0

    # 5. user-A tries to spoof creating an event as user-B
    print("[*] user-A spoofing user-B...")
    res = requests.post(f"{API_URL}/events", headers={"Authorization": "Bearer user-A-token"}, json={
        "eventType": "SPOOF",
        "actorId": "user-B",
        "resourceType": "System",
        "resourceId": "sys-1"
    })
    assert res.status_code == 201
    spoofed_event = res.json()
    assert spoofed_event["actorId"] == "user-A" # RBAC should override this!

    # 6. user-A tries to hit admin routes
    print("[*] user-A trying admin routes...")
    res = requests.get(f"{API_URL}/audit/verify", headers={"Authorization": "Bearer user-A-token"})
    assert res.status_code == 403

    res = requests.get(f"{API_URL}/events/export", headers={"Authorization": "Bearer user-A-token"})
    assert res.status_code == 403
    
    # 7. Unauthenticated hits
    print("[*] Unauthenticated trying routes...")
    res = requests.get(f"{API_URL}/events")
    assert res.status_code == 401

    print("[+] All RBAC tests passed successfully!")

if __name__ == "__main__":
    if wait_for_server():
        test_rbac()
    else:
        print("[-] API server not running.")
