"""JSON serialization utilities for complex Python types.

Provides helpers for serializing and deserializing datetime, UUID, and Decimal
types to/from JSON, ensuring round-trip consistency.

Requirements: 4.6, 5.6, 6.6
"""

import json
from datetime import datetime, UTC
from decimal import Decimal
from typing import Any
from uuid import UUID


class JSONEncoder(json.JSONEncoder):
    """Custom JSON encoder supporting datetime, UUID, and Decimal types."""

    def default(self, obj: Any) -> Any:
        """Encode special types to JSON-serializable format.

        Args:
            obj: Object to encode

        Returns:
            JSON-serializable representation of the object
        """
        if isinstance(obj, datetime):
            return {"__type__": "datetime", "value": obj.isoformat()}
        if isinstance(obj, UUID):
            return {"__type__": "uuid", "value": str(obj)}
        if isinstance(obj, Decimal):
            return {"__type__": "decimal", "value": str(obj)}
        return super().default(obj)


def json_decoder_hook(obj: dict[str, Any]) -> Any:
    """Decode special types from JSON representation.

    Args:
        obj: Dictionary that may contain type markers

    Returns:
        Decoded object or original dictionary
    """
    if "__type__" in obj:
        type_name = obj["__type__"]
        value = obj["value"]

        if type_name == "datetime":
            return datetime.fromisoformat(value)
        if type_name == "uuid":
            return UUID(value)
        if type_name == "decimal":
            return Decimal(value)

    return obj


def serialize(obj: Any) -> str:
    """Serialize an object to JSON string with type preservation.

    Supports datetime, UUID, and Decimal types with round-trip consistency.

    Args:
        obj: Object to serialize

    Returns:
        JSON string representation

    Example:
        >>> from uuid import uuid4
        >>> data = {"id": uuid4(), "amount": Decimal("19.99")}
        >>> json_str = serialize(data)
        >>> restored = deserialize(json_str)
        >>> data == restored
        True
    """
    return json.dumps(obj, cls=JSONEncoder)


def deserialize(json_str: str) -> Any:
    """Deserialize a JSON string back to Python objects.

    Restores datetime, UUID, and Decimal types from their JSON representation.

    Args:
        json_str: JSON string to deserialize

    Returns:
        Deserialized Python object with proper types restored
    """
    return json.loads(json_str, object_hook=json_decoder_hook)


def serialize_value(value: Any) -> Any:
    """Convert a single value to JSON-serializable format without type markers.

    Useful for simple serialization where type information is not needed.

    Args:
        value: Value to convert

    Returns:
        JSON-serializable representation
    """
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Decimal):
        return str(value)
    return value


def serialize_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Serialize all values in a dictionary to JSON-serializable format.

    Does not include type markers - use serialize() for round-trip support.

    Args:
        data: Dictionary with potentially non-serializable values

    Returns:
        Dictionary with all values converted to JSON-serializable format
    """
    return {key: serialize_value(value) for key, value in data.items()}
