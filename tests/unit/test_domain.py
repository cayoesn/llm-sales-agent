from datetime import datetime

from app.models import Cart, CartItem, ConversationSession, Order, OrderStatus


def test_cart_item_creation():
    item = CartItem(product_id="p1", name="Product 1", quantity=2, price=50.0)
    assert item.product_id == "p1"
    assert item.quantity == 2
    assert item.price == 50.0


def test_cart_initialization():
    cart = Cart(session_id="s1")
    assert cart.session_id == "s1"
    assert len(cart.items) == 0
    assert isinstance(cart.created_at, datetime)


def test_order_creation():
    item = CartItem(product_id="p1", name="Product 1", quantity=1, price=100.0)
    order = Order(
        session_id="s1", items=[item], total_price=100.0, pix_copy_paste="PIX123"
    )
    assert order.session_id == "s1"
    assert order.status == OrderStatus.PROCESSING
    assert len(order.items) == 1


def test_session_initialization():
    session = ConversationSession(session_id="s1")
    assert session.session_id == "s1"
    assert session.history == []


def test_cart_items_are_not_shared():
    first_cart = Cart(session_id="s1")
    second_cart = Cart(session_id="s2")
    first_cart.items.append(
        CartItem(product_id="p1", name="Product 1", quantity=1, price=10.0)
    )

    assert second_cart.items == []


def test_session_history_is_not_shared():
    first_session = ConversationSession(session_id="s1")
    second_session = ConversationSession(session_id="s2")
    first_session.history.append({"role": "user", "content": "oi"})

    assert second_session.history == []
