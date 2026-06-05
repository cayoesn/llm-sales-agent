from typing import Any, cast

from google.genai import types

from app.llm_logic.providers.base import LLMProviderClient
from app.llm_logic.tools import build_gemini_tools


class GeminiProviderClient(LLMProviderClient):
    def __init__(self, client: Any, model: str, temperature: float) -> None:
        self.client = client
        self.model = model
        self.temperature = temperature

    async def chat(
        self,
        trace: Any,
        messages: list[dict[str, Any]],
        include_tools: bool = True,
        tools_metadata: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        span = trace.span(name="gemini_chat")
        span.update(input={"messages": messages})

        try:
            # Extract system instruction
            system_instruction = None
            if messages and messages[0].get("role") == "system":
                system_instruction = messages[0].get("content")
                messages = messages[1:]

            gen_kwargs: dict[str, Any] = {"temperature": self.temperature}
            if system_instruction:
                gen_kwargs["system_instruction"] = system_instruction
            if include_tools:
                gen_kwargs["tools"] = cast(Any, build_gemini_tools())

            # Convert messages to types.Content
            contents = []
            for msg in messages:
                role = msg.get("role", "user")
                if role == "assistant":
                    role = "model"
                elif role == "tool":
                    role = "user"

                parts = [types.Part.from_text(text=str(msg.get("content", "")))]
                contents.append(types.Content(role=role, parts=parts))

            config = types.GenerateContentConfig(**gen_kwargs)
            response = await self.client.aio.models.generate_content(
                model=self.model,
                contents=contents,
                config=config,
            )

            # Extract usage
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                span.update(usage={
                    "prompt_tokens": response.usage_metadata.prompt_token_count,
                    "completion_tokens": response.usage_metadata.candidates_token_count,
                })

            part = response.candidates[0].content.parts[0]
            if part.function_call:
                result = {
                    "tool_calls": [
                        {
                            "function": {
                                "name": part.function_call.name,
                                "arguments": dict(part.function_call.args),
                            }
                        }
                    ]
                }
            else:
                result = {"content": response.text}

            span.end(output={"response": result})
            return result
        except Exception as e:
            span.update(level="ERROR", status_message=str(e))
            span.end()
            raise
