from datetime import datetime, timezone
from typing import Dict, Any

from app.storage import StorageProvider
from app.canonical import canonical
from app.chain import content_hash, record_hash

class AuditService:
    def __init__(self, storage: StorageProvider):
        self.storage = storage
        # 64 zeros as the starting point of our hash chain
        self.GENESIS_HASH = "0000000000000000000000000000000000000000000000000000000000000000"

    def record_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Takes a raw event dictionary, assigns a server timestamp, 
        calculates the hash chain, and stores it.
        """
        # 1. Assign server timestamp
        event_data["timestamp"] = datetime.now(timezone.utc).isoformat()
        
        # 2. Find the previous link in the chain
        last_event = self.storage.get_last_event()
        if last_event:
            prev_hash = last_event["hash"]
        else:
            prev_hash = self.GENESIS_HASH
            
        event_data["previousHash"] = prev_hash
        
        # 3. Get the deterministic bytes of the event
        # (It doesn't have a 'hash' key yet, which is perfect)
        canonical_bytes = canonical(event_data)
        
        # 4. Calculate the hashes
        c_hash = content_hash(canonical_bytes)
        final_hash = record_hash(prev_hash, c_hash)
        
        event_data["hash"] = final_hash
        
        # 5. Save to the database
        self.storage.append_event(event_data)
        
        return event_data
