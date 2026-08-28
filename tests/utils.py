from app.storage import get_storage

# Singleton storage for tests so data persists across multiple requests in the same test
test_storage = get_storage()
