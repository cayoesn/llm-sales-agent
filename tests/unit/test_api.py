from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.main import app


@pytest.mark.asyncio
async def test_health_endpoint():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_chat_endpoint_structure():
    fake_agent = MagicMock()
    fake_agent.chat = AsyncMock(return_value="Hello! How can I help?")
    payload = {"session_id": "test_s", "message": "oi"}

    with patch("app.main.get_agent", return_value=fake_agent):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            response = await ac.post(f"{settings.API_V1_STR}/chat", json=payload)

    assert response.status_code == 200
    assert response.json() == {
        "session_id": "test_s",
        "response": "Hello! How can I help?",
    }
    fake_agent.chat.assert_awaited_once_with("test_s", "oi")


def test_app_metadata():
    assert app.title == settings.PROJECT_NAME
    assert app.version == settings.VERSION
