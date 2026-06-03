from unittest.mock import patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.middlewares import LoggingMiddleware


@pytest.mark.asyncio
async def test_logging_middleware_adds_request_id_header():
    app = FastAPI()
    app.add_middleware(LoggingMiddleware)

    @app.get("/ping")
    async def ping():
        return {"ok": True}

    with patch("app.api.middlewares.logger.info") as mock_log:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            response = await ac.get("/ping")

    assert response.status_code == 200
    assert response.headers["x-request-id"]
    mock_log.assert_called_once()
