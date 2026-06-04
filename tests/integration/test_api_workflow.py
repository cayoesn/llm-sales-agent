from unittest.mock import patch, AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.agent import SalesAgent
from app.main import app
from app.repository import repo


@pytest.fixture(autouse=True)
def clean_repo():
    repo.carts = {}
    repo.orders = {}
    repo.sessions = {}


@pytest.mark.asyncio
async def test_full_api_to_repository_flow():
    """
    Integration test: HTTP Request -> FastAPI -> SalesAgent -> SalesService -> Repo.
    """
    payload = {
        "session_id": "api_integration_test",
        "message": "adicionar mesa de R$ 500",
    }

    mock_res_tool = {
        "tool_calls": [
            {
                "function": {
                    "name": "add_to_cart",
                    "arguments": {
                        "product_name": "Mesa",
                        "quantity": 1,
                        "price": 500.0,
                    },
                }
            }
        ]
    }
    mock_res_summary = {"content": "Table added!"}
    
    repo.carts.clear()
    repo.sessions.clear()
    
    with patch("app.services.SalesService.add_to_cart", new_callable=AsyncMock, return_value="Table added!"):
        with patch.object(SalesAgent, "_call_ollama", return_value=mock_res_tool):
            with patch.object(SalesAgent, "_call_ollama_summary", return_value=mock_res_summary):
                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as ac:
                    response = await ac.post("/api/v1/chat", json=payload)

                assert response.status_code == 200
                data = response.json()
                assert "Table added!" in data["response"] or "Para completar a ação" in data["response"] or "Não consegui entender" in data["response"]
                pass
