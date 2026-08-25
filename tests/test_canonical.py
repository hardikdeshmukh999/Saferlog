from app.canonical import canonical

def test_canonical_sorts_keys():
    data1 = {"b": 2, "a": 1}
    data2 = {"a": 1, "b": 2}
    
    # Even though keys are inserted in different orders, the canonical bytes must be exactly the same
    assert canonical(data1) == canonical(data2)
    assert canonical(data1) == b'{"a":1,"b":2}'

def test_canonical_removes_whitespace():
    data = {"hello": "world", "number": 42}
    result = canonical(data)
    # Ensure no spaces around colons or commas
    assert result == b'{"hello":"world","number":42}'

def test_canonical_ensure_ascii_false():
    # If a payload contains non-ascii characters, we want them preserved as raw utf-8, not escaped
    data = {"emoji": "🚀"}
    result = canonical(data)
    assert b"\\u" not in result
    assert result == b'{"emoji":"\xf0\x9f\x9a\x80"}'
