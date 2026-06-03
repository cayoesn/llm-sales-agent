from unittest.mock import patch

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

    with patch.object(
        SalesAgent, "_call_ollama", side_effect=[mock_res_tool, mock_res_summary]
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            response = await ac.post("/api/v1/chat", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["response"] == "Table added!"

        # Verify persistence integration
        assert "api_integration_test" in repo.carts
        assert len(repo.carts["api_integration_test"].items) == 1
        assert repo.carts["api_integration_test"].items[0].name == "Mesa"
