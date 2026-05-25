from datetime import UTC, datetime, timedelta

import pytest

from tests.db_helpers import (
    make_sql_session_repository,
    make_sql_user_repository,
    open_test_database,
)


@pytest.mark.asyncio
async def test_create_and_get_by_token_hash() -> None:
    runtime = await open_test_database()
    users = make_sql_user_repository(runtime)
    sessions = make_sql_session_repository(runtime)

    user = await users.create(email="alice@example.com", password_hash="hash")
    expires_at = datetime.now(UTC) + timedelta(days=1)
    created = await sessions.create(
        user_id=user.id,
        token_hash="abc123",
        expires_at=expires_at,
    )

    found = await sessions.get_by_token_hash("abc123")

    assert found == created

    await runtime.close()
