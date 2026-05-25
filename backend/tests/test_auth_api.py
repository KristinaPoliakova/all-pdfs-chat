import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_login_me_and_logout(api_client: AsyncClient) -> None:
    register = await api_client.post(
        "/api/v1/auth/register",
        json={"email": "alice@example.com", "password": "secret123"},
    )
    assert register.status_code == 201
    payload = register.json()
    assert payload["user"]["email"] == "alice@example.com"
    token = payload["token"]

    me = await api_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me.status_code == 200
    assert me.json()["email"] == "alice@example.com"

    logout = await api_client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert logout.status_code == 204

    me_after = await api_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_after.status_code == 401


@pytest.mark.asyncio
async def test_login_with_registered_user(api_client: AsyncClient) -> None:
    await api_client.post(
        "/api/v1/auth/register",
        json={"email": "bob@example.com", "password": "secret123"},
    )

    login = await api_client.post(
        "/api/v1/auth/login",
        json={"email": "bob@example.com", "password": "secret123"},
    )

    assert login.status_code == 200
    assert login.json()["user"]["email"] == "bob@example.com"


@pytest.mark.asyncio
async def test_register_duplicate_returns_409(api_client: AsyncClient) -> None:
    body = {"email": "dup@example.com", "password": "secret123"}
    first = await api_client.post("/api/v1/auth/register", json=body)
    second = await api_client.post("/api/v1/auth/register", json=body)

    assert first.status_code == 201
    assert second.status_code == 409
