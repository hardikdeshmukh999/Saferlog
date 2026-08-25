import pytest
from app.service import AuditService
from app.storage import SQLiteStorage

@pytest.fixture
def memory_db():
    return SQLiteStorage(db_path=":memory:")

@pytest.fixture
def service(memory_db):
    return AuditService(storage=memory_db)

def test_record_first_event(service):
    raw_event = {
        "eventType": "USER_LOGIN",
        "actorId": "user-1",
        "resourceType": "System",
        "resourceId": "sys-1",
        "payload": {"ip": "127.0.0.1"}
    }
    
    saved_event = service.record_event(raw_event)
    
    # Check that service added the missing fields
    assert "timestamp" in saved_event
    assert "hash" in saved_event
    assert saved_event["previousHash"] == service.GENESIS_HASH
    
    # Check that it actually went to the DB
    db_event = service.storage.get_last_event()
    assert db_event["hash"] == saved_event["hash"]

def test_record_multiple_events_chains_hashes(service):
    event1 = {
        "eventType": "USER_LOGIN",
        "actorId": "user-1",
        "resourceType": "System",
        "resourceId": "sys-1",
        "payload": {}
    }
    
    event2 = {
        "eventType": "FILE_DOWNLOAD",
        "actorId": "user-1",
        "resourceType": "File",
        "resourceId": "file-xyz",
        "payload": {}
    }
    
    saved_event1 = service.record_event(event1)
    saved_event2 = service.record_event(event2)
    
    # The second event's previousHash must equal the first event's final hash
    assert saved_event2["previousHash"] == saved_event1["hash"]
    
    # Confirm DB agrees
    results = service.storage.query_events({"actorId": "user-1"})
    assert len(results) == 2
    assert results[1]["previousHash"] == results[0]["hash"]
