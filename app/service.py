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
        
        last_event = self.storage.get_last_event()
        last_hash = last_event["hash"] if last_event else self.GENESIS_HASH
            
        # 3. Get the deterministic bytes of the event
        c_hash = content_hash(canonical(event_data))
        r_hash = record_hash(last_hash, c_hash)

        event_data = {
            "eventType": event_data["eventType"],
            "actorId": event_data["actorId"],
            "resourceType": event_data["resourceType"],
            "resourceId": event_data["resourceId"],
            "payload": event_data.get("payload", {}),
            "timestamp": event_data.get("timestamp"),
            "previousHash": last_hash,
            "content_hash": c_hash,
            "hash": r_hash,
            "is_archived": 0
        }
        
        # 5. Save to the database
        self.storage.append_event(event_data)
        
        return event_data

    def archive_event(self, event_hash: str) -> bool:
        return self.storage.archive_event(event_hash)

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
            
            # Check 2: If not archived, verify that the payload matches the content_hash
            if not event.get("is_archived"):
                event_copy = event.copy()
                for key in ["hash", "content_hash", "is_archived", "previousHash"]:
                    if key in event_copy:
                        del event_copy[key]
                
                canonical_bytes = canonical(event_copy)
                c_hash = content_hash(canonical_bytes)
                
                if c_hash != event["content_hash"]:
                    return {
                        "isValid": False,
                        "brokenRecordId": event["hash"],
                        "violationType": "TAMPERED_PAYLOAD",
                        "message": "The payload does not match the stored content hash."
                    }
            
            # Check 3: Check record hash using stored content_hash
            recalculated_hash = record_hash(event["previousHash"], event["content_hash"])
            
            if event["hash"] != recalculated_hash:
                return {
                    "isValid": False,
                    "brokenRecordId": event["hash"],
                    "violationType": "TAMPERED_RECORD",
                    "message": "The calculated record hash does not match the stored hash."
                }
                
            expected_prev_hash = event["hash"]
            
        return {
            "isValid": True,
            "message": "Chain is intact"
        }
