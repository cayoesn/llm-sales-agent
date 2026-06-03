import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class OrderStatus(StrEnum):
    PROCESSING = "Processando"
    SHIPPED = "Enviado"
    NOT_FOUND = "Pedido não encontrado"


class CartItem(BaseModel):
    product_id: str
    name: str
    quantity: int
    price: float


class Cart(BaseModel):
    session_id: str
    items: list[CartItem] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Order(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    items: list[CartItem]
    total_price: float
    pix_copy_paste: str
    status: OrderStatus = OrderStatus.PROCESSING
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ConversationSession(BaseModel):
    session_id: str
    history: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
