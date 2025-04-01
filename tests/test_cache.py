import pytest
from httpx import AsyncClient
from fastapi import status
from datetime import datetime, timezone, timedelta
import time

@pytest.mark.asyncio
async def test_cache_redirect(test_client: AsyncClient):
    """Тест кэширования редиректов"""
    await test_client.post(
        "/api/v1/auth/register",
        json={
            "email": "cache@example.com",
            "password": "testpassword123",
            "username": "cacheuser"
        }
    )
    
    login_response = await test_client.post(
        "/api/v1/auth/jwt/login",
        data={
            "username": "cache@example.com",
            "password": "testpassword123"
        }
    )
    token = login_response.json()["access_token"]
    
    create_response = await test_client.post(
        "/api/v1/links/shorten",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "original_url": "https://example.com",
            "custom_alias": "cache-test"
        }
    )
    short_code = create_response.json()["short_url"].split("/")[-1]
    
    start_time = time.time()
    response1 = await test_client.get(f"/{short_code}", follow_redirects=False)
    first_request_time = time.time() - start_time
    
    assert response1.status_code == status.HTTP_307_TEMPORARY_REDIRECT
    assert response1.headers["location"] == "https://example.com"
    
    start_time = time.time()
    response2 = await test_client.get(f"/{short_code}", follow_redirects=False)
    second_request_time = time.time() - start_time
    
    assert response2.status_code == status.HTTP_307_TEMPORARY_REDIRECT
    assert response2.headers["location"] == "https://example.com"

    # assert second_request_time < first_request_time

@pytest.mark.asyncio
async def test_cache_invalidation(test_client: AsyncClient):
    """Тест инвалидации кэша при обновлении ссылки"""
    await test_client.post(
        "/api/v1/auth/register",
        json={
            "email": "invalidate@example.com",
            "password": "testpassword123",
            "username": "invalidateuser"
        }
    )
    
    login_response = await test_client.post(
        "/api/v1/auth/jwt/login",
        data={
            "username": "invalidate@example.com",
            "password": "testpassword123"
        }
    )
    token = login_response.json()["access_token"]
    
    create_response = await test_client.post(
        "/api/v1/links/shorten",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "original_url": "https://example1.com",
            "custom_alias": "invalidate-test"
        }
    )
    short_code = create_response.json()["short_url"].split("/")[-1]
    
    response1 = await test_client.get(f"/{short_code}", follow_redirects=False)
    assert response1.headers["location"] == "https://example1.com"
    
    await test_client.put(
        f"/api/v1/links/{short_code}",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "original_url": "https://example2.com"
        }
    )
    
    response2 = await test_client.get(f"/{short_code}", follow_redirects=False)
    assert response2.headers["location"] == "https://example2.com"

@pytest.mark.asyncio
async def test_cache_expiration(test_client: AsyncClient):
    """Тест истечения срока действия кэша"""
    await test_client.post(
        "/api/v1/auth/register",
        json={
            "email": "expire@example.com",
            "password": "testpassword123",
            "username": "expireuser"
        }
    )
    
    login_response = await test_client.post(
        "/api/v1/auth/jwt/login",
        data={
            "username": "expire@example.com",
            "password": "testpassword123"
        }
    )
    token = login_response.json()["access_token"]
    
    create_response = await test_client.post(
        "/api/v1/links/shorten",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "original_url": "https://example.com",
            "custom_alias": "expire-test",
            "expires_at": (datetime.now(timezone.utc) + timedelta(seconds=2)).isoformat()
        }
    )
    short_code = create_response.json()["short_url"].split("/")[-1]
    
    response1 = await test_client.get(f"/{short_code}", follow_redirects=False)
    assert response1.status_code == status.HTTP_307_TEMPORARY_REDIRECT
    
    time.sleep(3)
    
    response2 = await test_client.get(f"/{short_code}", follow_redirects=False)
    assert response2.status_code == status.HTTP_410_GONE 
