from typing import Any, cast, Optional
import json

import httpx
from google import genai
from google.genai import types
from loguru import logger
from langfuse import Langfuse

from app.config import settings
from app.repository import repo
from app.services import SalesService
from app.router import IntentRouter
from app.validators import ToolValidator, RequiredFieldsValidator

try:
    from google.adk.agents import Agent
except ImportError:  # pragma: no cover - fallback for lean runtime and tests
    class Agent:  # type: ignore[no-redef]
        def __init__(self, **kwargs: Any) -> None:
            self.tools = kwargs.get("tools", [])

# Langfuse init
langfuse = Langfuse(
    public_key=settings.LANGFUSE_PUBLIC_KEY,
    secret_key=settings.LANGFUSE_SECRET_KEY,
    host=settings.LANGFUSE_HOST,
)

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
                    (
                        "APENAS quando o usuário deseja ADICIONAR um produto ao carrinho, "
                        "fornecendo nome do produto, quantidade e preço. "
                        "NUNCA use isto para visualizar, listar ou inspecionar o carrinho."
                    ),
                    {
                        "type": "object",
                        "properties": {
                            "product_name": {"type": "string", "description": "Nome do produto"},
                            "quantity": {"type": "integer", "description": "Quantidade de itens"},
                            "price": {"type": "number", "description": "Preço unitário do produto"},
                        },
                        "required": ["product_name", "quantity", "price"],
                    },
                ),
                _tool_schema(
                    "remove_from_cart",
                    (
                        "APENAS quando o usuário deseja REMOVER um produto específico do carrinho. "
                        "NUNCA use isto para visualizar o carrinho ou esvaziar todos os itens."
                    ),
                    {
                        "type": "object",
                        "properties": {
                            "product_name": {"type": "string", "description": "Nome do produto a remover"},
                        },
                        "required": ["product_name"],
                    },
                ),
                _tool_schema(
                    "clear_cart",
                    (
                        "APENAS quando o usuário deseja ESVAZIAR todo o carrinho de uma vez. "
                        "NUNCA use isto para remover um único item ou para visualizar o carrinho."
                    ),
                    {
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                ),
                _tool_schema(
                    "checkout",
                    (
                        "APENAS quando o usuário deseja FINALIZAR a compra, PAGAR ou receber um código PIX. "
                        "NUNCA use isto apenas para visualizar o carrinho."
                    ),
                    {
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                ),
                _tool_schema(
                    "show_cart",
                    (
                        "APENAS quando o usuário deseja VER, CONSULTAR ou INSPECIONAR o conteúdo do carrinho. "
                        "NUNCA use isto para adicionar, remover, esvaziar ou finalizar a compra."
                    ),
                    {
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                ),
                _tool_schema(
                    "get_order_status",
                    (
                        "APENAS quando o usuário pergunta pelo STATUS de um pedido já realizado e fornece o ID do pedido. "
                        "Se o usuário não fornecer o ID, solicite-o antes de chamar esta ferramenta."
                    ),
                    {
                        "type": "object",
                        "properties": {
                            "order_id": {"type": "string", "description": "ID único do pedido"},
                        },
                        "required": ["order_id"],
                    },
                ),
            ]
        )
    ]

genai_client = _build_genai_client()

def _build_instruction() -> str:
    return "\n".join(
        [
            "Você é o assistente virtual de vendas da LuizaLabs.",
            "Sua missão: entender a intenção do usuário e chamar EXATAMENTE a ferramenta correspondente.",
            "",
            "### REGRAS DE ROTEAMENTO:",
            "1. Analise a intenção do usuário.",
            "2. Escolha a ferramenta apropriada com base na descrição.",
            "3. Se faltarem informações obrigatórias para uma ferramenta (ex: ID do pedido), peça-as ao usuário.",
            "4. NUNCA invente valores para argumentos.",
            "5. NUNCA chame ferramentas sem os argumentos necessários.",
            "",
            "### FERRAMENTAS E USO:",
            "- 'add_to_cart': Use para adicionar produtos (nome, quantidade, preço).",
            "- 'remove_from_cart': Use para remover produto específico pelo nome.",
            "- 'show_cart': Use para visualizar o conteúdo atual do carrinho.",
            "- 'clear_cart': Use para esvaziar todo o carrinho.",
            "- 'checkout': Use para finalizar a compra.",
            "- 'get_order_status': Use para consultar status (requer 'order_id').",
            "",
            "### EXEMPLOS (FEW-SHOT):",
            "Usuário: 'Adicione 2 tênis por 199' -> add_to_cart(product_name='tênis', quantity=2, price=199.0)",
            "Usuário: 'Remova o teclado' -> remove_from_cart(product_name='teclado')",
            "Usuário: 'Mostre o carrinho' -> show_cart()",
            "Usuário: 'Limpar carrinho' -> clear_cart()",
            "Usuário: 'Finalizar compra' -> checkout()",
            "Usuário: 'Status do pedido 123' -> get_order_status(order_id='123')",
            "Usuário: 'Status do pedido' -> (Solicite o ID)",
            "",
            "Após a execução de qualquer ferramenta, responda ao usuário confirmando a ação.",
        ]
    )

