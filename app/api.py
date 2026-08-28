from fastapi import FastAPI, Query, Depends, Security, HTTPException, status, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, OAuth2PasswordRequestForm
from pydantic import BaseModel, Field, field_validator
from typing import Dict, Any, Optional
import json
import os
import jwt
from datetime import datetime, timedelta, timezone

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import cachetools

from app.storage import get_storage, StorageProvider
from app.service import AuditService
from app.crypto import CryptoService

app = FastAPI(title="Audit Log Service", description="Tamper-evident audit log prototype")

# CORS Setup: Restrictive origin policy
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://trusted-client.example.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
)

# Idempotency Cache (5 minute TTL)
idempotency_cache = cachetools.TTLCache(maxsize=10000, ttl=300)

def get_idempotency_key(idempotency_key: str = Header(..., alias="Idempotency-Key", description="Required to prevent replay attacks")):
    return idempotency_key

# Rate Limiting Setup
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Dependency Generators
def get_storage_provider() -> StorageProvider:
    return get_storage()

def get_audit_service(storage_provider: StorageProvider = Depends(get_storage_provider)) -> AuditService:
    return AuditService(storage_provider)

def get_crypto_service() -> CryptoService:
    return CryptoService()

# Authentication Setup
security = HTTPBearer()
API_TOKEN = os.environ.get("API_TOKEN")
if not API_TOKEN:
    raise RuntimeError("API_TOKEN environment variable is required")

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, API_TOKEN, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

@app.post("/auth/token", status_code=200)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Authentication API: Issues signed JWT tokens for users and admins.
    """
    # Issue Admin Token
    if form_data.username == "admin" and form_data.password == API_TOKEN:
        role = "admin"
        actor_id = "admin"
    # Issue User Token
    elif form_data.username != "admin" and form_data.password == "password":
        role = "user"
        actor_id = form_data.username
    else:
        raise HTTPException(status_code=400, detail="Incorrect username or password")

    # Create JWT
    expire = datetime.now(timezone.utc) + timedelta(hours=1)
    to_encode = {"sub": actor_id, "role": role, "actor_id": actor_id, "exp": expire}
    encoded_jwt = jwt.encode(to_encode, API_TOKEN, algorithm="HS256")
    
    return {"access_token": encoded_jwt, "token_type": "bearer"}

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

    @field_validator('payload')
    @classmethod
    def validate_payload_size(cls, v):
        payload_bytes = json.dumps(v).encode('utf-8')
        if len(payload_bytes) > 256 * 1024:  # 256 KB limit
            raise ValueError("Payload size exceeds the 256KB strict limit.")
        return v

@app.post("/events", status_code=201)
@limiter.limit("5/second")
def create_event(
    request: Request, 
    event_request: EventCreateRequest, 
    current_user: dict = Depends(get_current_user),
    idempotency_key: str = Depends(get_idempotency_key),
    service: AuditService = Depends(get_audit_service)
):
    """
    Write API: Accepts an event record, calculates hashes, and stores it in the append-only log.
    """
    if idempotency_key in idempotency_cache:
        raise HTTPException(status_code=409, detail="Duplicate Request: Idempotency-Key has already been used.")
    # Enforce RBAC: Users cannot spoof actorId
    if current_user["role"] == "user":
        event_request.actorId = current_user["actor_id"]

    # Convert Pydantic model to a raw dictionary
    event_dict = event_request.model_dump()
    
    # Let our service handle the timestamping, hashing, and storage
    saved_event = service.record_event(event_dict)
    
    # Store key in cache after successful processing
    idempotency_cache[idempotency_key] = True
    
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
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    current_user: dict = Depends(get_current_user),
    storage: StorageProvider = Depends(get_storage_provider)
):
    """
    Query API: Retrieve events with optional filtering.
    """
    filters = {}
    # Enforce RBAC: Users can only see their own events
    if current_user["role"] == "user":
        filters["actorId"] = current_user["actor_id"]
    elif actorId:
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
    limit: int = Query(10000, ge=1, le=100000, description="Max number of records to export"),
    current_user: dict = Depends(get_current_user),
    storage: StorageProvider = Depends(get_storage_provider),
    crypto_service: CryptoService = Depends(get_crypto_service)
):
    """
    Compliance Reporting API: Exports filtered events as a Cryptographically Signed JSON bundle.
    """
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required to export events")

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
def verify_chain(current_user: dict = Depends(get_current_user), service: AuditService = Depends(get_audit_service)):
    """
    Verification API: Walks the full chain and reports whether it is intact.
    """
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required to verify chain")
    return service.verify_chain()

@app.post("/events/{event_hash}/archive", status_code=200)
def archive_event(event_hash: str, current_user: dict = Depends(get_current_user), service: AuditService = Depends(get_audit_service)):
    """
    Retention Policy API: Soft-deletes the payload of an event.
    """
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required to archive events")
    
    success = service.archive_event(event_hash)
    if not success:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Event not found or already archived")
        
    return {"message": "Event archived successfully", "hash": event_hash}

@app.post("/events/{event_hash}/redact/{field_name}", status_code=200)
def redact_field(event_hash: str, field_name: str, current_user: dict = Depends(get_current_user), service: AuditService = Depends(get_audit_service)):
    """
    Cryptographic Erasure API: Permanently deletes the plaintext value of a sensitive field.
    The hashed representation remains in the payload to keep the chain intact.
    """
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required to redact fields")
    
    success = service.redact_field(event_hash, field_name)
    if not success:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Field not found or already redacted")
        
    return {"message": f"Field '{field_name}' redacted successfully", "hash": event_hash}
