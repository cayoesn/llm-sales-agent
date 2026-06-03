from app.models import Cart, ConversationSession, Order


class InMemoryRepository:
    def __init__(self):
        self.carts: dict[str, Cart] = {}
        self.orders: dict[str, Order] = {}
        self.sessions: dict[str, ConversationSession] = {}


repo = InMemoryRepository()
