from unittest.mock import MagicMock
import pytest
from app.repository import RedisDict, RedisRepository
from app.models import Cart


def test_redis_dict_operations():
    mock_client = MagicMock()
    cart = Cart(session_id="session123")
    mock_client.get.return_value = cart.model_dump_json().encode("utf-8")

    redis_dict = RedisDict(mock_client, "cart", Cart)

    # Test get item
    retrieved = redis_dict["session123"]
    assert retrieved.session_id == "session123"
    mock_client.get.assert_called_with("cart:session123")

    # Test set item
    redis_dict["session123"] = cart
    mock_client.set.assert_called_with("cart:session123", cart.model_dump_json())

    # Test del item
    mock_client.delete.return_value = 1
    del redis_dict["session123"]
    mock_client.delete.assert_called_with("cart:session123")

    # Test clear
    mock_client.scan_iter.return_value = [b"cart:session123"]
    redis_dict.clear()
    mock_client.delete.assert_called_with(b"cart:session123")

def test_redis_dict_getitem_keyerror():
    mock_client = MagicMock()
    mock_client.get.return_value = None
    redis_dict = RedisDict(mock_client, "cart", Cart)

    with pytest.raises(KeyError):
        _ = redis_dict["nonexistent"]

def test_redis_dict_delitem_keyerror():
    mock_client = MagicMock()
    mock_client.delete.return_value = 0
    redis_dict = RedisDict(mock_client, "cart", Cart)

    with pytest.raises(KeyError):
        del redis_dict["nonexistent"]

def test_redis_dict_iter():
    mock_client = MagicMock()
    mock_client.scan_iter.return_value = [b"cart:session1", b"cart:session2"]
    redis_dict = RedisDict(mock_client, "cart", Cart)

    keys = list(redis_dict)
    assert keys == ["session1", "session2"]
    mock_client.scan_iter.assert_called_with("cart:*")

def test_redis_dict_len():
    mock_client = MagicMock()
    mock_client.scan_iter.return_value = [b"cart:session1", b"cart:session2"]
    redis_dict = RedisDict(mock_client, "cart", Cart)

    assert len(redis_dict) == 2
    mock_client.scan_iter.assert_called_with("cart:*")
