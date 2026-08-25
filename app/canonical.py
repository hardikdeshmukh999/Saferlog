from datetime import datetime, timezone
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

def default_timestamp() -> datetime:
    """Returns the current UTC time."""
    return datetime.now(timezone.utc)

class AuditEvent(BaseModel):
    """
    Canonical representation of an Audit Event.
    """
    eventType: str = Field(..., description="What happened (e.g., USER_LOGIN)")
    actorId: str = Field(..., description="Who or what caused the event")
    resourceType: str = Field(..., description="The type of resource affected")
    resourceId: str = Field(..., description="The specific resource affected")
    payload: Dict[str, Any] = Field(..., description="A structured object with event-specific detail")
    
    # The server assigns the timestamp when the event is constructed.
    timestamp: datetime = Field(default_factory=default_timestamp, description="When the event occurred")
    
    # Hash fields for the tamper-evident chain. 
    # These will be populated by the hashing utility before storage.
    hash: Optional[str] = Field(None, description="Hash of this event's content")
    previousHash: Optional[str] = Field(None, description="Hash of the immediately preceding record")
