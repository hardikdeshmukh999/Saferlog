import pytest
from datetime import datetime, timezone
from pydantic import ValidationError
from app.canonical import AuditEvent

def test_audit_event_creation():
    event = AuditEvent(
        eventType="USER_LOGIN",
        actorId="user-123",
        resourceType="Account",
        resourceId="acc-456",
        payload={"ip": "127.0.0.1"}
    )
    
    assert event.eventType == "USER_LOGIN"
    assert event.actorId == "user-123"
    assert event.resourceType == "Account"
    assert event.resourceId == "acc-456"
    assert event.payload == {"ip": "127.0.0.1"}
    # Timestamp should be auto-assigned
    assert isinstance(event.timestamp, datetime)

def test_audit_event_validation_missing_fields():
    with pytest.raises(ValidationError):
        # Missing actorId
        AuditEvent(
            eventType="USER_LOGIN",
            resourceType="Account",
            resourceId="acc-456",
            payload={}
        )
