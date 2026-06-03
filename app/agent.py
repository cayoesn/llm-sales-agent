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
                    "show_cart",
                    "Shows the current cart contents.",
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
                "- If the user wants to see the cart contents, use 'show_cart'.",
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
                SalesService.show_cart,
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
            }
            if tools_metadata:
                payload["tools"] = tools_metadata
                logger.debug(f"Ollama tools_metadata: {tools_metadata}")
            
            response = await client.post(
                f"{settings.OLLAMA_BASE_URL}/api/chat",
                json=payload,
                timeout=60.0,
            )
            response.raise_for_status()
            data = response.json()
            logger.debug(f"Ollama request payload: {payload}")
            logger.debug(f"Ollama response raw data: {data}")
            message = self._parse_ollama_response(data)
            logger.debug(f"Ollama parsed message: {message}")
            if not message.get("content") and not message.get("tool_calls"):
                logger.warning(
                    f"Ollama response parsed to empty content. raw data={data} parsed={message}"
                )
            return message

    def _parse_ollama_response(self, data: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(data, dict):
            return {"content": str(data)}

        message = data.get("message")
        if message is None:
            message = data.get("response") or data.get("output")

        if message is None and isinstance(data.get("choices"), list):
            first_choice = data["choices"][0] if data["choices"] else None
            if isinstance(first_choice, dict):
                message = first_choice.get("message") or first_choice.get("content") or first_choice.get("response")

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

    def _normalize_tool_calls(
        self,
        message_obj: dict[str, Any],
        tools_metadata: list[dict[str, Any]],
    ) -> dict[str, Any]:
        if not isinstance(message_obj, dict) or "tool_calls" not in message_obj:
            return message_obj

        tool_calls = message_obj.get("tool_calls")
        if not isinstance(tool_calls, list):
            return message_obj

        normalized_calls: list[dict[str, Any]] = []
        for tool_call in tool_calls:
            function = tool_call.get("function", {}) or {}
            name = function.get("name") or ""
            if not name and isinstance(function.get("index"), int):
                index = function["index"]
                if 0 <= index < len(tools_metadata):
                    name = tools_metadata[index]["name"]
            if not name and len(tools_metadata) == 1:
                name = tools_metadata[0]["name"]

            function["name"] = name
            function["arguments"] = self._normalize_tool_arguments(
                function.get("arguments", {}) or {}
            )
            tool_call["function"] = function
            normalized_calls.append(tool_call)

        message_obj["tool_calls"] = normalized_calls
        return message_obj

    def _normalize_tool_arguments(self, arguments: dict[str, Any]) -> dict[str, Any]:
        normalized: dict[str, Any] = {}
        alias_map: dict[str, str] = {
            "produto": "product_name",
            "produto_id": "product_name",
            "descricao": "product_name",
            "description": "product_name",
            "item_id": "product_name",
            "item": "product_name",
            "product_id": "product_name",
            "nome_produto": "product_name",
            "product_name": "product_name",
            "quantidade": "quantity",
            "quantity": "quantity",
            "preco": "price",
            "price": "price",
            "valor": "price",
            "carrinho": "session_id",
            "carrinho_id": "session_id",
            "cart_id": "session_id",
            "session_id": "session_id",
            "pedido_id": "order_id",
            "order_id": "order_id",
            "id": "order_id",
        }

        for key, value in arguments.items():
            normalized_key = alias_map.get(key, key)

            if normalized_key == "product_name" and isinstance(value, str):
                normalized[normalized_key] = value.replace("_", " ").strip()
                continue

            if normalized_key == "quantity":
                try:
                    normalized[normalized_key] = int(value)
                    continue
                except Exception:
                    pass

            if normalized_key == "price":
                try:
                    normalized[normalized_key] = float(value)
                    continue
                except Exception:
                    pass

            if normalized_key in {"session_id", "order_id"}:
                normalized[normalized_key] = str(value)
                continue

            normalized[normalized_key] = value

        return normalized

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
            logger.debug(f"Tools metadata for {settings.LLM_PROVIDER}: {tools_metadata}")

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

            message_obj = self._normalize_tool_calls(message_obj, tools_metadata)
            logger.debug(f"Agent received message_obj: {message_obj}")
            if generation:
                generation.end(output=message_obj)

            content = ""  # Initialize to avoid UnboundLocalError
            if "tool_calls" in message_obj:
                for tool_call in message_obj["tool_calls"]:
                    func_name = tool_call.get("function", {}).get("name", "").strip()
                    
                    if not func_name:
                        logger.warning(f"Empty tool name received: {tool_call}")
                        continue
                    
                    args = tool_call.get("function", {}).get("arguments", {})

                    logger.info(
                        f"ADK Agent ({settings.LLM_PROVIDER}) calling tool: {func_name}"
                    )

                    tool_span = None
                    if trace:
                        tool_span = trace.span(
                            name=f"tool-call-{func_name}",
                            input=args,
                        )

                    if not hasattr(SalesService, func_name):
                        logger.error(f"Tool {func_name} not found in SalesService")
                        if tool_span:
                            tool_span.end(output=f"Tool {func_name} not found")
                        continue
                    
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

                    logger.debug(f"Agent received final_res: {final_res}")
                    if final_generation:
                        final_generation.end(output=final_res)

                    content = final_res.get("content", "Action completed successfully.")
                    if not content:
                        logger.warning(
                            "Final agent response is empty",
                            final_res=final_res,
                            session_history=session.history,
                        )
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
