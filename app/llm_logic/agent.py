import json
from typing import Any

from langfuse import Langfuse
from loguru import logger

from app.config import settings
from app.llm_logic.providers.base import LLMProviderClient
from app.llm_logic.providers.gemini import GeminiProviderClient
from app.llm_logic.providers.groq import GroqProviderClient
from app.llm_logic.providers.ollama import OllamaProviderClient
from app.llm_logic.tools import get_tools_metadata
from app.llm_logic.validators import RequiredFieldsValidator, ToolValidator
from app.repository import repo
from app.router import IntentRouter
from app.services import SalesService

# Langfuse init
langfuse = Langfuse(
    public_key=settings.LANGFUSE_PUBLIC_KEY,
    secret_key=settings.LANGFUSE_SECRET_KEY,
    host=settings.LANGFUSE_HOST,
)


def _build_genai_client() -> Any:
    try:
        from google import genai

        if settings.GEMINI_API_KEY:
            return genai.Client(api_key=settings.GEMINI_API_KEY)
        return genai.Client()
    except Exception:
        return None


class SalesAgent:
    def __init__(self) -> None:
        self._tools_metadata = get_tools_metadata()
        self.router = IntentRouter()
        self.tool_validator = ToolValidator()
        self.field_validator = RequiredFieldsValidator()
        self.provider: LLMProviderClient

        # Provider setup
        if settings.LLM_PROVIDER == "gemini":
            self.provider = GeminiProviderClient(
                client=_build_genai_client(),
                model=settings.GEMINI_MODEL,
                temperature=float(getattr(settings, "GEMINI_TEMPERATURE", 0)),
            )
        elif settings.LLM_PROVIDER == "groq":
            self.provider = GroqProviderClient(
                api_key=settings.GROQ_API_KEY or "",
                base_url=settings.GROQ_BASE_URL,
                model=settings.GROQ_MODEL,
                temperature=float(getattr(settings, "GROQ_TEMPERATURE", 0)),
            )
        else:
            self.provider = OllamaProviderClient(
                base_url=settings.OLLAMA_BASE_URL,
                model=settings.OLLAMA_MODEL,
                temperature=float(getattr(settings, "OLLAMA_TEMPERATURE", 0)),
            )

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
        for _i, tool_call in enumerate(tool_calls):
            function = tool_call.get("function", {}) or {}
            name = function.get("name") or ""
            if not name and isinstance(function.get("index"), int):
                index = function["index"]
                if 0 <= index < len(tools_metadata):
                    name = tools_metadata[index]["name"]
            if not name and len(tools_metadata) == 1:
                name = tools_metadata[0]["name"]
            arguments = function.get("arguments", {}) or {}
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except json.JSONDecodeError:
                    arguments = {}
            elif (
                isinstance(arguments, list)
                and arguments
                and isinstance(arguments[0], dict)
            ):
                arguments = arguments[0]
            normalized_args = self._normalize_tool_arguments(arguments)
            if name == "add_to_cart" and not all(
                k in normalized_args for k in ["product_name", "quantity", "price"]
            ):
                name = "show_cart"
                normalized_args = {}
            function["name"] = name
            function["arguments"] = normalized_args
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
            "product": "product_name",
            "name": "product_name",
            "item_name": "product_name",
            "produto_nome": "product_name",
            "product_id": "product_name",
            "nome_produto": "product_name",
            "product_name": "product_name",
            "quantidade": "quantity",
            "qtd": "quantity",
            "quantity": "quantity",
            "preco": "price",
            "preço": "price",
            "price": "price",
            "valor": "price",
            "valor_unitario": "price",
            "carrinho": "session_id",
            "carrinho_id": "session_id",
            "cart_id": "session_id",
            "session_id": "session_id",
            "user_id": "session_id",
            "usuario_id": "session_id",
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
                except (ValueError, TypeError):
                    pass
                continue
            if normalized_key == "price":
                try:
                    normalized[normalized_key] = float(value)
                except (ValueError, TypeError):
                    pass
                continue
            if normalized_key in {"session_id", "order_id"}:
                normalized[normalized_key] = str(value)
                continue
            normalized[normalized_key] = value
        return normalized

    async def _process_tool_calls(
        self,
        trace: Any,
        initial_message_obj: dict[str, Any],
        session: Any,
        session_id: str,
        tools_metadata: list[dict[str, Any]],
        intent: str | None,
    ) -> dict[str, Any]:
        span = trace.span(
            name="_process_tool_calls",
            input={"initial_message_obj": initial_message_obj},
        )
        message_obj = initial_message_obj
        if not isinstance(message_obj, dict) or "tool_calls" not in message_obj:
            span.end()
            return message_obj

        max_iterations = 3
        logger.info(
            f"[Tool Processing] Starting tool loop | Max iterations: {max_iterations}"
        )

        for _iter_num in range(max_iterations):
            tool_calls = message_obj.get("tool_calls")
            if not tool_calls:
                break

            for tool_call in tool_calls:
                function = tool_call.get("function", {}) or {}
                func_name = function.get("name", "").strip()
                if not func_name:
                    continue

                # Apply ToolValidator
                original_name = func_name
                if intent:
                    func_name = self.tool_validator.validate(intent, func_name)
                    if func_name != original_name:
                        logger.info(
                            f"[Tool Validator] Corrected tool '{original_name}' -> '{func_name}' for intent '{intent}'"
                        )

                args = function.get("arguments", {})

                # Apply RequiredFieldsValidator
                missing_fields = self.field_validator.validate(func_name, args)
                if missing_fields:
                    return {
                        "content": f"Por favor, forneça os seguintes campos: {', '.join(missing_fields)}"
                    }

                if "session_id" not in args and func_name != "get_order_status":
                    args["session_id"] = session_id

                if not hasattr(SalesService, func_name):
                    continue

                tool_func = getattr(SalesService, func_name)

                result = await self._execute_tool_span(
                    trace, tool_func, func_name, args
                )

                session.history.append(
                    {
                        "role": "tool",
                        "content": f"[Resultado de {func_name}]: {result}",
                        "name": func_name,
                    }
                )

            summary_messages = [
                {
                    "role": "system",
                    "content": "Você é o assistente virtual de vendas da LuizaLabs.",
                },
                *session.history,
                {
                    "role": "user",
                    "content": (
                        "As ferramentas acima já foram executadas e os resultados estão no histórico. "
                        "Responda ao usuário em linguagem natural com base nesses resultados. "
                        "NÃO chame nenhuma ferramenta adicional."
                    ),
                },
            ]

            message_obj = await self.provider.chat(
                trace, summary_messages, include_tools=False
            )
            message_obj = self._normalize_tool_calls(message_obj, tools_metadata)

            if not message_obj.get("tool_calls"):
                span.end(output={"final_response": message_obj})
                return message_obj

        span.end(output={"final_response": message_obj})
        return message_obj

    async def _execute_tool_span(self, trace: Any, tool_func, func_name, args):
        span = trace.span(name=f"tool_{func_name}", input={"args": args})
        try:
            result = await tool_func(**args)
            span.end(output={"result": result})
            return result
        except Exception as e:
            span.end(level="ERROR", status_message=str(e))
            raise

    async def chat(self, session_id: str, message: str) -> str:
        trace = langfuse.trace(name="chat_request", session_id=session_id)
        trace.update(input={"message": message})
        session = await SalesService.get_session(session_id)

        # Define intent to tool map for dynamic injection
        intent_tool_map = {
            "show_cart": ["show_cart"],
            "add_to_cart": ["add_to_cart"],
            "remove_from_cart": ["remove_from_cart"],
            "clear_cart": ["clear_cart"],
            "checkout": ["checkout"],
            "get_order_status": ["get_order_status"],
        }

        try:
            # Detect intent
            intent = self.router.get_intent(message)

            # Filter tools based on intent
            if intent and intent in intent_tool_map:
                allowed_tool_names = intent_tool_map[intent]
                tools_metadata = [
                    t for t in self._tools_metadata if t["name"] in allowed_tool_names
                ]
            else:
                tools_metadata = self._tools_metadata

            session.history.append({"role": "user", "content": message})

            current_messages = [
                {
                    "role": "system",
                    "content": "Você é o assistente virtual de vendas da LuizaLabs.",
                },
                *session.history,
            ]

            message_obj = await self.provider.chat(
                trace,
                current_messages,
                include_tools=True,
                tools_metadata=tools_metadata,
            )
            message_obj = self._normalize_tool_calls(message_obj, self._tools_metadata)

            if "tool_calls" in message_obj:
                message_obj = await self._process_tool_calls(
                    trace,
                    message_obj,
                    session,
                    session_id,
                    self._tools_metadata,
                    intent,
                )

            content = message_obj.get("content", "") or "Ação concluída com sucesso."

            session.history.append({"role": "assistant", "content": content})
            repo.sessions[session_id] = session
            trace.update(output={"response": content})
            return content

        except Exception as error:
            logger.exception(f"[CHAT] Error processing request: {error}")
            trace.update(level="ERROR", status_message=str(error))
            return "Desculpe, ocorreu um problema ao processar sua solicitação."
        finally:
            langfuse.flush()
