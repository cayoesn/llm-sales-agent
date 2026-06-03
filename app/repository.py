from collections.abc import MutableMapping
from typing import Generic, TypeVar
import redis
from pydantic import BaseModel

from app.config import settings
from app.models import Cart, ConversationSession, Order

T = TypeVar("T", bound=BaseModel)


class RedisDict(MutableMapping, Generic[T]):
    def __init__(self, client: redis.Redis, prefix: str, model_cls: type[T]):
        self.client = client
        self.prefix = prefix
        self.model_cls = model_cls

    def _key(self, key: str) -> str:
        return f"{self.prefix}:{key}"

    def __getitem__(self, key: str) -> T:
        data = self.client.get(self._key(key))
        if data is None:
            raise KeyError(key)
        # Decode bytes if needed
        data_str = data.decode("utf-8") if isinstance(data, bytes) else data
        return self.model_cls.model_validate_json(data_str)

    def __setitem__(self, key: str, value: T) -> None:
        self.client.set(self._key(key), value.model_dump_json())

    def __delitem__(self, key: str) -> None:
        if not self.client.delete(self._key(key)):
            raise KeyError(key)

    def __iter__(self):
        pattern = f"{self.prefix}:*"
        for k in self.client.scan_iter(pattern):
            k_str = k.decode("utf-8") if isinstance(k, bytes) else k
            yield k_str[len(self.prefix) + 1 :]

    def __len__(self) -> int:
        pattern = f"{self.prefix}:*"
        return len(list(self.client.scan_iter(pattern)))

    def clear(self) -> None:
        pattern = f"{self.prefix}:*"
        for k in self.client.scan_iter(pattern):
            self.client.delete(k)


class RedisRepository:
    def __init__(self, redis_url: str):
        self.client = redis.from_url(redis_url)
        self.carts = RedisDict(self.client, "cart", Cart)
        self.orders = RedisDict(self.client, "order", Order)
        self.sessions = RedisDict(self.client, "session", ConversationSession)


class InMemoryRepository:
    def __init__(self):
        self.carts: dict[str, Cart] = {}
        self.orders: dict[str, Order] = {}
        self.sessions: dict[str, ConversationSession] = {}


import os
import sys

# Instantiate repository based on settings
if settings.REDIS_URL and "pytest" not in sys.modules and not os.getenv("TESTING"):
    repo = RedisRepository(settings.REDIS_URL)  # type: ignore[assignment]
else:
    repo = InMemoryRepository()  # type: ignore[assignment]

