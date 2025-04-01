import pytest
from httpx import AsyncClient
from fastapi import status
from datetime import datetime, timezone, timedelta
import asyncio
from sqlalchemy import select, Select
from app.models.link import Link
from app.core.security import create_access_token
from app.core.config import settings
from sqlalchemy.ext.asyncio import AsyncSession

@pytest.mark.parametrize(
    "payload, error_detail_part",
    [
        ({"email": "invalid-email", "password": "password123", "username": "user1"}, "value is not a valid email address"),
        ({"email": "test@example.com", "password": "short", "username": "user2"}, "String should have at least 8 characters"),
        ({"email": "test3@example.com", "password": "password123"}, "Field required"), # Missing username
        ({"password": "password123", "username": "user4"}, "Field required"), # Missing email
        ({"email": "test5@example.com", "username": "user5"}, "Field required"), # Missing password
    ]
)
@pytest.mark.asyncio
async def test_register_user_invalid_input(test_client: AsyncClient, payload: dict, error_detail_part: str):
    """Тест регистрации пользователя с невалидными данными (ошибка 422)."""
    response = await test_client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert error_detail_part in response.text # Проверяем наличие части ожидаемой ошибки в теле ответа

@pytest.mark.asyncio
async def test_register_user(test_client: AsyncClient):
    """Тест регистрации нового пользователя"""
    response = await test_client.post(
        "/api/v1/auth/register",
        json={
            "email": "new_test_user@example.com",
            "password": "testpassword123",
            "username": "newtestuser"
        }
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["email"] == "new_test_user@example.com"
    assert data["username"] == "newtestuser"
    assert "id" in data

@pytest.mark.asyncio
async def test_login_user(test_client: AsyncClient):
    """Тест входа пользователя и проверка токена через /users/me."""
    email = "login_check@example.com"
    password = "testpassword123"
    username = "logincheckuser"
    await test_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "username": username}
    )
    
    response_login = await test_client.post(
        "/api/v1/auth/jwt/login",
        data={"username": email, "password": password}
    )
    assert response_login.status_code == status.HTTP_200_OK
    data_login = response_login.json()
    assert "access_token" in data_login
    assert data_login["token_type"] == "bearer"
    token = data_login["access_token"]
    
    response_me = await test_client.get(
        "/api/v1/auth/users/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response_me.status_code == status.HTTP_200_OK
    data_me = response_me.json()
    assert data_me["email"] == email
    assert data_me["username"] == username

# Тесты для работы со ссылками
@pytest.mark.asyncio
async def test_create_short_link(test_client: AsyncClient):
    """Тест создания короткой ссылки"""
    await test_client.post(
        "/api/v1/auth/register",
        json={
            "email": "link@example.com",
            "password": "testpassword123",
            "username": "linkuser"
        }
    )
    
    login_response = await test_client.post(
        "/api/v1/auth/jwt/login",
        data={
            "username": "link@example.com",
            "password": "testpassword123"
        }
    )
    token = login_response.json()["access_token"]
    
    response = await test_client.post(
        "/api/v1/links/shorten",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "original_url": "https://example.com",
            "custom_alias": "test-link",
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
        }
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert "short_url" in data
    assert data["short_url"].endswith("/test-link")

@pytest.mark.asyncio
async def test_create_short_link_no_alias(test_client: AsyncClient):
    """Тест создания короткой ссылки без указания custom_alias."""
    email = "noalias@example.com"
    password = "testpassword123"
    username = "noaliasuser"
    await test_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "username": username}
    )
    login_response = await test_client.post(
        "/api/v1/auth/jwt/login",
        data={"username": email, "password": password}
    )
    token = login_response.json()["access_token"]

    original_url = "https://generate-code.com"
    response = await test_client.post(
        "/api/v1/links/shorten",
        headers={"Authorization": f"Bearer {token}"},
        json={"original_url": original_url}
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()

    assert data["original_url"] == original_url
    assert data["custom_alias"] is None
    assert data["short_code"] is not None
    assert len(data["short_code"]) == 6
    assert data["short_url"] is not None
    assert data["short_url"].endswith(data["short_code"])

@pytest.mark.asyncio
async def test_get_link_stats(test_client: AsyncClient):
    """Тест получения статистики по ссылке"""
    await test_client.post(
        "/api/v1/auth/register",
        json={
            "email": "stats@example.com",
            "password": "testpassword123",
            "username": "statsuser"
        }
    )
    
    login_response = await test_client.post(
        "/api/v1/auth/jwt/login",
        data={
            "username": "stats@example.com",
            "password": "testpassword123"
        }
    )
    token = login_response.json()["access_token"]
    
    create_response = await test_client.post(
        "/api/v1/links/shorten",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "original_url": "https://example.com",
            "custom_alias": "stats-link"
        }
    )
    short_code = create_response.json()["short_url"].split("/")[-1]
    
    response = await test_client.get(
        f"/api/v1/links/{short_code}/stats",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["original_url"] == "https://example.com"
    assert "clicks" in data
    assert data["clicks"] == 0
    assert data["short_url"] is not None

@pytest.mark.asyncio
async def test_get_link_stats_not_found(test_client: AsyncClient):
    """Тест получения статистики для несуществующей ссылки (404)."""
    email = "stats_notfound@example.com"
    password = "testpassword123"
    await test_client.post("/api/v1/auth/register", json={"email": email, "password": password, "username": "statsnotfounduser"})
    login_resp = await test_client.post("/api/v1/auth/jwt/login", data={"username": email, "password": password})
    token = login_resp.json()["access_token"]

    response = await test_client.get(
        "/api/v1/links/nonexistent-stats-link/stats",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND

@pytest.mark.asyncio
async def test_redirect_short_link(test_client: AsyncClient):
    """Тест перенаправления по короткой ссылке"""
    await test_client.post(
        "/api/v1/auth/register",
        json={
            "email": "redirect@example.com",
            "password": "testpassword123",
            "username": "redirectuser"
        }
    )
    
    login_response = await test_client.post(
        "/api/v1/auth/jwt/login",
        data={
            "username": "redirect@example.com",
            "password": "testpassword123"
        }
    )
    token = login_response.json()["access_token"]
    
    create_response = await test_client.post(
        "/api/v1/links/shorten",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "original_url": "https://example.com",
            "custom_alias": "redirect-link"
        }
    )
    short_code = create_response.json()["short_url"].split("/")[-1]
    
    response = await test_client.get(f"/{short_code}", follow_redirects=False)
    assert response.status_code == status.HTTP_307_TEMPORARY_REDIRECT
    assert response.headers["location"] == "https://example.com"

    stats_response = await test_client.get(
        f"/api/v1/links/{short_code}/stats",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert stats_response.status_code == status.HTTP_200_OK
    assert stats_response.json()["clicks"] == 1

@pytest.mark.asyncio
async def test_delete_link(test_client: AsyncClient):
    """Тест удаления ссылки"""
    await test_client.post(
        "/api/v1/auth/register",
        json={
            "email": "delete@example.com",
            "password": "testpassword123",
            "username": "deleteuser"
        }
    )
    
    login_response = await test_client.post(
        "/api/v1/auth/jwt/login",
        data={
            "username": "delete@example.com",
            "password": "testpassword123"
        }
    )
    token = login_response.json()["access_token"]
    
    create_response = await test_client.post(
        "/api/v1/links/shorten",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "original_url": "https://example.com",
            "custom_alias": "delete-link"
        }
    )
    short_code = create_response.json()["short_url"].split("/")[-1]
    
    response = await test_client.delete(
        f"/api/v1/links/{short_code}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT
    
    stats_response = await test_client.get(
        f"/api/v1/links/{short_code}/stats",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert stats_response.status_code == status.HTTP_404_NOT_FOUND

@pytest.mark.asyncio
async def test_register_existing_user(test_client: AsyncClient):
    """Тест регистрации пользователя с уже существующим email (ошибка 400)."""
    payload = {
        "email": "existing@example.com",
        "password": "password123",
        "username": "existinguser"
    }
    response1 = await test_client.post("/api/v1/auth/register", json=payload)
    assert response1.status_code == status.HTTP_201_CREATED

    response2 = await test_client.post("/api/v1/auth/register", json=payload)
    assert response2.status_code == status.HTTP_400_BAD_REQUEST
    assert "Email already registered" in response2.json()["detail"]

@pytest.mark.asyncio
async def test_login_invalid_credentials(test_client: AsyncClient):
    """Тест попытки входа с неверными учетными данными"""
    response = await test_client.post(
        "/api/v1/auth/jwt/login",
        data={
            "username": "nonexistent@example.com",
            "password": "wrongpassword"
        }
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

@pytest.mark.asyncio
async def test_create_link_invalid_url(test_client: AsyncClient):
    """Тест создания ссылки с невалидным URL"""
    await test_client.post(
        "/api/v1/auth/register",
        json={
            "email": "invalid@example.com",
            "password": "testpassword123",
            "username": "invaliduser"
        }
    )
    
    login_response = await test_client.post(
        "/api/v1/auth/jwt/login",
        data={
            "username": "invalid@example.com",
            "password": "testpassword123"
        }
    )
    token = login_response.json()["access_token"]
    
    response = await test_client.post(
        "/api/v1/links/shorten",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "original_url": "not-a-url",
            "custom_alias": "invalid-link"
        }
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

@pytest.mark.asyncio
async def test_create_link_duplicate_alias(test_client: AsyncClient):
    """Тест создания ссылки с уже существующим алиасом"""
    await test_client.post(
        "/api/v1/auth/register",
        json={
            "email": "duplicate@example.com",
            "password": "testpassword123",
            "username": "duplicateuser"
        }
    )
    
    login_response = await test_client.post(
        "/api/v1/auth/jwt/login",
        data={
            "username": "duplicate@example.com",
            "password": "testpassword123"
        }
    )
    token = login_response.json()["access_token"]
    
    await test_client.post(
        "/api/v1/links/shorten",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "original_url": "https://example1.com",
            "custom_alias": "duplicate-link"
        }
    )
    
    response = await test_client.post(
        "/api/v1/links/shorten",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "original_url": "https://example2.com",
            "custom_alias": "duplicate-link"
        }
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST

@pytest.mark.asyncio
async def test_access_unauthorized(test_client: AsyncClient):
    """Тест доступа к защищенным эндпоинтам без авторизации"""
    response = await test_client.post(
        "/api/v1/links/shorten",
        json={
            "original_url": "https://example.com",
            "custom_alias": "unauthorized-link"
        }
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

@pytest.mark.asyncio
async def test_nonexistent_link(test_client: AsyncClient):
    """Тест обращения к несуществующей ссылке"""
    response = await test_client.get("/nonexistent-link")
    assert response.status_code == status.HTTP_404_NOT_FOUND

@pytest.mark.asyncio
async def test_expired_link(test_client: AsyncClient):
    """Тест обращения к просроченной ссылке"""
    await test_client.post(
        "/api/v1/auth/register",
        json={
            "email": "expired@example.com",
            "password": "testpassword123",
            "username": "expireduser"
        }
    )
    
    login_response = await test_client.post(
        "/api/v1/auth/jwt/login",
        data={
            "username": "expired@example.com",
            "password": "testpassword123"
        }
    )
    token = login_response.json()["access_token"]
    
    create_response = await test_client.post(
        "/api/v1/links/shorten",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "original_url": "https://example.com",
            "custom_alias": "expired-link",
            "expires_at": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        }
    )
    short_code = create_response.json()["short_url"].split("/")[-1]
    
    response = await test_client.get(f"/{short_code}")
    assert response.status_code == status.HTTP_410_GONE

@pytest.mark.asyncio
async def test_update_other_user_link(test_client: AsyncClient):
    """Тест запрета обновления чужой ссылки (403 Forbidden)."""
    email1 = "owner@example.com"
    pass1 = "password123"
    await test_client.post("/api/v1/auth/register", json={"email": email1, "password": pass1, "username": "owneruser"})
    login_resp1 = await test_client.post("/api/v1/auth/jwt/login", data={"username": email1, "password": pass1})
    token1 = login_resp1.json()["access_token"]

    email2 = "other@example.com"
    pass2 = "password456"
    await test_client.post("/api/v1/auth/register", json={"email": email2, "password": pass2, "username": "otheruser"})
    login_resp2 = await test_client.post("/api/v1/auth/jwt/login", data={"username": email2, "password": pass2})
    token2 = login_resp2.json()["access_token"]

    create_resp = await test_client.post(
        "/api/v1/links/shorten",
        headers={"Authorization": f"Bearer {token1}"},
        json={"original_url": "https://owner-link.com", "custom_alias": "owner-link"}
    )
    short_code = create_resp.json()["short_code"]

    update_resp = await test_client.put(
        f"/api/v1/links/{short_code}",
        headers={"Authorization": f"Bearer {token2}"},
        json={"original_url": "https://hacked.com"}
    )
    assert update_resp.status_code == status.HTTP_403_FORBIDDEN

@pytest.mark.asyncio
async def test_delete_other_user_link(test_client: AsyncClient):
    """Тест запрета удаления чужой ссылки (403 Forbidden)."""
    email1 = "owner_del@example.com"
    pass1 = "password123"
    await test_client.post("/api/v1/auth/register", json={"email": email1, "password": pass1, "username": "ownerdeluser"})
    login_resp1 = await test_client.post("/api/v1/auth/jwt/login", data={"username": email1, "password": pass1})
    token1 = login_resp1.json()["access_token"]

    email2 = "other_del@example.com"
    pass2 = "password456"
    await test_client.post("/api/v1/auth/register", json={"email": email2, "password": pass2, "username": "otherdeluser"})
    login_resp2 = await test_client.post("/api/v1/auth/jwt/login", data={"username": email2, "password": pass2})
    token2 = login_resp2.json()["access_token"]

    create_resp = await test_client.post(
        "/api/v1/links/shorten",
        headers={"Authorization": f"Bearer {token1}"},
        json={"original_url": "https://owner-del-link.com", "custom_alias": "owner-del-link"}
    )
    short_code = create_resp.json()["short_code"]

    delete_resp = await test_client.delete(
        f"/api/v1/links/{short_code}",
        headers={"Authorization": f"Bearer {token2}"}
    )
    assert delete_resp.status_code == status.HTTP_403_FORBIDDEN

@pytest.mark.asyncio
async def test_update_link_success(test_client: AsyncClient):
    """Тест успешного обновления ссылки."""
    email = "update_success@example.com"
    password = "testpassword123"
    await test_client.post("/api/v1/auth/register", json={"email": email, "password": password, "username": "updatesuccessuser"})
    login_resp = await test_client.post("/api/v1/auth/jwt/login", data={"username": email, "password": password})
    token = login_resp.json()["access_token"]

    alias = "update-success-link"
    create_resp = await test_client.post(
        "/api/v1/links/shorten",
        headers={"Authorization": f"Bearer {token}"},
        json={"original_url": "https://initial-update.com", "custom_alias": alias}
    )
    assert create_resp.status_code == status.HTTP_201_CREATED
    short_code = create_resp.json()["short_code"]

    updated_url = "https://updated-successfully.com"
    new_expiry_dt = datetime.now(timezone.utc) + timedelta(days=30)
    new_expiry_iso = new_expiry_dt.isoformat()

    update_resp = await test_client.put(
        f"/api/v1/links/{short_code}",
        headers={"Authorization": f"Bearer {token}"},
        json={"original_url": updated_url, "expires_at": new_expiry_iso}
    )
    assert update_resp.status_code == status.HTTP_200_OK
    update_data = update_resp.json()
    assert update_data["original_url"] == updated_url
    assert update_data["expires_at"].split('.')[0] == new_expiry_dt.isoformat().split('.')[0]
    assert update_data["short_code"] == short_code

    stats_resp = await test_client.get(
        f"/api/v1/links/{short_code}/stats",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert stats_resp.status_code == status.HTTP_200_OK
    stats_data = stats_resp.json()
    assert stats_data["original_url"] == updated_url
    assert stats_data["expires_at"].split('.')[0] == new_expiry_dt.isoformat().split('.')[0]

@pytest.mark.asyncio
async def test_read_users_me_no_token(test_client: AsyncClient):
    """Тест доступа к /users/me без токена."""
    response = await test_client.get("/api/v1/auth/users/me")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Not authenticated" in response.json()["detail"]

@pytest.mark.asyncio
async def test_read_users_me_invalid_token_format(test_client: AsyncClient):
    """Тест доступа к /users/me с некорректным форматом заголовка."""
    response = await test_client.get("/api/v1/auth/users/me", headers={"Authorization": "invalid token"})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Not authenticated" in response.json()["detail"]

@pytest.mark.asyncio
async def test_read_users_me_invalid_token(test_client: AsyncClient):
    """Тест доступа к /users/me с невалидным JWT токеном."""
    invalid_token = "this.is.not.a.valid.jwt"
    response = await test_client.get("/api/v1/auth/users/me", headers={"Authorization": f"Bearer {invalid_token}"})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Could not validate credentials" in response.json()["detail"]

@pytest.mark.asyncio
async def test_read_users_me_expired_token(test_client: AsyncClient):
    """Тест доступа к /users/me с истекшим токеном."""
    expired_token = create_access_token(
        data={"sub": "test@example.com"},
        expires_delta=timedelta(seconds=-1)
    )
    response = await test_client.get("/api/v1/auth/users/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Could not validate credentials" in response.json()["detail"]

@pytest.mark.asyncio
async def test_read_users_me_no_sub(test_client: AsyncClient):
    """Тест доступа к /users/me с токеном без поля 'sub'."""
    token_no_sub = create_access_token(data={"email": "test@example.com"})
    response = await test_client.get("/api/v1/auth/users/me", headers={"Authorization": f"Bearer {token_no_sub}"})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Could not validate credentials" in response.json()["detail"]

@pytest.mark.asyncio
async def test_read_users_me_user_not_found(test_client: AsyncClient):
    """Тест доступа к /users/me с токеном пользователя, которого нет в БД."""
    token_ghost_user = create_access_token(data={"sub": "ghost@example.com"})
    response = await test_client.get("/api/v1/auth/users/me", headers={"Authorization": f"Bearer {token_ghost_user}"})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Could not validate credentials" in response.json()["detail"]

@pytest.mark.asyncio
async def test_create_short_link_collision(test_client: AsyncClient):
    """Тест создания короткой ссылки с коллизией короткого кода."""
    await test_client.post(
        "/api/v1/auth/register",
        json={
            "email": "collision@example.com",
            "password": "testpassword123",
            "username": "collisionuser"
        }
    )
    login_response = await test_client.post(
        "/api/v1/auth/jwt/login",
        data={
            "username": "collision@example.com",
            "password": "testpassword123"
        }
    )
    token = login_response.json()["access_token"]

    response1 = await test_client.post(
        "/api/v1/links/shorten",
        headers={"Authorization": f"Bearer {token}"},
        json={"original_url": "https://example1.com"}
    )
    assert response1.status_code == status.HTTP_201_CREATED
    short_code1 = response1.json()["short_code"]

    response2 = await test_client.post(
        "/api/v1/links/shorten",
        headers={"Authorization": f"Bearer {token}"},
        json={"original_url": "https://example2.com"}
    )
    assert response2.status_code == status.HTTP_201_CREATED
    short_code2 = response2.json()["short_code"]

    assert short_code1 != short_code2

@pytest.mark.asyncio
async def test_update_link_remove_trailing_slash(test_client: AsyncClient):
    """Тест обновления ссылки с удалением завершающего слэша."""
    await test_client.post(
        "/api/v1/auth/register",
        json={
            "email": "slash@example.com",
            "password": "testpassword123",
            "username": "slashuser"
        }
    )
    login_response = await test_client.post(
        "/api/v1/auth/jwt/login",
        data={
            "username": "slash@example.com",
            "password": "testpassword123"
        }
    )
    token = login_response.json()["access_token"]

    create_response = await test_client.post(
        "/api/v1/links/shorten",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "original_url": "https://example.com",
            "custom_alias": "slash-test"
        }
    )
    assert create_response.status_code == status.HTTP_201_CREATED

    update_response = await test_client.put(
        "/api/v1/links/slash-test",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "original_url": "https://updated-example.com/"
        }
    )
    assert update_response.status_code == status.HTTP_200_OK
    assert update_response.json()["original_url"] == "https://updated-example.com"

@pytest.mark.asyncio
async def test_link_inconsistency(test_client: AsyncClient):
    """Тест на несоответствие ссылки при редиректе."""
    await test_client.post(
        "/api/v1/auth/register",
        json={
            "email": "inconsistent@example.com",
            "password": "testpassword123",
            "username": "inconsistentuser"
        }
    )
    login_response = await test_client.post(
        "/api/v1/auth/jwt/login",
        data={
            "username": "inconsistent@example.com",
            "password": "testpassword123"
        }
    )
    token = login_response.json()["access_token"]

    create_response = await test_client.post(
        "/api/v1/links/shorten",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "original_url": "https://example.com",
            "custom_alias": "inconsistent-test"
        }
    )
    assert create_response.status_code == status.HTTP_201_CREATED

    stats_response = await test_client.get(
        "/api/v1/links/non-existent/stats",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert stats_response.status_code == status.HTTP_404_NOT_FOUND 

@pytest.mark.asyncio
async def test_login_invalid_form_data(test_client: AsyncClient):
    """Тест аутентификации с неверным форматом данных."""
    await test_client.post(
        "/api/v1/auth/register",
        json={
            "email": "form@example.com",
            "password": "testpassword123",
            "username": "formuser"
        }
    )

    response = await test_client.post(
        "/api/v1/auth/jwt/login",
        json={ 
            "username": "form@example.com",
            "password": "testpassword123"
        }
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

@pytest.mark.asyncio
async def test_register_user_db_error(test_client, monkeypatch):
    async def mock_get_by_email(*args, **kwargs):
        return None
    
    async def mock_save(*args, **kwargs):
        raise Exception("DB Error")
    
    monkeypatch.setattr("app.models.user.User.get_by_email", mock_get_by_email)
    monkeypatch.setattr("app.models.user.User.save", mock_save)
    
    response = await test_client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@example.com",
            "password": "testpass123",
            "username": "testuser"
        }
    )
    assert response.status_code == 500
    assert response.json()["detail"] == "Error saving user to database"

@pytest.mark.asyncio
async def test_login_invalid_password(test_client, test_user):
    response = await test_client.post(
        "/api/v1/auth/jwt/login",
        data={
            "username": test_user["email"],
            "password": "wrongpassword"
        }
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"

@pytest.mark.asyncio
async def test_login_nonexistent_user(test_client):
    response = await test_client.post(
        "/api/v1/auth/jwt/login",
        data={
            "username": "nonexistent@example.com",
            "password": "testpass123"
        }
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"

@pytest.mark.asyncio
async def test_redirect_expired_link(test_client, test_user, test_link_factory, db_session):
    expired_link = await test_link_factory(
        user_id=test_user["id"],
        expires_at=datetime.now(timezone.utc) - timedelta(days=1)
    )
    await db_session.commit()
    
    response = await test_client.get(f"/{expired_link.short_code}")
    assert response.status_code == 410
    assert response.json()["detail"] == "Link expired"

@pytest.mark.asyncio
async def test_redirect_link_inconsistency(test_client, test_user, monkeypatch):
    class MockLink:
        id = 99999 
        short_code = "test-inconsistency"
    
    async def mock_get_by_short_code(*args, **kwargs):
        return MockLink()
    
    async def mock_execute(*args, **kwargs):
        class MockResult:
            def scalar_one_or_none(self):
                return None
        return MockResult()
    
    monkeypatch.setattr("app.models.link.Link.get_by_short_code", mock_get_by_short_code)
    monkeypatch.setattr("sqlalchemy.ext.asyncio.AsyncSession.execute", mock_execute)
    
    response = await test_client.get("/test-inconsistency")
    assert response.status_code == 404
    assert response.json()["detail"] == "Link inconsistency"

@pytest.mark.asyncio
async def test_update_link_not_found(test_client, test_user_token):
    response = await test_client.put(
        "/api/v1/links/nonexistent",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={"original_url": "https://example.com/new"}
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Link not found"

@pytest.mark.asyncio
async def test_update_link_unauthorized(test_client, test_user_token, test_link_factory, test_user2, db_session):
    link = await test_link_factory(user_id=test_user2["id"])
    await db_session.commit()
    
    response = await test_client.put(
        f"/api/v1/links/{link.short_code}",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={"original_url": "https://example.com/new"}
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authorized to update this link"

@pytest.mark.asyncio
async def test_delete_link_not_found(test_client, test_user_token):
    response = await test_client.delete(
        "/api/v1/links/nonexistent",
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Link not found"

@pytest.mark.asyncio
async def test_delete_link_unauthorized(test_client, test_user_token, test_link_factory, test_user2, db_session):
    link = await test_link_factory(user_id=test_user2["id"])
    await db_session.commit()
    
    response = await test_client.delete(
        f"/api/v1/links/{link.short_code}",
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authorized to delete this link" 
