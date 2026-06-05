from typing import Any, cast


def get_tools_metadata() -> list[dict[str, Any]]:
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
                    "product_name": {
                        "type": "string",
                        "description": "Nome do produto",
                    },
                    "quantity": {
                        "type": "integer",
                        "description": "Quantidade de itens",
                    },
                    "price": {
                        "type": "number",
                        "description": "Preço unitário do produto",
                    },
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
                    "product_name": {
                        "type": "string",
                        "description": "Nome do produto a remover",
                    },
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


def build_gemini_tools() -> list[Any]:
    from google.genai import types

    return [
        types.Tool(
            function_declarations=[
                types.FunctionDeclaration(
                    name=meta["name"],
                    description=meta["description"],
                    parameters=cast(Any, meta["parameters"]),
                )
                for meta in get_tools_metadata()
            ]
        )
    ]
