import pytest
import asyncio
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from app.main import app
from app.gateway.rate_limiter import rate_limiter

client = TestClient(app)

from app.config import settings

def test_admin_auth_required():
    # Attempting to access admin without key
    response = client.get("/api/metrics")
    assert response.status_code == 401 # Unauthorized

def test_admin_auth_success():
    # Admin with key
    response = client.get("/api/metrics", headers={"Authorization": f"Bearer {settings.admin_api_key}"})
    assert response.status_code == 200
    assert "total_requests" in response.json()

@pytest.mark.asyncio
async def test_rate_limiter_exceeded():
    # Mock redis to simulate exceeding rate limit
    with patch('app.gateway.rate_limiter.redis_client', new_callable=AsyncMock) as mock_redis:
        mock_redis.incr.return_value = 101 # Above 100 default
        
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as excinfo:
            await rate_limiter.check_rate_limit("test_user")
            
        assert excinfo.value.status_code == 429

@pytest.mark.asyncio
async def test_rate_limiter_fail_open():
    # If redis connection fails, it should fail open (allow request)
    with patch('app.gateway.rate_limiter.redis_client', new_callable=AsyncMock) as mock_redis:
        mock_redis.incr.side_effect = Exception("Redis Connection Error")
        
        # Should not raise exception
        await rate_limiter.check_rate_limit("test_user")
        assert True
        
@pytest.mark.asyncio
async def test_high_critical_verification_fail_closed():
    # Ensure that if verification throws an unexpected error, we do NOT silently bypass it.
    from app.verification.pipeline import verification_pipeline
    
    with patch('app.verification.pipeline.ClaimExtractor.extract', new_callable=AsyncMock) as mock_ext:
        mock_ext.side_effect = Exception("Verification Pipeline Crashing")
        
        # Extract will just catch the exception and return [] natively in our current implementation.
        # Wait, if it returns [], is_valid=True. This violates fail-closed!
        # Let's see if ClaimExtractor returning [] triggers fail-open.
        res = await verification_pipeline.verify_text("req-test", "Some claim")
        
        assert res["is_valid"] is False
        assert "SYSTEM_VERIFICATION_FAILURE" in res["contradicted_claims"]
