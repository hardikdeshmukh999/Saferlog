import sqlite3
import json
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

class StorageProvider(ABC):
    @abstractmethod
    def append_event(self, event: Dict[str, Any]) -> None:
        pass

    @abstractmethod
    def get_last_event(self) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def query_events(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_all_events(self) -> List[Dict[str, Any]]:
        pass

class SQLiteStorage(StorageProvider):
    def __init__(self, db_path: str = "audit.db"):
        self.db_path = db_path
        # Use check_same_thread=False for easy testing and async usage later.
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_db()

    def _get_connection(self):
        return self._conn

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    actor_id TEXT NOT NULL,
                    resource_type TEXT NOT NULL,
                    resource_id TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    hash TEXT NOT NULL UNIQUE,
                    previous_hash TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    payload TEXT,
                    is_archived INTEGER DEFAULT 0
                )
            ''')
            # Create indexes for faster querying
            conn.execute('CREATE INDEX IF NOT EXISTS idx_actor ON events(actor_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_resource ON events(resource_type, resource_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_event_type ON events(event_type)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON events(timestamp)')
            conn.commit()

    def append_event(self, event_dict: Dict[str, Any]) -> None:
        with self._get_connection() as conn:
            conn.execute('''
                INSERT INTO events (
                    event_type, actor_id, resource_type, resource_id, 
                    timestamp, hash, previous_hash, content_hash, payload, is_archived
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                event_dict["eventType"],
                event_dict["actorId"],
                event_dict["resourceType"],
                event_dict["resourceId"],
                event_dict["timestamp"],
                event_dict["hash"],
                event_dict["previousHash"],
                event_dict["content_hash"],
                json.dumps(event_dict.get("payload", {})) if event_dict.get("payload") is not None else None,
                event_dict.get("is_archived", 0)
            ))
            conn.commit()

    def get_last_event(self) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.execute('SELECT * FROM events ORDER BY id DESC LIMIT 1')
            row = cursor.fetchone()
            
            if not row:
                return None
                
            return self._row_to_dict(row)

    def archive_event(self, event_hash: str) -> bool:
        """
        Soft-deletes the payload of an event by setting is_archived=1 and payload=NULL
        """
        with self._get_connection() as conn:
            cursor = conn.execute('''
                UPDATE events 
                SET is_archived = 1, payload = NULL 
                WHERE hash = ? AND is_archived = 0
            ''', (event_hash,))
            conn.commit()
            return cursor.rowcount > 0

    def query_events(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        query = 'SELECT * FROM events WHERE is_archived = 0'
        params = []

        if "actorId" in filters:
            query += ' AND actor_id = ?'
            params.append(filters["actorId"])
        
        if "resourceType" in filters:
            query += ' AND resource_type = ?'
            params.append(filters["resourceType"])
            
        if "resourceId" in filters:
            query += ' AND resource_id = ?'
            params.append(filters["resourceId"])
            
        if "eventType" in filters:
            query += ' AND event_type = ?'
            params.append(filters["eventType"])
            
        if "from_time" in filters:
            query += ' AND timestamp >= ?'
            params.append(filters["from_time"])
            
        if "to_time" in filters:
            query += ' AND timestamp <= ?'
            params.append(filters["to_time"])
        
        # Ensure consistent ordering for pagination
        query += ' ORDER BY id ASC'
            
        if "limit" in filters:
            query += ' LIMIT ?'
            params.append(filters["limit"])
            
        if "offset" in filters:
            query += ' OFFSET ?'
            params.append(filters["offset"])
            
        with self._get_connection() as conn:
            cursor = conn.execute(query, params)
            return [self._row_to_dict(row) for row in cursor.fetchall()]

    def get_all_events(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.execute('SELECT * FROM events ORDER BY id ASC')
            return [self._row_to_dict(row) for row in cursor.fetchall()]

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        result = {
            "eventType": row["event_type"],
            "actorId": row["actor_id"],
            "resourceType": row["resource_type"],
            "resourceId": row["resource_id"],
            "timestamp": row["timestamp"],
            "hash": row["hash"],
            "previousHash": row["previous_hash"],
            "content_hash": row["content_hash"],
            "is_archived": bool(row["is_archived"])
        }
        
        # Only include payload if it exists (not archived/deleted)
        if row["payload"] is not None:
            result["payload"] = json.loads(row["payload"])
            
        return result
