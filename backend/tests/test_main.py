import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.cache.exact_cache import generate_cache_key

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_cache_key_generation():
    key1 = generate_cache_key("hello world", "model1", "v1", 0.5, "v1")
    key2 = generate_cache_key("Hello World ", "model1", "v1", 0.5, "v1")
    assert key1 == key2
