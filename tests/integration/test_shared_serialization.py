"""Integration tests for JSON serialization utilities.

Tests serialization and deserialization of complex types.
"""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from shared.utils.serialization import (
    JSONEncoder,
    deserialize,
    json_decoder_hook,
    serialize,
    serialize_dict,
    serialize_value,
)


class TestJSONEncoder:
    """Tests for custom JSON encoder."""

    def test_encode_datetime(self):
        """Test encoding datetime objects."""
        import json

        dt = datetime(2024, 6, 15, 12, 30, 45, tzinfo=UTC)
        result = json.dumps({"date": dt}, cls=JSONEncoder)

        assert '"__type__": "datetime"' in result
        assert "2024-06-15" in result

    def test_encode_uuid(self):
        """Test encoding UUID objects."""
        import json

        uid = uuid4()
        result = json.dumps({"id": uid}, cls=JSONEncoder)

        assert '"__type__": "uuid"' in result
        assert str(uid) in result

    def test_encode_decimal(self):
        """Test encoding Decimal objects."""
        import json

        amount = Decimal("19.99")
        result = json.dumps({"amount": amount}, cls=JSONEncoder)

        assert '"__type__": "decimal"' in result
        assert "19.99" in result

    def test_encode_regular_types(self):
        """Test that regular types are encoded normally."""
        import json

        data = {"string": "hello", "number": 42, "list": [1, 2, 3]}
        result = json.dumps(data, cls=JSONEncoder)

        assert '"string": "hello"' in result
        assert '"number": 42' in result


class TestJsonDecoderHook:
    """Tests for JSON decoder hook."""

    def test_decode_datetime(self):
        """Test decoding datetime from type marker."""
        obj = {"__type__": "datetime", "value": "2024-06-15T12:30:45+00:00"}

        result = json_decoder_hook(obj)

        assert isinstance(result, datetime)
        assert result.year == 2024
        assert result.month == 6
        assert result.day == 15

    def test_decode_uuid(self):
        """Test decoding UUID from type marker."""
        uid = uuid4()
        obj = {"__type__": "uuid", "value": str(uid)}

        result = json_decoder_hook(obj)

        assert isinstance(result, UUID)
        assert result == uid

    def test_decode_decimal(self):
        """Test decoding Decimal from type marker."""
        obj = {"__type__": "decimal", "value": "19.99"}

        result = json_decoder_hook(obj)

        assert isinstance(result, Decimal)
        assert result == Decimal("19.99")

    def test_decode_regular_dict(self):
        """Test that regular dicts are returned unchanged."""
        obj = {"name": "test", "value": 42}

        result = json_decoder_hook(obj)

        assert result == obj


class TestSerialize:
    """Tests for serialize function."""

    def test_serialize_simple_data(self):
        """Test serializing simple data."""
        data = {"name": "test", "count": 5}

        result = serialize(data)

        assert isinstance(result, str)
        assert "test" in result
        assert "5" in result

    def test_serialize_with_datetime(self):
        """Test serializing data with datetime."""
        dt = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        data = {"created_at": dt}

        result = serialize(data)

        assert "datetime" in result
        assert "2024-01-01" in result

    def test_serialize_with_uuid(self):
        """Test serializing data with UUID."""
        uid = uuid4()
        data = {"id": uid}

        result = serialize(data)

        assert "uuid" in result
        assert str(uid) in result

    def test_serialize_with_decimal(self):
        """Test serializing data with Decimal."""
        data = {"price": Decimal("99.99")}

        result = serialize(data)

        assert "decimal" in result
        assert "99.99" in result

    def test_serialize_nested_data(self):
        """Test serializing nested data structures."""
        data = {
            "order": {
                "id": uuid4(),
                "total": Decimal("150.00"),
                "created_at": datetime.now(UTC),
            }
        }

        result = serialize(data)

        assert isinstance(result, str)


