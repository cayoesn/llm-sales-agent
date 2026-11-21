from typing import Any, cast


def get_tools_metadata() -> list[dict[str, Any]]:
    return [
        {
            "name": "add_to_cart",
            "description": (
                "ONLY when the user wants to ADD a product to the cart, "
                "providing product name, quantity, and price. "
                "NEVER use this to view, list, or inspect the cart."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "product_name": {
                        "type": "string",
                        "description": "Product name",
                    },
                    "quantity": {
                        "type": "integer",
                        "description": "Number of items",
                    },
                    "price": {
                        "type": "number",
                        "description": "Unit price of the product",
                    },
                },
                "required": ["product_name", "quantity", "price"],
            },
        },
        {
            "name": "remove_from_cart",
            "description": (
                "ONLY when the user wants to REMOVE a specific product from the cart. "
                "NEVER use this to view the cart or clear all items."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "product_name": {
                        "type": "string",
                        "description": "Name of the product to remove",
                    },
                },
                "required": ["product_name"],
            },
        },
        {
            "name": "clear_cart",
            "description": (
                "ONLY when the user wants to CLEAR the entire cart at once. "
                "NEVER use this to remove a single item or view the cart."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
            "produces_final_response": True,
        },
        {
            "name": "show_cart",
            "description": (
                "ONLY when the user wants to VIEW, CHECK, or INSPECT the contents of the cart. "
                "NEVER use this to add, remove, clear, or complete a purchase."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
            "produces_final_response": True,
        },
        {
            "name": "checkout",
            "description": (
                "ONLY when the user wants to COMPLETE the purchase, PAY, or receive a PIX payment code. "
                "NEVER use this just to view the cart."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
            "produces_final_response": True,
        },
        {
            "name": "get_order_status",
            "description": (
                "ONLY when the user asks for the STATUS of an already placed order and provides the order ID. "
                "The order ID is a unique alphanumeric code, usually long (e.g., '1f3db40c-efba-4efd-9603-90f8a3cc3dd7'). "
                "If the user does not provide the ID, ask for it before calling this tool."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "Unique order ID"},
                },
                "required": ["order_id"],
            },
            "produces_final_response": True,
        },
        {
            "name": "search_catalog_graph_rag",
            "description": (
                "ONLY when the user wants to SEARCH, BROWSE, or QUERY the catalog of products and accessories. "
                "Uses Hybrid Graph-RAG with the Product Knowledge Graph and RRF."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Product or category search terms",
                    },
                },
                "required": ["query"],
            },
            "produces_final_response": True,
        },
        {
            "name": "apply_negotiated_discount",
            "description": (
                "ONLY when the user REQUESTS A DISCOUNT or negotiates the cart price. "
                "Enforces margin rules with the negotiation FSM without hallucination."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "requested_discount_percent": {
                        "type": "number",
                        "description": "Requested discount percentage",
                    },
                    "payment_method": {
                        "type": "string",
                        "description": "Payment method (PIX, Credit Card)",
                    },
                },
                "required": ["requested_discount_percent"],
            },
            "produces_final_response": True,
        },
        {
            "name": "get_personalized_recommendations",
            "description": (
                "ONLY when the user asks for RECOMMENDATIONS, bundle SUGGESTIONS, or accessories for their cart. "
                "Uses Long-Term Memory and the Product Knowledge Graph."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
            "produces_final_response": True,
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
