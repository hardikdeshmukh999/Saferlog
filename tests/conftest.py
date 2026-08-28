import pytest
from app.storage import get_storage
from app.api import app, get_idempotency_key, get_storage_provider
import uuid
from tests.utils import test_storage

@pytest.fixture(autouse=True)
def clear_db():
    conn = test_storage._get_connection()
    if type(test_storage).__name__ == "PostgresStorage":
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE events, sensitive_payloads CASCADE")
        conn.commit()
    else:  # sqlite3
        conn.execute("DELETE FROM events")
        conn.execute("DELETE FROM sensitive_payloads")
        # reset auto increment
        conn.execute("DELETE FROM sqlite_sequence WHERE name='events'")
        conn.commit()

    # Disable the rate limiter so tests don't hit the 5/sec limit
    app.state.limiter.enabled = False
    
    # Automatically supply unique idempotency keys for all tests
    app.dependency_overrides[get_idempotency_key] = lambda: str(uuid.uuid4())
    # Supply singleton storage for all tests
    app.dependency_overrides[get_storage_provider] = lambda: test_storage
    
    yield
    
    # Clean up overrides after test
    app.dependency_overrides.clear()
