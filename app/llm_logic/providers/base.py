from abc import ABC, abstractmethod
from typing import Any


class LLMProviderClient(ABC):
    @abstractmethod
    async def chat(
        self,
        trace: Any,
        messages: list[dict[str, Any]],
        include_tools: bool = True,
        tools_metadata: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Send chat messages and return the normalized LLM response."""
        pass
