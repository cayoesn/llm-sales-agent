from typing import Any, cast

import httpx
from google import genai
from google.genai import types
from loguru import logger

from app.config import settings
from app.repository import repo
from app.services import SalesService

try:
    from google.adk.agents import Agent
except ImportError:  # pragma: no cover - fallback for lean runtime and tests

    class Agent:  # type: ignore[no-redef]
        def __init__(self, **kwargs: Any) -> None:
            self.tools = kwargs.get("tools", [])


def _build_langfuse() -> Any:
    try:
        from langfuse import Langfuse
    except ImportError:  # pragma: no cover - optional telemetry
        return None

    if not (settings.LANGFUSE_PUBLIC_KEY and settings.LANGFUSE_SECRET_KEY):
        return None

    try:
        return Langfuse(
            public_key=settings.LANGFUSE_PUBLIC_KEY,
            secret_key=settings.LANGFUSE_SECRET_KEY,
            host=settings.LANGFUSE_HOST,
        )
    except Exception:
        return None


def _build_genai_client() -> Any:
    try:
        if settings.GEMINI_API_KEY:
            return genai.Client(api_key=settings.GEMINI_API_KEY)
        return genai.Client()
    except Exception:
        return None


def _tool_schema(
    name: str, description: str, parameters: dict[str, Any]
) -> types.FunctionDeclaration:
    return types.FunctionDeclaration(
        name=name,
        description=description,
        parameters=cast(Any, parameters),
    )


def _build_gemini_tools() -> list[types.Tool]:
    return [
        types.Tool(
            function_declarations=[
                _tool_schema(
                    "add_to_cart",
                    "Adds a product to the cart.",
                    {
                        "type": "object",
                        "properties": {
                            "session_id": {"type": "string"},
                            "product_name": {"type": "string"},
                            "quantity": {"type": "integer"},
                            "price": {"type": "number"},
                        },
                        "required": ["session_id", "product_name", "quantity", "price"],
                    },
                ),
                _tool_schema(
                    "remove_from_cart",
                    "Removes a product from the cart.",
                    {
                        "type": "object",
                        "properties": {
                            "session_id": {"type": "string"},
                            "product_name": {"type": "string"},
                        },
                        "required": ["session_id", "product_name"],
                    },
                ),
                _tool_schema(
                    "clear_cart",
                    "Clears the user's cart.",
                    {
                        "type": "object",
                        "properties": {
                            "session_id": {"type": "string"},
                        },
                        "required": ["session_id"],
                    },
                ),
                _tool_schema(
                    "checkout",
                    "Completes the purchase and generates the PIX code.",
                    {
                        "type": "object",
                        "properties": {
                            "session_id": {"type": "string"},
                        },
                        "required": ["session_id"],
                    },
                ),
                _tool_schema(
                    "get_order_status",
                    "Checks the status of an order.",
                    {
                        "type": "object",
                        "properties": {
                            "order_id": {"type": "string"},
                        },
                        "required": ["order_id"],
                    },
                ),
            ]
        )
    ]


langfuse = _build_langfuse()
genai_client = _build_genai_client()


