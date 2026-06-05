from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.config import settings
from app.llm_logic.agent import SalesAgent
from app.models import ConversationSession


@pytest.fixture
def groq_agent():
    # Ensure LLM_PROVIDER is set to "groq" for these tests
    with patch("app.llm_logic.agent.settings.LLM_PROVIDER", "groq"):
        # Patch the Groq API key, base URL, and temperature in app.config.settings
        with patch("app.config.settings.GROQ_API_KEY", "mock-api-key"):
            with patch("app.config.settings.GROQ_BASE_URL", "http://mock-groq-url"):
                with patch("app.config.settings.GROQ_TEMPERATURE", 0.0):
                    agent = SalesAgent()
                    yield agent


@pytest.mark.asyncio
async def test_agent_chat_groq_no_tools(groq_agent):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [
            {"message": {"content": "Hello from Groq! How can I help you today?"}}
        ]
    }
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.post", return_value=mock_response) as mock_post:
        session = ConversationSession(session_id="s1")
        with patch("app.services.SalesService.get_session", return_value=session):
            resp = await groq_agent.chat("s1", "oi")
            assert resp == "Hello from Groq! How can I help you today?"
            mock_post.assert_called_once()
            _, kwargs = mock_post.call_args
            assert kwargs["json"]["model"] == settings.GROQ_MODEL
            assert "tools" in kwargs["json"]  # Tools are included by default
            assert session.history[-2:] == [
                {"role": "user", "content": "oi"},
                {
                    "role": "assistant",
                    "content": "Hello from Groq! How can I help you today?",
                },
            ]


@pytest.mark.asyncio
async def test_agent_chat_groq_with_tools(groq_agent):
    # First call to Groq: returns a tool call
    mock_res_tool = MagicMock()
    mock_res_tool.json.return_value = {
        "choices": [
            {
                "message": {
                    "tool_calls": [
                        {
                            "function": {
                                "name": "add_to_cart",
                                "arguments": '{"product_name": "Laptop", "quantity": 1, "price": 1200.0}',
                            }
                        }
                    ]
                }
            }
        ]
    }
    mock_res_tool.raise_for_status = MagicMock()

    # Second call to Groq: returns a summary after tool execution
    mock_res_summary = MagicMock()
    mock_res_summary.json.return_value = {
        "choices": [{"message": {"content": "I've added the Laptop to your cart!"}}]
    }
    mock_res_summary.raise_for_status = MagicMock()

    with patch(
        "httpx.AsyncClient.post", side_effect=[mock_res_tool, mock_res_summary]
    ) as mock_post:
        with patch(
            "app.services.SalesService.add_to_cart",
            new_callable=AsyncMock,
            return_value="Success",
        ) as mock_add_to_cart:
            session = ConversationSession(session_id="s1")
            with patch("app.services.SalesService.get_session", return_value=session):
                resp = await groq_agent.chat("s1", "quero um Laptop de 1200")
                assert resp == "I've added the Laptop to your cart!"
                assert mock_post.call_count == 2
                mock_add_to_cart.assert_called_once_with(
                    product_name="Laptop", quantity=1, price=1200.0, session_id="s1"
                )
                assert session.history[-1] == {
                    "role": "assistant",
                    "content": "I've added the Laptop to your cart!",
                }


@pytest.mark.asyncio
async def test_agent_chat_groq_error_handling(groq_agent):
    with patch(
        "httpx.AsyncClient.post", side_effect=httpx.RequestError("Network error")
    ) as mock_post:
        session = ConversationSession(session_id="s1")
        with patch("app.services.SalesService.get_session", return_value=session):
            resp = await groq_agent.chat("s1", "oi")
            assert resp == "Desculpe, ocorreu um problema ao processar sua solicitação."
            mock_post.assert_called_once()
            # The agent does not add error messages to history in this implementation
            assert session.history[-1]["content"] == "oi"


@pytest.mark.asyncio
async def test_agent_chat_groq_http_error(groq_agent):
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "400 Bad Request",
        request=httpx.Request("POST", "http://mock-groq-url"),
        response=httpx.Response(400),
    )

    with patch("httpx.AsyncClient.post", return_value=mock_response) as mock_post:
        session = ConversationSession(session_id="s1")
        with patch("app.services.SalesService.get_session", return_value=session):
            resp = await groq_agent.chat("s1", "oi")
            assert resp == "Desculpe, ocorreu um problema ao processar sua solicitação."
            mock_post.assert_called_once()
            # The agent does not add error messages to history in this implementation
            assert session.history[-1]["content"] == "oi"
