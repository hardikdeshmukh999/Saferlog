import os
from unittest import mock
from app.storage import get_storage, PostgresStorage, SQLiteStorage

def test_get_storage_factory_postgres():
    """Test that the storage factory correctly instantiates PostgresStorage when DATABASE_URL is present."""
    with mock.patch.dict(os.environ, {"DATABASE_URL": "postgresql://user:pass@localhost/db"}):
        with mock.patch("psycopg2.connect"):
            storage = get_storage()
            assert isinstance(storage, PostgresStorage)

def test_get_storage_factory_sqlite():
    """Test that the storage factory correctly instantiates SQLiteStorage when DATABASE_URL is missing."""
    with mock.patch.dict(os.environ, {}, clear=True):
        storage = get_storage()
        assert isinstance(storage, SQLiteStorage)