class TestDeserialize:
    """Tests for deserialize function."""

    def test_deserialize_simple_data(self):
        """Test deserializing simple data."""
        json_str = '{"name": "test", "count": 5}'

        result = deserialize(json_str)

        assert result["name"] == "test"
        assert result["count"] == 5

    def test_deserialize_with_datetime(self):
        """Test deserializing data with datetime."""
        json_str = '{"created_at": {"__type__": "datetime", "value": "2024-01-01T12:00:00+00:00"}}'

        result = deserialize(json_str)

        assert isinstance(result["created_at"], datetime)
        assert result["created_at"].year == 2024

    def test_deserialize_with_uuid(self):
        """Test deserializing data with UUID."""
        uid = uuid4()
        json_str = f'{{"id": {{"__type__": "uuid", "value": "{uid}"}}}}'

        result = deserialize(json_str)

        assert isinstance(result["id"], UUID)
        assert result["id"] == uid

    def test_deserialize_with_decimal(self):
        """Test deserializing data with Decimal."""
        json_str = '{"price": {"__type__": "decimal", "value": "99.99"}}'

        result = deserialize(json_str)

        assert isinstance(result["price"], Decimal)
        assert result["price"] == Decimal("99.99")


class TestRoundTrip:
    """Tests for serialize/deserialize round-trip consistency."""

    def test_roundtrip_datetime(self):
        """Test datetime round-trip."""
        original = {"timestamp": datetime(2024, 6, 15, 12, 30, 45, tzinfo=UTC)}

        json_str = serialize(original)
        restored = deserialize(json_str)

        assert restored["timestamp"] == original["timestamp"]

    def test_roundtrip_uuid(self):
        """Test UUID round-trip."""
        original = {"id": uuid4()}

        json_str = serialize(original)
        restored = deserialize(json_str)

        assert restored["id"] == original["id"]

    def test_roundtrip_decimal(self):
        """Test Decimal round-trip."""
        original = {"amount": Decimal("123.45")}

        json_str = serialize(original)
        restored = deserialize(json_str)

        assert restored["amount"] == original["amount"]

    def test_roundtrip_complex_data(self):
        """Test complex data round-trip."""
        original = {
            "id": uuid4(),
            "amount": Decimal("999.99"),
            "created_at": datetime(2024, 6, 15, tzinfo=UTC),
            "name": "Test Order",
            "items": [1, 2, 3],
        }

        json_str = serialize(original)
        restored = deserialize(json_str)

        assert restored["id"] == original["id"]
        assert restored["amount"] == original["amount"]
        assert restored["created_at"] == original["created_at"]
        assert restored["name"] == original["name"]
        assert restored["items"] == original["items"]


class TestSerializeValue:
    """Tests for serialize_value function."""

    def test_serialize_datetime_value(self):
        """Test serializing datetime value."""
        dt = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)

        result = serialize_value(dt)

        assert isinstance(result, str)
        assert "2024-06-15" in result

    def test_serialize_uuid_value(self):
        """Test serializing UUID value."""
        uid = uuid4()

        result = serialize_value(uid)

        assert isinstance(result, str)
        assert result == str(uid)

    def test_serialize_decimal_value(self):
        """Test serializing Decimal value."""
        amount = Decimal("19.99")

        result = serialize_value(amount)

        assert isinstance(result, str)
        assert result == "19.99"

    def test_serialize_regular_value(self):
        """Test serializing regular values."""
        assert serialize_value("hello") == "hello"
        assert serialize_value(42) == 42
        assert serialize_value([1, 2, 3]) == [1, 2, 3]


class TestSerializeDict:
    """Tests for serialize_dict function."""

    def test_serialize_dict_with_special_types(self):
        """Test serializing dict with special types."""
        data = {
            "id": uuid4(),
            "amount": Decimal("50.00"),
            "created_at": datetime(2024, 1, 1, tzinfo=UTC),
            "name": "test",
        }

        result = serialize_dict(data)

        assert isinstance(result["id"], str)
        assert isinstance(result["amount"], str)
        assert isinstance(result["created_at"], str)
        assert result["name"] == "test"

    def test_serialize_dict_preserves_keys(self):
        """Test that serialize_dict preserves all keys."""
        data = {"a": 1, "b": 2, "c": 3}

        result = serialize_dict(data)

        assert set(result.keys()) == set(data.keys())

    def test_serialize_empty_dict(self):
        """Test serializing empty dict."""
        result = serialize_dict({})

        assert result == {}
