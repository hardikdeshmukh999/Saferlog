from fastapi import FastAPI, Query
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
import json

from app.storage import SQLiteStorage
from app.service import AuditService
from app.crypto import CryptoService

app = FastAPI(title="Audit Log Service", description="Tamper-evident audit log prototype")

# Initialize our core components
storage = SQLiteStorage()
service = AuditService(storage)
crypto_service = CryptoService()

class EventCreateRequest(BaseModel):
    """
    The shape of the data we expect from the client when writing a new event.
    """
    eventType: str = Field(..., json_schema_extra={"example": "USER_LOGIN"})
    actorId: str = Field(..., json_schema_extra={"example": "user-123"})
    resourceType: str = Field(..., json_schema_extra={"example": "Account"})
    resourceId: str = Field(..., json_schema_extra={"example": "acc-456"})
    payload: Dict[str, Any] = Field(default_factory=dict, json_schema_extra={"example": {"ip": "127.0.0.1", "ssn": "123-45-678"}})
    sensitiveFields: Optional[list[str]] = Field(None, json_schema_extra={"example": ["ssn"]}, description="List of keys in the payload to cryptographically erase later")

@app.post("/events", status_code=201)
def create_event(request: EventCreateRequest):
    """
    Write API: Accepts an event record, calculates hashes, and stores it in the append-only log.
    """
    # Convert Pydantic model to a raw dictionary
    event_dict = request.model_dump()
    
    # Let our service handle the timestamping, hashing, and storage
    saved_event = service.record_event(event_dict)
    
    return saved_event

@app.get("/events")
def query_events(
    actorId: Optional[str] = None,
    resourceType: Optional[str] = None,
    resourceId: Optional[str] = None,
    eventType: Optional[str] = None,
    from_time: Optional[float] = None,
    to_time: Optional[float] = None,
    limit: int = Query(50, ge=1, le=1000, description="Max number of records to return"),
    offset: int = Query(0, ge=0, description="Number of records to skip")
):
    """
    Query API: Retrieve events with optional filtering.
    """
    filters = {}
    if actorId:
        filters["actorId"] = actorId
    if resourceType:
        filters["resourceType"] = resourceType
    if resourceId:
        filters["resourceId"] = resourceId
    if eventType:
        filters["eventType"] = eventType
    if from_time:
        filters["from_time"] = from_time
    if to_time:
        filters["to_time"] = to_time
        
    filters["limit"] = limit
    filters["offset"] = offset
        
    return storage.query_events(filters)

@app.get("/events/export")
def export_events(
    actorId: Optional[str] = None,
    resourceType: Optional[str] = None,
    resourceId: Optional[str] = None,
    eventType: Optional[str] = None,
    from_time: Optional[float] = None,
    to_time: Optional[float] = None,
    limit: int = Query(10000, ge=1, le=100000, description="Max number of records to export")
):
    """
    Compliance Reporting API: Exports filtered events as a Cryptographically Signed JSON bundle.
    """
    filters = {}
    if actorId:
        filters["actorId"] = actorId
    if resourceType:
        filters["resourceType"] = resourceType
    if resourceId:
        filters["resourceId"] = resourceId
    if eventType:
        filters["eventType"] = eventType
    if from_time:
        filters["from_time"] = from_time
    if to_time:
        filters["to_time"] = to_time
        
    filters["limit"] = limit
    filters["offset"] = 0
    
    events = storage.query_events(filters)
    
    # Serialize events deterministically so the signature is stable
    events_json_str = json.dumps(events, separators=(',', ':'), sort_keys=True)
    events_bytes = events_json_str.encode('utf-8')
    
    # Sign the JSON string
    signature = crypto_service.sign_data(events_bytes)
    
    return {
        "events": events,
        "signature": signature,
        "public_key": crypto_service.get_public_key_pem()
    }

@app.get("/audit/verify")
def verify_chain():
    """
    Verification API: Walks the full chain and reports whether it is intact.
    """
    return service.verify_chain()

@app.post("/events/{event_hash}/archive", status_code=200)
def archive_event(event_hash: str):
    """
    Retention Policy API: Soft-deletes the payload of an event.
    """
    success = service.archive_event(event_hash)
    if not success:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Event not found or already archived")
        
    return {"message": "Event archived successfully", "hash": event_hash}

@app.post("/events/{event_hash}/redact/{field_name}", status_code=200)
def redact_field(event_hash: str, field_name: str):
    """
    Cryptographic Erasure API: Permanently deletes the plaintext value of a sensitive field.
    The hashed representation remains in the payload to keep the chain intact.
    """
    success = service.redact_field(event_hash, field_name)
    if not success:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Field not found or already redacted")
        
    return {"message": f"Field '{field_name}' redacted successfully", "hash": event_hash}
