import json

def canonical(value: dict) -> bytes:
    """
    Deterministically serializes a dictionary to a UTF-8 JSON byte string.
    Ensures keys are sorted and whitespace is stripped for consistent hashing.
    """
    return json.dumps(
        value,
        sort_keys=True,
        separators=(',', ':'),
        allow_nan=False,
        ensure_ascii=False
    ).encode('utf-8')