class SalesAgent:
    def __init__(self) -> None:
        instruction = "\n".join(
            [
                "You are the virtual sales assistant for LuizaLabs.",
                "Your mission is to help customers with their shopping cart.",
                "",
                "WORKFLOW:",
                "1. Understand what the user wants.",
                "2. Call the appropriate tool when needed.",
                "3. Respond politely in English confirming the action.",
                "",
                "RULES:",
                "- If the user wants to buy or add something, use 'add_to_cart'.",
                "- If the user wants to remove something, use 'remove_from_cart'.",
                "- To check an order status, ask for the order ID if it is missing.",
                "- Use 'get_order_status' to look up the order.",
                "- Always generate the PIX code during checkout.",
            ]
        )

        self.agent = Agent(
            name="SalesAssistant",
            model=settings.GEMINI_MODEL,
            description="LuizaLabs sales assistant",
            instruction=instruction,
            tools=[
                SalesService.add_to_cart,
                SalesService.remove_from_cart,
                SalesService.clear_cart,
                SalesService.checkout,
                SalesService.get_order_status,
            ],
        )

    async def _call_ollama(
        self,
        messages: list[dict[str, Any]],
        tools_metadata: list[dict[str, Any]],
    ) -> dict[str, Any]:
        async with httpx.AsyncClient() as client:
            payload = {
                "model": settings.OLLAMA_MODEL,
                "messages": messages,
                "stream": False,
                "tools": tools_metadata,
            }
            response = await client.post(
                f"{settings.OLLAMA_BASE_URL}/api/chat",
                json=payload,
                timeout=60.0,
            )
            response.raise_for_status()
            return response.json()["message"]

    async def _call_gemini(
        self,
        messages: list[dict[str, Any]],
        tools_metadata: list[dict[str, Any]],
    ) -> dict[str, Any]:
        _ = tools_metadata
        if genai_client is None:
            raise RuntimeError("Gemini client is not available")
        config = types.GenerateContentConfig(tools=cast(Any, _build_gemini_tools()))
        response = await genai_client.aio.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=messages,
            config=config,
        )

        part = response.candidates[0].content.parts[0]
        if part.function_call:
            function_call = part.function_call
            return {
                "tool_calls": [
                    {
                        "function": {
                            "name": function_call.name,
                            "arguments": dict(function_call.args),
                        }
                    }
                ]
            }

        return {"content": response.text}

    async def chat(self, session_id: str, message: str) -> str:
        session = await SalesService.get_session(session_id)
        trace = None
        try:
            if langfuse:
                trace = langfuse.trace(
                    name=f"agent-loop-{settings.LLM_PROVIDER}",
                    user_id=session_id,
                    session_id=session_id,
                )
        except Exception as error:
            logger.debug(f"Langfuse trace skipped: {error}")

        try:
            tools_metadata: list[dict[str, Any]] = []
            for tool in self.agent.tools:
                name = getattr(tool, "name", tool.__name__)
                description = getattr(tool, "description", tool.__doc__ or "")
                parameters = getattr(tool, "parameters", {})
                tools_metadata.append(
                    {
                        "name": name,
                        "description": description,
                        "parameters": parameters,
                    }
                )

            span = None
            if trace:
                span = trace.span(
                    name="llm-call",
                    input={"provider": settings.LLM_PROVIDER, "message": message},
                )

            current_messages = session.history + [{"role": "user", "content": message}]

            generation = None
            if trace:
                generation = trace.generation(
                    name=f"llm-call-{settings.LLM_PROVIDER}",
                    model=settings.GEMINI_MODEL if settings.LLM_PROVIDER == "gemini" else settings.OLLAMA_MODEL,
                    input=current_messages,
                )

            if settings.LLM_PROVIDER == "gemini":
                message_obj = await self._call_gemini(current_messages, tools_metadata)
            else:
                message_obj = await self._call_ollama(current_messages, tools_metadata)

            if generation:
                generation.end(output=message_obj)

            if "tool_calls" in message_obj:
                for tool_call in message_obj["tool_calls"]:
                    func_name = tool_call["function"]["name"]
                    args = tool_call["function"]["arguments"]

                    logger.info(
                        f"ADK Agent ({settings.LLM_PROVIDER}) calling tool: {func_name}"
                    )

                    tool_span = None
                    if trace:
                        tool_span = trace.span(
                            name=f"tool-call-{func_name}",
                            input=args,
                        )

                    tool_func = getattr(SalesService, func_name)
                    if "session_id" not in args:
                        args["session_id"] = session_id

                    result = await tool_func(**args)

                    if tool_span:
                        tool_span.end(output=str(result))

                    session.history.append({"role": "user", "content": message})
                    session.history.append(
                        {
                            "role": "tool",
                            "content": str(result),
                            "name": func_name,
                        }
                    )

                    final_generation = None
                    if trace:
                        final_generation = trace.generation(
                            name=f"llm-call-final-{settings.LLM_PROVIDER}",
                            model=settings.GEMINI_MODEL if settings.LLM_PROVIDER == "gemini" else settings.OLLAMA_MODEL,
                            input=session.history,
                        )

                    if settings.LLM_PROVIDER == "gemini":
                        final_res = await self._call_gemini(
                            session.history, tools_metadata
                        )
                    else:
                        final_res = await self._call_ollama(session.history, [])

                    if final_generation:
                        final_generation.end(output=final_res)

                    content = final_res.get("content", "Action completed successfully.")
            else:
                content = message_obj.get("content", "")
                session.history.append({"role": "user", "content": message})

            session.history.append({"role": "assistant", "content": content})
            repo.sessions[session_id] = session
            if span:
                span.end(output=content)
            return content

        except Exception as error:
            logger.error(f"Error in {settings.LLM_PROVIDER} Agent: {error}")
            if trace:
                trace.update(status_message=str(error))
            return "Sorry, there was a problem processing your request."
