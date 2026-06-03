from unittest.mock import AsyncMock, MagicMock, patch

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
async def test_agent_chat_ollama_with_choice_response_format():
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": "Hello from choices format!"
                }
            }
        ]
    }
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.post", return_value=mock_response):
        session = ConversationSession(session_id="s1")
        with patch("app.services.SalesService.get_session", return_value=session):
            agent = SalesAgent()
            resp = await agent.chat("s1", "oi")
            assert resp == "Hello from choices format!"


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
        with patch("app.services.SalesService.add_to_cart", new_callable=AsyncMock, return_value="Success"):
            agent = SalesAgent()
            resp = await agent.chat("s1", "quero um tênis")
            assert resp == "I added the sneakers to your cart!"


@pytest.mark.asyncio
async def test_agent_chat_ollama_with_indexed_tool_call():
    mock_res1 = MagicMock()
    mock_res1.json.return_value = {
        "message": {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "function": {
                        "index": 0,
                        "name": "",
                        "arguments": {
                            "produto_id": "tênis_de_corrida",
                            "quantidade": 2,
                            "carrinho_id": "s1",
                        },
                    }
                }
            ],
        }
    }

    mock_res2 = MagicMock()
    mock_res2.json.return_value = {
        "message": {"content": "I added the items to your cart!"}
    }

    with patch("httpx.AsyncClient.post", side_effect=[mock_res1, mock_res2]):
        agent = SalesAgent()
        with patch("app.services.SalesService.add_to_cart", new_callable=AsyncMock, return_value="Success"):
            resp = await agent.chat("s1", "quero adicionar 2 tênis de corrida")
            assert resp == "I added the items to your cart!"


@pytest.mark.asyncio
async def test_agent_chat_ollama_with_tool_call_missing_price():
    mock_res1 = MagicMock()
    mock_res1.json.return_value = {
        "message": {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "function": {
                        "name": "add_to_cart",
                        "arguments": {
                            "produto": "tênis de corrida",
                            "quantidade": 2,
                        },
                    }
                }
            ],
        }
    }

    mock_res2 = MagicMock()
    mock_res2.json.return_value = {
        "message": {"content": "Added the product without a price."}
    }

    with patch("httpx.AsyncClient.post", side_effect=[mock_res1, mock_res2]):
        agent = SalesAgent()
        with patch("app.services.SalesService.add_to_cart", new_callable=AsyncMock, return_value="Success"):
            resp = await agent.chat("s1", "quero adicionar 2 tênis de corrida")
            assert resp == "Added the product without a price."


@pytest.mark.asyncio
async def test_agent_chat_ollama_with_description_alias():
    mock_res1 = MagicMock()
    mock_res1.json.return_value = {
        "message": {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "function": {
                        "name": "add_to_cart",
                        "arguments": {
                            "descricao": "tênis de corrida",
                            "quantidade": 2,
                            "preco": 150.0,
                        },
                    }
                }
            ],
        }
    }

    mock_res2 = MagicMock()
    mock_res2.json.return_value = {
        "message": {"content": "Added the product using descricao alias."}
    }

    with patch("httpx.AsyncClient.post", side_effect=[mock_res1, mock_res2]):
        agent = SalesAgent()
        with patch("app.services.SalesService.add_to_cart", new_callable=AsyncMock, return_value="Success"):
            resp = await agent.chat("s1", "quero adicionar 2 tênis de corrida")
            assert resp == "Added the product using descricao alias."


@pytest.mark.asyncio
async def test_agent_chat_ollama_with_item_id_alias():
    mock_res1 = MagicMock()
    mock_res1.json.return_value = {
        "message": {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "function": {
                        "name": "add_to_cart",
                        "arguments": {
                            "item_id": "tênis_de_corrida",
                            "quantidade": 2,
                            "preco": 150.0,
                        },
                    }
                }
            ],
        }
    }

    mock_res2 = MagicMock()
    mock_res2.json.return_value = {
        "message": {"content": "Added the product using item_id alias."}
    }

    with patch("httpx.AsyncClient.post", side_effect=[mock_res1, mock_res2]):
        agent = SalesAgent()
        with patch("app.services.SalesService.add_to_cart", new_callable=AsyncMock, return_value="Success"):
            resp = await agent.chat("s1", "quero adicionar 2 tênis de corrida")
            assert resp == "Added the product using item_id alias."


@pytest.mark.asyncio
async def test_agent_chat_ollama_with_user_id_json_arguments():
    mock_res1 = MagicMock()
    mock_res1.json.return_value = {
        "message": {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "function": {
                        "name": "add_to_cart",
                        "arguments": '{"user_id":"s1","produto":"tênis de corrida","quantidade":2,"preco":150.0}',
                    }
                }
            ],
        }
    }

    mock_res2 = MagicMock()
    mock_res2.json.return_value = {
        "message": {"content": "Added the product using JSON arguments."}
    }

    with patch("httpx.AsyncClient.post", side_effect=[mock_res1, mock_res2]):
        agent = SalesAgent()
        with patch("app.services.SalesService.add_to_cart", new_callable=AsyncMock, return_value="Success"):
            resp = await agent.chat("s1", "quero adicionar 2 tênis de corrida")
            assert resp == "Added the product using JSON arguments."


@pytest.mark.asyncio
async def test_agent_chat_ollama_with_show_cart():
    mock_res1 = MagicMock()
    mock_res1.json.return_value = {
        "message": {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "function": {
                        "name": "show_cart",
                        "arguments": {"session_id": "s1"},
                    }
                }
            ],
        }
    }

    mock_res2 = MagicMock()
    mock_res2.json.return_value = {
        "message": {"content": "Here is your cart."}
    }

    with patch("httpx.AsyncClient.post", side_effect=[mock_res1, mock_res2]):
        with patch("app.services.SalesService.show_cart", new_callable=AsyncMock, return_value="2x Tênis - R$ 150.00 each - Total R$ 300.00\nCart total: R$ 300.00"):
            agent = SalesAgent()
            resp = await agent.chat("s1", "mostrar meu carrinho")
            assert resp == "Here is your cart."


@pytest.mark.asyncio
async def test_agent_chat_ollama_with_carrinho_alias():
    mock_res1 = MagicMock()
    mock_res1.json.return_value = {
        "message": {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "function": {
                        "name": "add_to_cart",
                        "arguments": {
                            "produto": "tênis de corrida",
                            "quantidade": 2,
                            "carrinho": "s1",
                        },
                    }
                }
            ],
        }
    }

    mock_res2 = MagicMock()
    mock_res2.json.return_value = {
        "message": {"content": "Added the product using carrinho alias."}
    }

    with patch("httpx.AsyncClient.post", side_effect=[mock_res1, mock_res2]):
        agent = SalesAgent()
        with patch("app.services.SalesService.add_to_cart", new_callable=AsyncMock, return_value="Success"):
            resp = await agent.chat("s1", "quero adicionar 2 tênis de corrida")
            assert resp == "Added the product using carrinho alias."


@pytest.mark.asyncio
async def test_agent_chat_error():
    with patch("httpx.AsyncClient.post", side_effect=Exception("Network error")):
        agent = SalesAgent()
        resp = await agent.chat("s1", "oi")
        assert resp == "Sorry, there was a problem processing your request."
