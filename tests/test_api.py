import pytest
from fastapi.testclient import TestClient

from app.api import app, storage

# A test client lets us simulate HTTP requests to our FastAPI app
client = TestClient(app)

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

def test_verify_chain_intact():
    # Write a few events
    client.post("/events", json={"eventType": "LOGIN", "actorId": "user-A", "resourceType": "App", "resourceId": "app-1"})
    client.post("/events", json={"eventType": "LOGOUT", "actorId": "user-A", "resourceType": "App", "resourceId": "app-1"})
    
    response = client.get("/audit/verify")
    assert response.status_code == 200
    data = response.json()
    assert data["isValid"] is True
    assert data["message"] == "Chain is intact"

def test_verify_chain_broken():
    # Write events
    client.post("/events", json={"eventType": "LOGIN", "actorId": "user-A", "resourceType": "App", "resourceId": "app-1"})
    
    # Tamper with the database directly to break the chain
    events = storage.get_all_events()
    event_to_tamper = events[0]
    
    with storage._get_connection() as conn:
        conn.execute("UPDATE events SET payload = ? WHERE hash = ?", ('{"tampered": true}', event_to_tamper["hash"]))
        conn.commit()
        
    response = client.get("/audit/verify")
    data = response.json()
    
    assert data["isValid"] is False
    assert data["violationType"] == "TAMPERED_CONTENT"

