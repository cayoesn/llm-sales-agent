import re


class IntentRouter:
    INTENTS = {
        "get_order_status": [
            r"status do pedido",
            r"onde esta o pedido",
            r"rastrear pedido",
        ],
        "checkout": [r"finalizar compra", r"pagar", r"fechar pedido"],
        "clear_cart": [r"limpar.*carrinho", r"esvaziar.*carrinho", r"apagar.*carrinho"],
        "remove_from_cart": [r"remover", r"tirar do carrinho", r"excluir do carrinho"],
        "add_to_cart": [r"adicionar", r"colocar no carrinho", r"comprar"],
        "show_cart": [
            r"mostrar.*carrinho",
            r"ver.*carrinho",
            r"o que tem.*carrinho",
            r"listar.*carrinho",
            r"meu carrinho",
        ],
    }

    def get_intent(self, text: str) -> str | None:
        text = text.lower()
        for intent, patterns in self.INTENTS.items():
            for pattern in patterns:
                # Use word boundaries or just rely on search.
                # Reordering to prioritize specific over generic is key.
                if re.search(pattern, text):
                    return intent
        return None
