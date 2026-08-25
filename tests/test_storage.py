import pytest
from app.storage import SQLiteStorage

@pytest.fixture
def memory_db():
    # Use an in-memory SQLite database for testing
    storage = SQLiteStorage(db_path=":memory:")
    yield storage
    # In-memory DB is automatically destroyed when connection closes

def test_append_and_get_last_event(memory_db):
    event = {
        "eventType": "USER_LOGIN",
        "actorId": "user-123",
        "resourceType": "Account",
        "resourceId": "acc-456",
        "timestamp": "2026-08-25T10:00:00Z",
        "hash": "hash1",
        "previousHash": "genesis",
        "payload": {"ip": "127.0.0.1"}
    }
    
    # DB should initially be empty
    assert memory_db.get_last_event() is None
    
    memory_db.append_event(event)
    
    last_event = memory_db.get_last_event()
    assert last_event is not None
    assert last_event["actorId"] == "user-123"
    assert last_event["payload"] == {"ip": "127.0.0.1"}

def test_query_events(memory_db):
    event1 = {
        "eventType": "USER_LOGIN",
        "actorId": "user-123",
        "resourceType": "Account",
        "resourceId": "acc-456",
        "timestamp": "2026-08-25T10:00:00Z",
        "hash": "hash1",
        "previousHash": "genesis",
        "payload": {}
    }
    event2 = {
        "eventType": "FILE_DOWNLOAD",
        "actorId": "user-999",
        "resourceType": "File",
        "resourceId": "file-1",
        "timestamp": "2026-08-25T10:05:00Z",
        "hash": "hash2",
        "previousHash": "hash1",
        "payload": {}
    }
    
    memory_db.append_event(event1)
    memory_db.append_event(event2)
    
    # Query by actorId
    results = memory_db.query_events({"actorId": "user-123"})
    assert len(results) == 1
    assert results[0]["eventType"] == "USER_LOGIN"
    
    # Query by resourceType
    results = memory_db.query_events({"resourceType": "File"})
    assert len(results) == 1
    assert results[0]["actorId"] == "user-999"
    
    # Query matching none
    results = memory_db.query_events({"actorId": "nonexistent"})
    assert len(results) == 0
