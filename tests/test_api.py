import pytest
import os

os.environ["API_TOKEN"] = "supersecret"
os.environ["RSA_PASSPHRASE"] = "test-passphrase"
os.environ["DATA_ENCRYPTION_KEY"] = "tG6jmLlzfdGkKF3Y0Qpb0wYUYSAc0jIo2smsT8_TxfQ="

from fastapi.testclient import TestClient
from app.api import app, storage

client = TestClient(app, headers={"Authorization": "Bearer supersecret"})

@pytest.fixture(autouse=True)
def clean_database():
    """
    Since FastAPI uses the global 'storage' instance, we need to make sure 
    we clean it up before each test so tests don't interfere with each other.
    For this prototype, we'll just re-initialize the in-memory SQLite store.
    """
    storage.db_path = ":memory:"
    # Create a fresh new connection
    import sqlite3
    storage._conn = sqlite3.connect(":memory:", check_same_thread=False)
    storage._conn.row_factory = sqlite3.Row
    storage._init_db()
    yield

def test_create_event():
    response = client.post("/events", json={
        "eventType": "SYSTEM_START",
        "actorId": "admin",
        "resourceType": "System",
        "resourceId": "sys-0",
        "payload": {"version": "1.0"}
    })
    
    assert response.status_code == 201
    data = response.json()
    
    assert data["eventType"] == "SYSTEM_START"
    assert "timestamp" in data
    assert "hash" in data
    assert "previousHash" in data

def test_query_events():
    # Write a few events
    client.post("/events", json={
        "eventType": "LOGIN",
        "actorId": "user-A",
        "resourceType": "App",
        "resourceId": "app-1"
    })
    client.post("/events", json={
        "eventType": "LOGOUT",
        "actorId": "user-A",
        "resourceType": "App",
        "resourceId": "app-1"
    })
    client.post("/events", json={
        "eventType": "LOGIN",
        "actorId": "user-B",
        "resourceType": "App",
        "resourceId": "app-1"
    })
    
    # Query for user-A
    response = client.get("/events?actorId=user-A")
    assert response.status_code == 200
    data = response.json()
    
    assert len(data) == 2
    assert data[0]["eventType"] == "LOGIN"
    assert data[1]["eventType"] == "LOGOUT"
    
    # Query for eventType LOGIN
    response2 = client.get("/events?eventType=LOGIN")
    assert len(response2.json()) == 2

def test_query_pagination():
    # Insert 5 events
    for i in range(5):
        client.post("/events", json={
            "eventType": "TEST_PAGINATION",
            "actorId": f"user-{i}",
            "resourceType": "App",
            "resourceId": "app-1"
        })
        
    # Limit to 2
    response = client.get("/events?eventType=TEST_PAGINATION&limit=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["actorId"] == "user-0"
    assert data[1]["actorId"] == "user-1"
    
    # Offset by 2, limit to 2
    response2 = client.get("/events?eventType=TEST_PAGINATION&limit=2&offset=2")
    data2 = response2.json()
    assert len(data2) == 2
    assert data2[0]["actorId"] == "user-2"
    assert data2[1]["actorId"] == "user-3"

def test_verify_chain_intact():
    # Write a few events
    client.post("/events", json={"eventType": "LOGIN", "actorId": "user-A", "resourceType": "App", "resourceId": "app-1"})
    client.post("/events", json={"eventType": "LOGOUT", "actorId": "user-A", "resourceType": "App", "resourceId": "app-1"})
    
    response = client.get("/audit/verify")
    assert response.status_code == 200
    data = response.json()
    assert data["isValid"] is True, f"Failed: {data.get('message')} - {data.get('brokenRecordId')}"
    assert data["message"] == "Chain is intact"

def test_verify_chain_broken():
    # Write events
    client.post("/events", json={"eventType": "LOGIN", "actorId": "user-A", "resourceType": "App", "resourceId": "app-1"})
    
    # Tamper with the database directly to break the chain
    events = storage.get_all_events()
    event_to_tamper = events[0]
    
    with storage._get_connection() as conn:
        if hasattr(conn, "cursor"):
            with conn.cursor() as cur:
                cur.execute("UPDATE events SET payload = %s WHERE hash = %s", ('{"tampered": true}', event_to_tamper["hash"]))
            conn.commit()
        else:
            conn.execute("UPDATE events SET payload = ? WHERE hash = ?", ('{"tampered": true}', event_to_tamper["hash"]))
            conn.commit()
        
    response = client.get("/audit/verify")
    data = response.json()
    
    assert data["isValid"] is False
    assert data["violationType"] == "TAMPERED_PAYLOAD"


def test_archive_event():
    # 1. Create event
    response = client.post('/events', json={'eventType': 'LOGIN', 'actorId': 'user-A', 'resourceType': 'App', 'resourceId': 'app-2', 'payload': {'secret': '123'}})
    event_hash = response.json()['hash']
    
    # 2. Archive it
    arc_response = client.post(f'/events/{event_hash}/archive')
    assert arc_response.status_code == 200
    
    # 3. Query it (should be hidden)
    query_response = client.get('/events?resourceId=app-2')
    assert len(query_response.json()) == 0
    
    # 4. Verify chain (should still be intact despite missing payload)
    verify_response = client.get('/audit/verify')
    assert verify_response.json()['isValid'] is True


def test_structured_redaction():
    # 1. Create event with sensitive fields
    response = client.post('/events', json={
        'eventType': 'REGISTER', 
        'actorId': 'user-A', 
        'resourceType': 'App', 
        'resourceId': 'app-2', 
        'payload': {'public': 'hello', 'secret_ssn': '12345'},
        'sensitiveFields': ['secret_ssn']
    })
    event_hash = response.json()['hash']
    
    # 2. Query it (the raw value should be reassembled and visible!)
    query_response = client.get(f'/events?eventType=REGISTER')
    events = [e for e in query_response.json() if e['hash'] == event_hash]
    assert len(events) == 1
    assert events[0]['payload']['secret_ssn'] == '12345'
    assert events[0]['payload']['public'] == 'hello'
    
    # 3. Verify chain is intact
    verify_response = client.get('/audit/verify')
    assert verify_response.json()['isValid'] is True
    
    # 4. Redact the field
    redact_response = client.post(f'/events/{event_hash}/redact/secret_ssn')
    assert redact_response.status_code == 200
    
    # 5. Query it again (the raw value should be gone, only the hash remains)
    query_response2 = client.get(f'/events?eventType=REGISTER')
    events2 = [e for e in query_response2.json() if e['hash'] == event_hash]
    assert 'REDACTED:' in events2[0]['payload']['secret_ssn']
    assert events2[0]['payload']['public'] == 'hello'
    
    # 6. Verify chain is STILL intact
    verify_response2 = client.get('/audit/verify')
    assert verify_response2.json()['isValid'] is True

