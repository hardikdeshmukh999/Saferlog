import sys
sys.path.insert(0, ".")

import json
import os
os.environ["API_TOKEN"] = "supersecret"
os.environ["RSA_PASSPHRASE"] = "test-passphrase"

from app.api import app
from fastapi.testclient import TestClient
from verify_export import verify_export_bundle

client = TestClient(app, headers={"Authorization": "Bearer supersecret"})
print('1. Exporting bundle from API...')
response = client.get('/events/export')
with open('test_export_local.json', 'w') as f:
    json.dump(response.json(), f)

print('2. Running verification script...')
verify_export_bundle('test_export_local.json')

