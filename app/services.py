import secrets
import uuid

from app.llm_logic.graph_rag import graph_rag_engine
from app.llm_logic.long_term_memory import memory_engine
from app.llm_logic.negotiation_fsm import negotiation_fsm
from app.models import Cart, CartItem, ConversationSession, Order, OrderStatus
from app.repository import repo


class SalesService:
    @staticmethod
    async def get_or_create_cart(session_id: str) -> Cart:
        """Retrieve the existing cart or create a new one for the user session."""
        if session_id not in repo.carts:
            repo.carts[session_id] = Cart(session_id=session_id)
        return repo.carts[session_id]

    @staticmethod
    async def add_to_cart(
        session_id: str, product_name: str, quantity: int, price: float = 0.0
    ) -> str:
        """Add a product to the cart with name, quantity, and price."""
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
        return f"Added {quantity}x {product_name} to the cart."

    @staticmethod
    async def remove_from_cart(session_id: str, product_name: str) -> str:
        """Remove a specific product from the cart."""
        cart = await SalesService.get_or_create_cart(session_id)
        product_id = product_name.lower().replace(" ", "_")
        cart.items = [item for item in cart.items if item.product_id != product_id]
        repo.carts[session_id] = cart
        return f"Removed {product_name} from the cart."

    @staticmethod
    async def clear_cart(session_id: str) -> str:
        """Clear all items from the user's cart."""
        if session_id in repo.carts:
            del repo.carts[session_id]
        return "Cart cleared."

    @staticmethod
    async def show_cart(session_id: str) -> str:
        """Display the current cart items and accumulated total."""
        cart = await SalesService.get_or_create_cart(session_id)
        if not cart.items:
            return "Your cart is empty."

        lines = []
        total = 0.0
        for item in cart.items:
            item_total = item.price * item.quantity
            total += item_total
            lines.append(
                f"{item.quantity}x {item.name} - ${item.price:.2f} each - Total ${item_total:.2f}"
            )

        lines.append(f"Cart total: ${total:.2f}")
        return "\n".join(lines)

    @staticmethod
    async def checkout(session_id: str) -> str:
        """Complete the order and generate a PIX payment code."""
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

        return f"Order {order_id} placed successfully! Total: ${total:.2f}\nPIX: {pix}"

    @staticmethod
    async def get_order_status(order_id: str) -> str:
        """Check the status of an order using the order ID."""
        order = repo.orders.get(order_id)
        if not order:
            return OrderStatus.NOT_FOUND.value
        return secrets.choice([OrderStatus.PROCESSING.value, OrderStatus.SHIPPED.value])

    @staticmethod
    async def get_session(session_id: str) -> ConversationSession:
        """Retrieve or create a conversation session for the user."""
        if session_id not in repo.sessions:
            repo.sessions[session_id] = ConversationSession(session_id=session_id)
        return repo.sessions[session_id]

    @staticmethod
    async def search_catalog_graph_rag(query: str) -> str:
        """Search products using Hybrid Graph-RAG with Knowledge Graph expansion and RRF."""
        results = graph_rag_engine.search_hybrid(query, top_k=3)
        if not results:
            return "No products found in the catalog matching your search."

        formatted_lines = []
        for prod in results:
            line = (
                f"📦 {prod['name']} - ${prod['price']:.2f}\n"
                f"  Description: {prod['description']}"
            )
            if prod.get("graph_relations"):
                relations = ", ".join(
                    [
                        f"{r['related_product']} ({r['relation']})"
                        for r in prod["graph_relations"]
                    ]
                )
                line += f"\n  💡 Related Items/Accessories: {relations}"
            formatted_lines.append(line)

        return "\n\n".join(formatted_lines)

    @staticmethod
    async def apply_negotiated_discount(
        session_id: str, requested_discount_percent: float, payment_method: str = "PIX"
    ) -> str:
        """Apply a negotiated discount to the cart with strict FSM validation."""
        cart = await SalesService.get_or_create_cart(session_id)
        if not cart.items:
            return "Cart is empty. Add products before negotiating discounts."

        cart_total = sum(item.price * item.quantity for item in cart.items)
        approval = negotiation_fsm.evaluate_discount_request(
            cart_total=cart_total,
            requested_discount_percent=requested_discount_percent,
            payment_method=payment_method,
        )

        return (
            f"{approval.reason}\n"
            f"Original Total: ${cart_total:.2f} -> Discounted Total: ${approval.final_price:.2f}"
        )

    @staticmethod
    async def get_personalized_recommendations(session_id: str) -> str:
        """Generate personalized recommendations using Long-Term Memory and the Product Knowledge Graph."""
        memory_engine.get_or_create_profile(session_id)
        cart = await SalesService.get_or_create_cart(session_id)

        cart_product_ids = [item.product_id for item in cart.items]
        recommendations = graph_rag_engine.get_bundle_recommendations(cart_product_ids)

        if not recommendations:
            return (
                "Add products to your cart to view recommended bundles and accessories!"
            )

        lines = ["🎯 Personalized Recommendations and Bundle Discounts:"]
        for rec in recommendations:
            lines.append(
                f"- For your cart item, we recommend: {rec['recommended_product_name']} "
                f"for ${rec['special_price']:.2f} ({rec['discount_percent']}% discount)"
            )

        return "\n".join(lines)
