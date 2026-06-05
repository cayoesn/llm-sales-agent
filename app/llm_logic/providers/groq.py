from typing import Any

import httpx

from app.llm_logic.providers.base import LLMProviderClient


class GroqProviderClient(LLMProviderClient):
    def __init__(
        self, api_key: str, base_url: str, model: str, temperature: float
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.temperature = temperature

    async def chat(
        self,
        trace: Any,
        messages: list[dict[str, Any]],
        include_tools: bool = True,
        tools_metadata: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        span = trace.span(name="groq_chat")
        span.update(input={"messages": messages})

        try:
            async with httpx.AsyncClient() as client:
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                }
                payload: dict[str, Any] = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": self.temperature,
                }
                if include_tools and tools_metadata:
                    # Groq supports OpenAI tool calling
                    payload["tools"] = [
                        {"type": "function", "function": t} for t in tools_metadata
                    ]

                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=240.0,
                )
                response.raise_for_status()
                data = response.json()

                # Extract usage
                usage = data.get("usage", {})
                span.update(
                    usage={
                        "prompt_tokens": usage.get("prompt_tokens"),
                        "completion_tokens": usage.get("completion_tokens"),
                    }
                )

                message = self._parse_openai_response(data)
                span.update(output={"response": message})
                span.end()
                return message
        except Exception as e:
            span.update(level="ERROR", status_message=str(e))
            span.end()
            raise

    def _parse_openai_response(self, data: dict[str, Any]) -> dict[str, Any]:
        choice = data.get("choices", [{}])[0]
        message = choice.get("message", {})

        parsed = {"content": message.get("content") or ""}

        if "tool_calls" in message:
            parsed["tool_calls"] = [
                {
                    "function": {
                        "name": tool_call["function"]["name"],
                        "arguments": tool_call["function"]["arguments"],
                    }
                }
                for tool_call in message["tool_calls"]
            ]

        return parsed
