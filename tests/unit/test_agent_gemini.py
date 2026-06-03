from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agent import SalesAgent


@pytest.fixture
def agent():
    return SalesAgent()


@pytest.mark.asyncio
async def test_agent_chat_gemini_no_tools():
    mock_response = MagicMock()
    mock_candidate = MagicMock()
    mock_candidate.content.parts = [MagicMock()]
    mock_candidate.content.parts[0].function_call = None
    mock_response.candidates = [mock_candidate]
    mock_response.text = "Gemini response"

    with patch("app.agent.settings.LLM_PROVIDER", "gemini"):
        with patch(
            "app.agent.genai_client.aio.models.generate_content",
            new=AsyncMock(return_value=mock_response),
        ):
            agent = SalesAgent()
            resp = await agent.chat("s1", "oi")
            assert resp == "Gemini response"


@pytest.mark.asyncio
async def test_agent_chat_gemini_with_tools():
    mock_res1 = MagicMock()
    mock_part1 = MagicMock()
    mock_part1.function_call.name = "add_to_cart"
    mock_part1.function_call.args = {
        "product_name": "Tênis",
        "quantity": 1,
        "price": 100.0,
    }
    mock_res1.candidates = [MagicMock(content=MagicMock(parts=[mock_part1]))]

    mock_res2 = MagicMock()
    mock_res2.text = "Added via Gemini!"
    mock_res2.candidates = [
        MagicMock(content=MagicMock(parts=[MagicMock(function_call=None)]))
    ]

    with patch("app.agent.settings.LLM_PROVIDER", "gemini"):
        with patch(
            "app.agent.genai_client.aio.models.generate_content",
            new=AsyncMock(side_effect=[mock_res1, mock_res2]),
        ):
            with patch("app.services.SalesService.add_to_cart", return_value="Sucesso"):
                agent = SalesAgent()
                resp = await agent.chat("s1", "comprar tênis")
                assert resp == "Added via Gemini!"
