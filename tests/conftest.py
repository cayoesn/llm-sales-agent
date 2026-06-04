from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

import app.agent as agent_module
from app.repository import repo


@pytest.fixture(autouse=True)
def reset_state():
    repo.carts.clear()
    repo.orders.clear()
    repo.sessions.clear()

    try:
        from app.main import get_agent

        get_agent.cache_clear()
    except Exception:
        pass


@pytest.fixture(autouse=True)
def stub_external_dependencies(monkeypatch):
    fake_trace = MagicMock()
    fake_trace.span.return_value = MagicMock()
    fake_langfuse = MagicMock()
    fake_langfuse.trace.return_value = fake_trace
    fake_genai_client = MagicMock()
    fake_genai_client.aio.models.generate_content = AsyncMock()

    def fake_agent(*args, **kwargs):
        return SimpleNamespace(
            tools=kwargs.get("tools", []),
            model=kwargs.get("model", "gemini-1.5-flash"),
        )

    monkeypatch.setattr(agent_module, "Agent", fake_agent, raising=False)
    monkeypatch.setattr(agent_module, "langfuse", fake_langfuse, raising=False)
    monkeypatch.setattr(agent_module, "genai_client", fake_genai_client, raising=False)
