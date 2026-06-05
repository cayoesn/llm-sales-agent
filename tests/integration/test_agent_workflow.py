from unittest.mock import AsyncMock, patch

import pytest

from app.llm_logic.agent import SalesAgent
from app.repository import repo
from app.services import SalesService


@pytest.fixture(autouse=True)
def clean_repo():
    repo.carts = {}
    repo.orders = {}
    repo.sessions = {}


@pytest.mark.asyncio
async def test_agent_integration_with_service_and_repo():
    """
    Test the integration between SalesAgent, SalesService and InMemoryRepository.
    This simulates a real workflow where the agent decides to call a tool.
    """
    agent = SalesAgent()
    session_id = "test_integration_s1"

    with patch("app.llm_logic.agent.settings.LLM_PROVIDER", "ollama"):
        with patch(
            "app.llm_logic.providers.ollama.OllamaProviderClient.chat",
            new_callable=AsyncMock,
            side_effect=[
                {
                    "tool_calls": [
                        {
                            "function": {
                                "name": "add_to_cart",
                                "arguments": {
                                    "product_name": "Tênis Nike",
                                    "quantity": 2,
                                    "price": 299.9,
                                },
                            }
                        }
                    ]
                },
                {"content": "Done! I added 2 Nike sneakers to your cart."},
            ],
        ):
            # Execute the agent chat
            response = await agent.chat(session_id, "quero 2 tênis nike de 299.9")

            # Verify the result from LLM summary
            assert "Done!" in response
            assert "added 2 Nike sneakers" in response

            # VERIFY INTEGRATION: Check if the product was ACTUALLY added to the repository
            cart = await SalesService.get_or_create_cart(session_id)
            assert len(cart.items) == 1
            assert cart.items[0].name == "Tênis Nike"
            assert cart.items[0].quantity == 2
            assert cart.items[0].price == 299.9


@pytest.mark.asyncio
async def test_agent_checkout_integration():
    """
    Test the full flow from agent call to order persistence in repository.
    """
    agent = SalesAgent()
    session_id = "test_checkout_s1"

    # Pre-populate cart via service
    await SalesService.add_to_cart(session_id, "Camisa", 1, 50.0)

    with patch("app.llm_logic.agent.settings.LLM_PROVIDER", "ollama"):
        with patch(
            "app.llm_logic.providers.ollama.OllamaProviderClient.chat",
            new_callable=AsyncMock,
            side_effect=[
                {"tool_calls": [{"function": {"name": "checkout", "arguments": {}}}]},
                {"content": "Order completed! Here is your PIX code."},
            ],
        ):
            await agent.chat(session_id, "quero finalizar minha compra")

            # VERIFY INTEGRATION: Cart should be cleared and Order should exist in repo
            assert session_id not in repo.carts
            assert len(repo.orders) == 1
            order = list(repo.orders.values())[0]
            assert order.session_id == session_id
            assert order.total_price == 50.0
