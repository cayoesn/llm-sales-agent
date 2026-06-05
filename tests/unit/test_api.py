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

@pytest.mark.asyncio
@patch("app.main.settings")
async def test_check_ollama_ready_non_ollama(mock_settings):
    mock_settings.LLM_PROVIDER = "gemini"
    from app.main import check_ollama_ready
    assert await check_ollama_ready() is True

@pytest.mark.asyncio
@patch("app.main.settings")
@patch("httpx.AsyncClient.get")
async def test_check_ollama_ready_success(mock_get, mock_settings):
    mock_settings.LLM_PROVIDER = "ollama"
    mock_settings.OLLAMA_MODEL = "llama3.1"

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"models": [{"name": "llama3.1"}]}
    mock_get.return_value = mock_response

    from app.main import check_ollama_ready
    assert await check_ollama_ready() is True

@pytest.mark.asyncio
@patch("app.main.settings")
@patch("httpx.AsyncClient.get")
async def test_check_ollama_ready_failure(mock_get, mock_settings):
    mock_settings.LLM_PROVIDER = "ollama"
    mock_get.side_effect = Exception("Connection error")

    from app.main import check_ollama_ready
    assert await check_ollama_ready() is False

@pytest.mark.asyncio
@patch("app.main.settings")
@patch("app.main.check_ollama_ready", new_callable=AsyncMock)
@patch("asyncio.sleep", new_callable=AsyncMock)
async def test_lifespan_ollama_ready(mock_sleep, mock_check, mock_settings):
    mock_settings.LLM_PROVIDER = "ollama"
    mock_check.return_value = True

    from app.main import lifespan
    async with lifespan(app):
        mock_check.assert_awaited()
        mock_sleep.assert_not_awaited()
