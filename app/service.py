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

    def verify_chain(self) -> Dict[str, Any]:
        """
        Walks the full chain and reports whether it is intact.
        If broken, reports which record failed and why.
        """
        events = self.storage.get_all_events()
        expected_prev_hash = self.GENESIS_HASH
        
        for event in events:
            # Check 1: Does the previousHash match the actual previous hash?
            if event["previousHash"] != expected_prev_hash:
                return {
                    "isValid": False,
                    "brokenRecordId": event.get("hash", "UNKNOWN"),
                    "violationType": "BROKEN_LINK",
                    "message": f"Expected previousHash {expected_prev_hash} but got {event['previousHash']}."
                }
            
            # Check 2: Does the content hash match the payload?
            event_copy = event.copy()
            if "hash" in event_copy:
                del event_copy["hash"]
            
            canonical_bytes = canonical(event_copy)
            c_hash = content_hash(canonical_bytes)
            recalculated_hash = record_hash(event["previousHash"], c_hash)
            
            if event["hash"] != recalculated_hash:
                return {
                    "isValid": False,
                    "brokenRecordId": event["hash"],
                    "violationType": "TAMPERED_CONTENT",
                    "message": "The calculated hash does not match the stored hash."
                }
                
            expected_prev_hash = event["hash"]
            
        return {
            "isValid": True,
            "message": "Chain is intact"
        }
