from app.chain import content_hash, record_hash

def test_content_hash():
    # Known canonical bytes
    canonical_bytes = b'{"a":1}'
    # The SHA-256 of '{"a":1}'
    expected = "015abd7f5cc57a2dd94b7590f04ad8084273905ee33ec5cebeae62276a97f862"
    assert content_hash(canonical_bytes) == expected

def test_record_hash():
    prev_hash = "0000000000000000000000000000000000000000000000000000000000000000"
    curr_content = "206b02a24fa68b200b3d819992f4dfdb9d5e396013a7c6f05b0d01f9ce020468"
    
    result = record_hash(prev_hash, curr_content)
    
    # Verify it produces a 64 char hex string (valid SHA-256 length)
    assert len(result) == 64
    assert result.isalnum()
