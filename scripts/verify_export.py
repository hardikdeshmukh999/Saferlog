import sys
sys.path.insert(0, ".")
import sys
import json
import base64
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes, serialization

def verify_export_bundle(bundle_path: str):
    """
    Reads an exported JSON bundle and mathematically verifies its cryptographic signature
    using the provided public key.
    """
    try:
        with open(bundle_path, 'r') as f:
            bundle = json.load(f)
    except Exception as e:
        print(f"[-] Error reading bundle file: {e}")
        sys.exit(1)

    if not all(k in bundle for k in ("events", "signature", "public_key")):
        print("[-] Invalid bundle format. Missing required fields.")
        sys.exit(1)

    events = bundle["events"]
    signature_b64 = bundle["signature"]
    public_key_pem = bundle["public_key"]

    # 1. Reconstruct the exact deterministic bytes that were signed
    events_json_str = json.dumps(events, separators=(',', ':'), sort_keys=True)
    events_bytes = events_json_str.encode('utf-8')

    # 2. Decode the signature
    try:
        signature = base64.b64decode(signature_b64)
    except Exception as e:
        print(f"[-] Error decoding signature: {e}")
        sys.exit(1)

    # 3. Load the Public Key
    try:
        public_key = serialization.load_pem_public_key(public_key_pem.encode('utf-8'))
    except Exception as e:
        print(f"[-] Error loading public key: {e}")
        sys.exit(1)

    # 4. Verify
    try:
        public_key.verify(
            signature,
            events_bytes,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        print("[+] SUCCESS: The export bundle signature is VALID.")
        print(f"    The bundle contains {len(events)} untampered events.")
        print(f"    This data definitively originated from the Saferlog system.")
    except Exception:
        print("[-] FAILURE: The export bundle signature is INVALID.")
        print("    The data has been tampered with or did not originate from Saferlog!")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python verify_export.py <path_to_export_bundle.json>")
        sys.exit(1)
        
    verify_export_bundle(sys.argv[1])
