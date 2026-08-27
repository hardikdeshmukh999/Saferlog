import pytest
from app.storage import get_storage

@pytest.fixture(autouse=True)
def clear_db():
    storage = get_storage()
    conn = storage._get_connection()
    if hasattr(conn, "cursor"):  # psycopg2
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE events, sensitive_payloads CASCADE")
        conn.commit()
    else:  # sqlite3
        conn.execute("DELETE FROM events")
        conn.execute("DELETE FROM sensitive_payloads")
        conn.commit()
