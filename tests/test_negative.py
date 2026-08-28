import pytest
from fastapi.testclient import TestClient
import jwt
import os
from datetime import datetime, timedelta, timezone

from app.api import app

client = TestClient(app)

@pytest.fixture(autouse=True)
def disable_rate_limiter():
    app.state.limiter.enabled = False
    yield

@pytest.mark.parametrize("invalid_token", [
    # 1. Completely garbage string
    "Bearer this_is_not_a_jwt",
    # 2. Correctly formatted JWT, but signed with the wrong secret key
    f"Bearer {jwt.encode({'sub': 'admin', 'role': 'admin'}, 'WRONG_SECRET', algorithm='HS256')}",
    # 3. Correctly formatted JWT, signed with the correct key, but expired
    f"Bearer {jwt.encode({'sub': 'admin', 'role': 'admin', 'exp': datetime.now(timezone.utc) - timedelta(hours=1)}, os.environ['API_TOKEN'], algorithm='HS256')}",
    # 4. No token at all
    ""
])
def test_reject_invalid_jwts(invalid_token):
    headers = {"Authorization": invalid_token} if invalid_token else {}
    response = client.post("/events", headers=headers, json={
        "eventType": "HACK_ATTEMPT",
        "actorId": "hacker",
        "resourceType": "System",
        "resourceId": "sys-0",
        "payload": {}
    })
    
    # Fast API's HTTPBearer and JWT exception handlers should return 401 or 403
    assert response.status_code in (401, 403)


@pytest.mark.parametrize("payload_size", [
    256 * 1024 + 1,  # Just over 256KB
    500 * 1024       # 500KB
])
def test_reject_oversized_payloads(payload_size):
    res_admin = client.post("/auth/token", data={"username": "admin", "password": "supersecret"})
    admin_token = res_admin.json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {admin_token}"}
    
    massive_string = "A" * payload_size
    
    response = client.post("/events", headers=auth_headers, json={
        "eventType": "MASSIVE_UPLOAD",
        "actorId": "admin",
        "resourceType": "System",
        "resourceId": "sys-0",
        "payload": {"data": massive_string}
    })
    
    assert response.status_code == 422
    assert "Payload size exceeds the 256KB strict limit" in response.text

def test_idempotency_prevents_replay():
    res_admin = client.post("/auth/token", data={"username": "admin", "password": "supersecret"})
    admin_token = res_admin.json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {admin_token}", "Idempotency-Key": "test-replay-key-123"}
    
    # Temporarily remove the conftest.py override so it respects our header
    from app.api import get_idempotency_key
    if get_idempotency_key in app.dependency_overrides:
        del app.dependency_overrides[get_idempotency_key]
        
    payload = {
        "eventType": "REPLAY_ATTACK",
        "actorId": "admin",
        "resourceType": "System",
        "resourceId": "sys-0",
        "payload": {"data": "test"}
    }
    
    # First request should succeed
    response1 = client.post("/events", headers=auth_headers, json=payload)
    assert response1.status_code == 201
    
    # Second request with the SAME Idempotency-Key should be blocked
    response2 = client.post("/events", headers=auth_headers, json=payload)
    assert response2.status_code == 409
    assert "Duplicate Request" in response2.text
    
    # Missing Idempotency-Key should be blocked by FastAPI validation (422 Unprocessable Entity)
    auth_headers_missing = {"Authorization": f"Bearer {admin_token}"}
    response3 = client.post("/events", headers=auth_headers_missing, json=payload)
    assert response3.status_code == 422
