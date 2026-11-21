import re


class IntentRouter:
    INTENTS = {
        "get_order_status": [
            r"order status",
            r"status of (?:my |the )?order",
            r"where is (?:my |the )?order",
            r"track (?:my |the )?order",
        ],
        "checkout": [
            r"checkout",
            r"complete (?:my )?purchase",
            r"pay",
            r"finish (?:my )?order",
            r"place (?:my )?order",
        ],
        "clear_cart": [r"clear.*cart", r"empty.*cart", r"delete.*cart"],
        "remove_from_cart": [
            r"remove",
            r"take.*out of.*cart",
            r"delete from cart",
        ],
        "add_to_cart": [r"add", r"put in.*cart", r"buy"],
        "show_cart": [
            r"show.*cart",
            r"view.*cart",
            r"what(?:'s| is) in.*cart",
            r"list.*cart",
            r"my cart",
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
