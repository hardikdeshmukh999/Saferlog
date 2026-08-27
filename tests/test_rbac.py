import pytest
import os
os.environ["API_TOKEN"] = "supersecret"
os.environ["RSA_PASSPHRASE"] = "test-passphrase"
os.environ["DATA_ENCRYPTION_KEY"] = "tG6jmLlzfdGkKF3Y0Qpb0wYUYSAc0jIo2smsT8_TxfQ="

from fastapi.testclient import TestClient
from app.api import app, storage

# Default client is admin
admin_client = TestClient(app, headers={"Authorization": "Bearer supersecret"})

# User client
user_client = TestClient(app, headers={"Authorization": "Bearer user-A-token"})

# Unauthenticated client
anon_client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_database():
    storage.db_path = ":memory:"
    import sqlite3
    storage._conn = sqlite3.connect(":memory:", check_same_thread=False)
    storage._conn.row_factory = sqlite3.Row
    storage._init_db()
    yield

def test_rbac_admin_can_create_and_view_all():
    # 1. Admin creates event for user-A
    res1 = admin_client.post("/events", json={
        "eventType": "LOGIN",
        "actorId": "user-A",
        "resourceType": "System",
        "resourceId": "sys-1"
    })
    assert res1.status_code == 201
    
    # 2. Admin creates event for user-B
    res2 = admin_client.post("/events", json={
        "eventType": "LOGIN",
        "actorId": "user-B",
        "resourceType": "System",
        "resourceId": "sys-1"
    })
    assert res2.status_code == 201

    # 3. Admin querying all events (should see both)
    res3 = admin_client.get("/events")
    assert res3.status_code == 200
    events = res3.json()
    assert len(events) == 2

def test_rbac_user_isolation():
    # Admin seeds data for multiple users
    admin_client.post("/events", json={"eventType": "LOGIN", "actorId": "user-A", "resourceType": "System", "resourceId": "sys-1"})
    admin_client.post("/events", json={"eventType": "LOGIN", "actorId": "user-B", "resourceType": "System", "resourceId": "sys-1"})
    
    # 4. user-A querying events (should only see user-A)
    res = user_client.get("/events")
    assert res.status_code == 200
    events = res.json()
    assert all(e["actorId"] == "user-A" for e in events)
    assert len(events) == 1

def test_rbac_user_anti_spoofing():
    # 5. user-A tries to spoof creating an event as user-B
    res = user_client.post("/events", json={
        "eventType": "SPOOF",
        "actorId": "user-B",
        "resourceType": "System",
        "resourceId": "sys-1"
    })
    assert res.status_code == 201
    spoofed_event = res.json()
    assert spoofed_event["actorId"] == "user-A" # RBAC should override this!

def test_rbac_admin_only_routes():
    # 6. user-A tries to hit admin routes
    res1 = user_client.get("/audit/verify")
    assert res1.status_code == 403

    res2 = user_client.get("/events/export")
    assert res2.status_code == 403
    
def test_rbac_unauthenticated_blocked():
    # 7. Unauthenticated hits
    res = anon_client.get("/events")
    assert res.status_code == 401
