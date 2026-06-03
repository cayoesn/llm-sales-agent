from unittest.mock import MagicMock, patch

import pytest

from app.agent import SalesAgent
from app.models import ConversationSession


@pytest.fixture
def agent():
    return SalesAgent()


@pytest.mark.asyncio
async def test_agent_chat_ollama_no_tools():
    # Mocking Ollama call
    mock_response = MagicMock()
    mock_response.json.return_value = {"message": {"content": "Hello! How can I help?"}}
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.post", return_value=mock_response):
        session = ConversationSession(session_id="s1")
        with patch("app.services.SalesService.get_session", return_value=session):
            agent = SalesAgent()
            resp = await agent.chat("s1", "oi")
            assert resp == "Hello! How can I help?"
            assert session.history[-2:] == [
                {"role": "user", "content": "oi"},
                {"role": "assistant", "content": "Hello! How can I help?"},
            ]


@pytest.mark.asyncio
async def test_agent_chat_ollama_with_tools():
    # 1st call: request tool call
    mock_res1 = MagicMock()
    mock_res1.json.return_value = {
        "message": {
            "tool_calls": [
                {
                    "function": {
                        "name": "add_to_cart",
                        "arguments": {
                            "product_name": "Tênis",
                            "quantity": 1,
                            "price": 100.0,
                        },
                    }
                }
            ]
        }
    }

    # 2nd call: summary
    mock_res2 = MagicMock()
    mock_res2.json.return_value = {
        "message": {"content": "I added the sneakers to your cart!"}
    }

    with patch("httpx.AsyncClient.post", side_effect=[mock_res1, mock_res2]):
        with patch("app.services.SalesService.add_to_cart", return_value="Success"):
            agent = SalesAgent()
            resp = await agent.chat("s1", "quero um tênis")
            assert resp == "I added the sneakers to your cart!"


@pytest.mark.asyncio
async def test_agent_chat_error():
    with patch("httpx.AsyncClient.post", side_effect=Exception("Network error")):
        agent = SalesAgent()
        resp = await agent.chat("s1", "oi")
        assert resp == "Sorry, there was a problem processing your request."
