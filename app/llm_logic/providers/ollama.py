from typing import Any

import httpx

from app.llm_logic.providers.base import LLMProviderClient


class OllamaProviderClient(LLMProviderClient):
    def __init__(self, base_url: str, model: str, temperature: float) -> None:
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
        span = trace.span(name="ollama_chat")
        span.update(input={"messages": messages})

        try:
            async with httpx.AsyncClient() as client:
                payload: dict[str, Any] = {
                    "model": self.model,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "temperature": self.temperature,
                        "top_p": 0.95,
                        "top_k": 40,
                    },
                }
                if include_tools and tools_metadata:
                    payload["tools"] = tools_metadata

                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                    timeout=240.0,
                )
                response.raise_for_status()
                data = response.json()

                # Extract usage
                usage = {
                    "prompt_tokens": data.get("prompt_eval_count"),
                    "completion_tokens": data.get("eval_count"),
                }
                if any(usage.values()):
                    span.update(usage=usage)

                message = self._parse_ollama_response(data)
                span.update(output={"response": message})
                span.end()
                return message
        except Exception as e:
            span.update(level="ERROR", status_message=str(e))
            span.end()
            raise

    def _parse_ollama_response(self, data: dict[str, Any]) -> dict[str, Any]:
        # Implementation from previous agent.py
        if not isinstance(data, dict):
            return {"content": str(data)}
        message = data.get("message")
        if message is None:
            message = data.get("response") or data.get("output")
        if message is None and isinstance(data.get("choices"), list):
            first_choice = data["choices"][0] if data["choices"] else None
            if isinstance(first_choice, dict):
                message = (
                    first_choice.get("message")
                    or first_choice.get("content")
                    or first_choice.get("response")
                )
        if message is None:
            output = data.get("output")
            if isinstance(output, list) and output:
                message = output[0]
        if isinstance(message, dict):
            content = message.get("content")
            tool_calls = message.get("tool_calls")
            if isinstance(content, list):
                flattened = []
                for part in content:
                    if isinstance(part, dict):
                        flattened.append(str(part.get("text", "")))
                    elif isinstance(part, str):
                        flattened.append(part)
                parsed = {"content": "".join(flattened).strip()}
            elif content is not None:
                parsed = {"content": content}
            else:
                parsed = {"content": ""}
            if tool_calls is not None:
                parsed["tool_calls"] = tool_calls
            return parsed
        if isinstance(message, list) and message:
            first_item = message[0]
            if isinstance(first_item, dict) and "content" in first_item:
                return {"content": first_item["content"]}
            return {"content": str(first_item)}
        return {"content": str(message) if message is not None else ""}