def _build_tools_metadata() -> list[dict[str, Any]]:
    return [
        {
            "name": "add_to_cart",
            "description": (
                "APENAS quando o usuário deseja ADICIONAR um produto ao carrinho, "
                "fornecendo nome do produto, quantidade e preço. "
                "NUNCA use isto para visualizar, listar ou inspecionar o carrinho."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "product_name": {"type": "string", "description": "Nome do produto"},
                    "quantity": {"type": "integer", "description": "Quantidade de itens"},
                    "price": {"type": "number", "description": "Preço unitário do produto"},
                },
                "required": ["product_name", "quantity", "price"],
            },
        },
        {
            "name": "remove_from_cart",
            "description": (
                "APENAS quando o usuário deseja REMOVER um produto específico do carrinho. "
                "NUNCA use isto para visualizar o carrinho ou esvaziar todos os itens."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "product_name": {"type": "string", "description": "Nome do produto a remover"},
                },
                "required": ["product_name"],
            },
        },
        {
            "name": "clear_cart",
            "description": (
                "APENAS quando o usuário deseja ESVAZIAR todo o carrinho de uma vez. "
                "NUNCA use isto para remover um único item ou para visualizar o carrinho."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
        {
            "name": "show_cart",
            "description": (
                "APENAS quando o usuário deseja VER, CONSULTAR ou INSPECIONAR o conteúdo do carrinho. "
                "NUNCA use isto para adicionar, remover, esvaziar ou finalizar a compra."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
        {
            "name": "checkout",
            "description": (
                "APENAS quando o usuário deseja FINALIZAR a compra, PAGAR ou receber um código PIX. "
                "NUNCA use isto apenas para visualizar o carrinho."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
        {
            "name": "get_order_status",
            "description": (
                "APENAS quando o usuário pergunta pelo STATUS de um pedido já realizado e fornece o ID do pedido. "
                "Se o usuário não fornecer o ID, solicite-o antes de chamar esta ferramenta."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "ID único do pedido"},
                },
                "required": ["order_id"],
            },
        },
    ]

class SalesAgent:
    def __init__(self) -> None:
        self._instruction = _build_instruction()
        self._tools_metadata = _build_tools_metadata()
        self.router = IntentRouter()
        self.tool_validator = ToolValidator()
        self.field_validator = RequiredFieldsValidator()
        self.agent = Agent(
            name="SalesAssistant",
            model=settings.GEMINI_MODEL,
            description="LuizaLabs sales assistant",
            instruction=self._instruction,
            tools=[
                SalesService.add_to_cart,
                SalesService.remove_from_cart,
                SalesService.clear_cart,
                SalesService.show_cart,
                SalesService.checkout,
                SalesService.get_order_status,
            ],
        )

    def _ollama_temperature(self) -> float:
        return float(getattr(settings, "OLLAMA_TEMPERATURE", 0))

    def _gemini_temperature(self) -> float:
        return float(getattr(settings, "GEMINI_TEMPERATURE", 0))

    async def _call_ollama(
        self,
        trace: Any,
        messages: list[dict[str, Any]],
        tools_metadata: list[dict[str, Any]],
    ) -> dict[str, Any]:
        span = trace.span(name="_call_ollama")
        span.update(input={"messages": messages})
        try:
            async with httpx.AsyncClient() as client:
                payload: dict[str, Any] = {
                    "model": settings.OLLAMA_MODEL,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "temperature": self._ollama_temperature(),
                        "top_p": 0.95,
                        "top_k": 40,
                    },
                }
                if tools_metadata:
                    payload["tools"] = tools_metadata
                    logger.debug(f"Ollama tools_metadata: {tools_metadata}")

                response = await client.post(
                    f"{settings.OLLAMA_BASE_URL}/api/chat",
                    json=payload,
                    timeout=240.0,
                )
                response.raise_for_status()
                data = response.json()
                logger.debug(f'Ollama full response: {data}')
                
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

    async def _call_ollama_summary(self, trace: Any, messages: list[dict[str, Any]]) -> dict[str, Any]:
        span = trace.span(name="_call_ollama_summary", input={"messages": messages})
        try:
            async with httpx.AsyncClient() as client:
                payload: dict[str, Any] = {
                    "model": settings.OLLAMA_MODEL,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "temperature": self._ollama_temperature(),
                        "top_p": 0.95,
                        "top_k": 40,
                    },
                }
                response = await client.post(
                    f"{settings.OLLAMA_BASE_URL}/api/chat",
                    json=payload,
                    timeout=240.0,
                )
                response.raise_for_status()
                data = response.json()
                result = self._parse_ollama_response(data)
                span.end(output={"response": result})
                return result
        except Exception as e:
            span.end(level="ERROR", status_message=str(e))
            raise

    def _parse_ollama_response(self, data: dict[str, Any]) -> dict[str, Any]:
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
        for i, tool_call in enumerate(tool_calls):
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
            elif isinstance(arguments, list) and arguments and isinstance(arguments[0], dict):
                arguments = arguments[0]
            normalized_args = self._normalize_tool_arguments(arguments)
            if name == "add_to_cart" and not all(k in normalized_args for k in ["product_name", "quantity", "price"]):
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
            "produto": "product_name", "produto_id": "product_name", "descricao": "product_name",
            "description": "product_name", "item_id": "product_name", "item": "product_name",
            "product": "product_name", "name": "product_name", "item_name": "product_name",
            "produto_nome": "product_name", "product_id": "product_name", "nome_produto": "product_name",
            "product_name": "product_name", "quantidade": "quantity", "qtd": "quantity",
            "quantity": "quantity", "preco": "price", "preço": "price", "price": "price",
            "valor": "price", "valor_unitario": "price", "carrinho": "session_id",
            "carrinho_id": "session_id", "cart_id": "session_id", "session_id": "session_id",
            "user_id": "session_id", "usuario_id": "session_id", "pedido_id": "order_id",
            "order_id": "order_id", "id": "order_id",
        }
        for key, value in arguments.items():
            normalized_key = alias_map.get(key, key)
            if normalized_key == "product_name" and isinstance(value, str):
                normalized[normalized_key] = value.replace("_", " ").strip()
                continue
            if normalized_key == "quantity":
                try: normalized[normalized_key] = int(value)
                except: pass
                continue
            if normalized_key == "price":
                try: normalized[normalized_key] = float(value)
                except: pass
                continue
            if normalized_key in {"session_id", "order_id"}:
                normalized[normalized_key] = str(value)
                continue
            normalized[normalized_key] = value
        return normalized

    async def _call_gemini(
        self,
        trace: Any,
        messages: list[dict[str, Any]],
        include_tools: bool = True,
    ) -> dict[str, Any]:
        span = trace.span(name="_call_gemini")
        span.update(input={"messages": messages})
        try:
            # Explicitly using the ADK Agent property for the model name 
            # to show deeper integration with the Google ADK object.
            if genai_client is None:
                raise RuntimeError("Cliente Gemini não disponível")
            
            gen_kwargs: dict[str, Any] = {"temperature": self._gemini_temperature()}
            if include_tools:
                gen_kwargs["tools"] = cast(Any, _build_gemini_tools())
            
            config = types.GenerateContentConfig(**gen_kwargs)
            response = await genai_client.aio.models.generate_content(
                model=self.agent.model,
                contents=messages,
                config=config,
            )
            logger.debug(f'Gemini full response: {response}')
            
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
            span.update(output={"response": result})
            span.end()
            return result
        except Exception as e:
            span.update(level="ERROR", status_message=str(e))
            span.end()
            raise

    async def _process_tool_calls(
        self,
        trace: Any,
        initial_message_obj: dict[str, Any],
        session: Any,
        session_id: str,
        tools_metadata: list[dict[str, Any]],
        intent: Optional[str],
    ) -> dict[str, Any]:
        span = trace.span(name="_process_tool_calls", input={"initial_message_obj": initial_message_obj})
        message_obj = initial_message_obj
        if not isinstance(message_obj, dict) or "tool_calls" not in message_obj:
            span.end()
            return message_obj
            
        max_iterations = 3
        logger.info(f"[Tool Processing] Starting tool loop | Max iterations: {max_iterations}")

        for iter_num in range(max_iterations):
            tool_calls = message_obj.get("tool_calls")
            if not tool_calls: 
                logger.info("[Tool Processing] No more tool calls, breaking loop.")
                break
            
            logger.info(f"[Tool Processing] Iteration {iter_num} | Found {len(tool_calls)} tool calls")

            for tool_call in tool_calls:
                function = tool_call.get("function", {}) or {}
                func_name = function.get("name", "").strip()
                if not func_name: 
                    logger.warning(f"[Tool Processing] Empty tool name in: {tool_call}")
                    continue
                
                # Apply ToolValidator
                original_name = func_name
                if intent:
                    func_name = self.tool_validator.validate(intent, func_name)
                    if func_name != original_name:
                        logger.info(f"[Tool Validator] Corrected tool '{original_name}' -> '{func_name}' for intent '{intent}'")
                
                args = function.get("arguments", {})
                logger.info(f"[Tool Processing] Tool: '{func_name}' | Args: {args}")

                # Apply RequiredFieldsValidator
                missing_fields = self.field_validator.validate(func_name, args)
                if missing_fields:
                    logger.warning(f"[Required Fields Validator] Missing fields for {func_name}: {missing_fields}")
                    return {"content": f"Por favor, forneça os seguintes campos: {', '.join(missing_fields)}"}

                if "session_id" not in args and func_name != "get_order_status":
                    args["session_id"] = session_id
                    
                if not hasattr(SalesService, func_name):
                    logger.error(f"[Tool Processing] Tool '{func_name}' not found in SalesService.")
                    continue

                tool_func = getattr(SalesService, func_name)
                
                logger.info(f"[Tool Execution] Calling {func_name} with {args}")
                result = await self._execute_tool_span(trace, tool_func, func_name, args)
                logger.info(f"[Tool Execution] Result from {func_name}: {result}")
                
                session.history.append({"role": "tool", "content": str(result), "name": func_name})
            
            summary_messages = [{"role": "system", "content": self._instruction}, *session.history]
            if settings.LLM_PROVIDER == "gemini":
                message_obj = await self._call_gemini(trace, summary_messages, include_tools=False)
            else:
                message_obj = await self._call_ollama_summary(trace, summary_messages)
            
            logger.debug(f"[Tool Processing] Summary loop response: {message_obj}")
            
            if not message_obj.get("tool_calls"): 
                logger.info("[Tool Processing] No further tool calls after summary loop.")
                break
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
        INTENT_TOOL_MAP = {
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
            logger.info(f"[CHAT] Input: '{message}' | Intent detected: {intent} | Provider: {settings.LLM_PROVIDER}")

            # Filter tools based on intent
            if intent and intent in INTENT_TOOL_MAP:
                allowed_tool_names = INTENT_TOOL_MAP[intent]
                tools_metadata = [t for t in self._tools_metadata if t["name"] in allowed_tool_names]
                logger.info(f"[Dynamic Tool Injection] Restricting tools to: {allowed_tool_names}")
            else:
                tools_metadata = self._tools_metadata
                logger.info("[Dynamic Tool Injection] No restriction, passing all tools.")

            session.history.append({"role": "user", "content": message})

            current_messages = [
                {"role": "system", "content": self._instruction},
                *session.history,
            ]

            if settings.LLM_PROVIDER == "gemini":
                # For Gemini, we might still want to pass all tools if possible, 
                # but for Ollama this is critical. 
                # Keeping consistent for now.
                message_obj = await self._call_gemini(trace, current_messages, include_tools=True)
            else:
                message_obj = await self._call_ollama(trace, current_messages, tools_metadata)

            logger.info(f"[LLM Response] Raw from {settings.LLM_PROVIDER}: {message_obj}")
            message_obj = self._normalize_tool_calls(message_obj, self._tools_metadata)
            logger.info(f"[LLM Response] Post-normalization: {message_obj}")

            if "tool_calls" in message_obj:
                message_obj = await self._process_tool_calls(
                    trace,
                    message_obj,
                    session,
                    session_id,
                    self._tools_metadata, # Pass full metadata for validator
                    intent,
                )

            content = message_obj.get("content", "") or "Ação concluída com sucesso."

            logger.info(f"[CHAT] Final Response: '{content}'")
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
