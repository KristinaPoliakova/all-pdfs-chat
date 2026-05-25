from __future__ import annotations

from httpx import AsyncClient


async def register_and_get_auth_headers(
    client: AsyncClient,
    *,
    email: str = "pdf-user@example.com",
    password: str = "secret123",
) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password},
    )
    assert response.status_code == 201, response.text
    token = response.json()["token"]
    return {"Authorization": f"Bearer {token}"}
