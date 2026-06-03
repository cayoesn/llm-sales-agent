import secrets
import uuid

from app.models import Cart, CartItem, ConversationSession, Order, OrderStatus
from app.repository import repo


class SalesService:
    @staticmethod
    async def get_or_create_cart(session_id: str) -> Cart:
        if session_id not in repo.carts:
            repo.carts[session_id] = Cart(session_id=session_id)
        return repo.carts[session_id]

    @staticmethod
    async def add_to_cart(
        session_id: str, product_name: str, quantity: int, price: float
    ) -> str:
        cart = await SalesService.get_or_create_cart(session_id)
        product_id = product_name.lower().replace(" ", "_")

        # Update or add item
        for item in cart.items:
            if item.product_id == product_id:
                item.quantity += quantity
                repo.carts[session_id] = cart
                return f"Updated {product_name} to {item.quantity} units."

        cart.items.append(
            CartItem(
                product_id=product_id, name=product_name, quantity=quantity, price=price
            )
        )
        repo.carts[session_id] = cart
        return f"Added {quantity}x {product_name} to cart."

    @staticmethod
    async def remove_from_cart(session_id: str, product_name: str) -> str:
        cart = await SalesService.get_or_create_cart(session_id)
        product_id = product_name.lower().replace(" ", "_")
        cart.items = [item for item in cart.items if item.product_id != product_id]
        repo.carts[session_id] = cart
        return f"Removed {product_name} from cart."

    @staticmethod
    async def clear_cart(session_id: str) -> str:
        if session_id in repo.carts:
            del repo.carts[session_id]
        return "Cart cleared."

    @staticmethod
    async def checkout(session_id: str) -> str:
        cart = await SalesService.get_or_create_cart(session_id)
        if not cart.items:
            return "Cart is empty."

        total = sum(item.price * item.quantity for item in cart.items)
        order_id = str(uuid.uuid4())
        pix = f"PIX_CODE_{order_id}_{total:.2f}"

        order = Order(
            id=order_id,
            session_id=session_id,
            items=cart.items,
            total_price=total,
            pix_copy_paste=pix,
        )
        repo.orders[order_id] = order
        await SalesService.clear_cart(session_id)

        return (
            f"Order {order_id} placed successfully! Total: R$ {total:.2f}\nPIX: {pix}"
        )

    @staticmethod
    async def get_order_status(order_id: str) -> str:
        order = repo.orders.get(order_id)
        if not order:
            return OrderStatus.NOT_FOUND.value
        return secrets.choice([OrderStatus.PROCESSING.value, OrderStatus.SHIPPED.value])

    @staticmethod
    async def get_session(session_id: str) -> ConversationSession:
        if session_id not in repo.sessions:
            repo.sessions[session_id] = ConversationSession(session_id=session_id)
        return repo.sessions[session_id]
