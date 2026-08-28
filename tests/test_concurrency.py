import pytest
import concurrent.futures
from fastapi.testclient import TestClient
from app.api import app
from tests.utils import test_storage as storage

anon_client = TestClient(app)
res_admin = anon_client.post("/auth/token", data={"username": "admin", "password": "supersecret"})
admin_token = res_admin.json()["access_token"]
client = TestClient(app, headers={"Authorization": f"Bearer {admin_token}"})

@pytest.fixture(autouse=True)
def clean_database():
    storage.db_path = ":memory:"
    import sqlite3
    # Use a higher timeout to let threads queue up waiting for the exclusive lock
    storage._conn = sqlite3.connect(":memory:", check_same_thread=False, timeout=15.0)
    storage._conn.row_factory = sqlite3.Row
    storage._init_db()
    
    # Disable rate limiter for this test
    app.state.limiter.enabled = False
    
    yield

def post_event(i):
    return client.post("/events", json={
        "eventType": "CONCURRENT_TEST",
        "actorId": "admin",
        "resourceType": "Thread",
        "resourceId": f"thread-{i}",
        "payload": {"thread_index": i}
    })

def test_atomic_appends_prevent_chain_forking():
    """
    Fires 50 simultaneous threads at the API to ensure that database locks 
    prevent the cryptographic hash chain from forking.
    """
    num_threads = 50
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(post_event, i) for i in range(num_threads)]
        
        results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
    # Verify all 50 events were successfully created without locking errors
    assert all(r.status_code == 201 for r in results), f"Some requests failed: {[r.text for r in results if r.status_code != 201]}"
    
    # Fetch all events from the API
    res = client.get("/events?limit=100")
    assert res.status_code == 200
    events = res.json()
    assert len(events) == num_threads
    
    # Mathematically prove the chain did not fork
    # The /audit/verify endpoint traverses the entire chain from Genesis to tip.
    # If two threads grabbed the same parent hash, the chain would branch, 
    # and verify would fail because it wouldn't form a single linear sequence.
    verify_res = client.get("/audit/verify")
    assert verify_res.status_code == 200
    assert verify_res.json()["isValid"] is True
