import hashlib

def content_hash(canonical_bytes: bytes) -> str:
    """
    Returns the SHA-256 hex string (64 characters) of the given canonical bytes.
    """
    return hashlib.sha256(canonical_bytes).hexdigest()

def record_hash(prev_hash: str, current_content_hash: str) -> str:
    """
    Combines the previous hash and the current content hash, 
    and returns the SHA-256 hex string of the result.
    This creates the tamper-evident chain link.
    """
    # We combine them by simply concatenating the two hex strings and hashing the result.
    # Alternatively, you could concatenate their raw bytes, but concatenating hex strings 
    # and encoding to utf-8 is completely deterministic and standard.
    combined = (prev_hash + current_content_hash).encode('utf-8')
    return hashlib.sha256(combined).hexdigest()
