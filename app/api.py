from fastapi import FastAPI, Query
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

from app.storage import SQLiteStorage
from app.service import AuditService

app = FastAPI(title="Audit Log Service", description="Tamper-evident audit log prototype")

# Initialize our core components
storage = SQLiteStorage()
service = AuditService(storage)

class EventCreateRequest(BaseModel):
    """
    The shape of the data we expect from the client when writing a new event.
    """
    eventType: str = Field(..., json_schema_extra={"example": "USER_LOGIN"})
    actorId: str = Field(..., json_schema_extra={"example": "user-123"})
    resourceType: str = Field(..., json_schema_extra={"example": "Account"})
    resourceId: str = Field(..., json_schema_extra={"example": "acc-456"})
    payload: Dict[str, Any] = Field(default_factory=dict, json_schema_extra={"example": {"ip": "127.0.0.1"}})

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
    from_time: Optional[str] = Query(None, description="ISO-8601 timestamp (e.g. 2026-08-25T10:00:00Z)"),
    to_time: Optional[str] = Query(None, description="ISO-8601 timestamp")
):
    """
    Query API: Retrieve events with filtering.
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
        
    return storage.query_events(filters)
