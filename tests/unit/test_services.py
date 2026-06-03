import pytest

from app.models import OrderStatus
from app.repository import repo
from app.services import SalesService


@pytest.fixture(autouse=True)
def clean_repo():
    repo.carts = {}
    repo.orders = {}
    repo.sessions = {}


@pytest.mark.asyncio
async def test_add_to_cart_new_item():
    resp = await SalesService.add_to_cart("s1", "Tênis", 1, 200.0)
    assert "Added 1x Tênis" in resp
    cart = await SalesService.get_or_create_cart("s1")
    assert len(cart.items) == 1
    assert cart.items[0].quantity == 1


@pytest.mark.asyncio
async def test_add_to_cart_existing_item():
    await SalesService.add_to_cart("s1", "Tênis", 1, 200.0)
    resp = await SalesService.add_to_cart("s1", "Tênis", 2, 200.0)
    assert "Updated Tênis to 3 units" in resp
    cart = await SalesService.get_or_create_cart("s1")
    assert cart.items[0].quantity == 3


@pytest.mark.asyncio
async def test_remove_from_cart():
    await SalesService.add_to_cart("s1", "Tênis", 1, 200.0)
    resp = await SalesService.remove_from_cart("s1", "Tênis")
    assert "Removed Tênis" in resp
    cart = await SalesService.get_or_create_cart("s1")
    assert len(cart.items) == 0


@pytest.mark.asyncio
async def test_clear_cart():
    await SalesService.add_to_cart("s1", "Tênis", 1, 200.0)
    resp = await SalesService.clear_cart("s1")
    assert "Cart cleared" in resp
    assert "s1" not in repo.carts


@pytest.mark.asyncio
async def test_clear_cart_without_existing_session():
    resp = await SalesService.clear_cart("missing")
    assert resp == "Cart cleared."


@pytest.mark.asyncio
async def test_checkout_success():
    await SalesService.add_to_cart("s1", "Tênis", 2, 150.0)
    resp = await SalesService.checkout("s1")
    assert "Order" in resp
    assert "Total: R$ 300.00" in resp
    assert len(repo.orders) == 1
    assert "s1" not in repo.carts


@pytest.mark.asyncio
async def test_checkout_empty_cart():
    resp = await SalesService.checkout("s2")
    assert resp == "Cart is empty."


@pytest.mark.asyncio
async def test_get_order_status():
    await SalesService.add_to_cart("s1", "Tênis", 1, 100.0)
    checkout_resp = await SalesService.checkout("s1")
    order_id = checkout_resp.split("Order ")[1].split(" placed successfully")[0]
    status = await SalesService.get_order_status(order_id)
    assert status in [OrderStatus.PROCESSING.value, OrderStatus.SHIPPED.value]


@pytest.mark.asyncio
async def test_get_order_status_not_found():
    status = await SalesService.get_order_status("missing")
    assert status == OrderStatus.NOT_FOUND.value


@pytest.mark.asyncio
async def test_get_session():
    session = await SalesService.get_session("s1")
    assert session.session_id == "s1"
    assert "s1" in repo.sessions
