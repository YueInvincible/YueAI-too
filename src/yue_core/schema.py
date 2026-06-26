from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .errors import SchemaValidationError

_TYPE_MAP = {
    "object": Mapping,
    "array": Sequence,
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
    "null": type(None),
}


def validate_schema(schema: Mapping[str, Any], *, path: str = "$schema") -> None:
    expected_type = schema.get("type")
    if expected_type is not None and expected_type not in _TYPE_MAP:
        raise SchemaValidationError(f"{path}: unsupported schema type {expected_type!r}")
    properties = schema.get("properties", {})
    if not isinstance(properties, Mapping):
        raise SchemaValidationError(f"{path}.properties: expected object")
    required = schema.get("required", [])
    if not isinstance(required, list) or not all(isinstance(item, str) for item in required):
        raise SchemaValidationError(f"{path}.required: expected string array")
    unknown_required = sorted(set(required) - set(properties))
    if unknown_required:
        raise SchemaValidationError(
            f"{path}.required: keys absent from properties {unknown_required}"
        )
    for key, child in properties.items():
        if not isinstance(child, Mapping):
            raise SchemaValidationError(f"{path}.properties.{key}: expected object")
        validate_schema(child, path=f"{path}.properties.{key}")
    items = schema.get("items")
    if items is not None:
        if not isinstance(items, Mapping):
            raise SchemaValidationError(f"{path}.items: expected object")
        validate_schema(items, path=f"{path}.items")


def validate(value: Any, schema: Mapping[str, Any], *, path: str = "$") -> None:
    """Validate the JSON-Schema subset used by tool arguments."""

    expected_type = schema.get("type")
    if expected_type is not None:
        python_type = _TYPE_MAP.get(expected_type)
        if python_type is None:
            raise SchemaValidationError(f"{path}: unsupported schema type {expected_type!r}")
        if expected_type == "array":
            valid = isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))
        elif expected_type == "integer":
            valid = isinstance(value, int) and not isinstance(value, bool)
        elif expected_type == "number":
            valid = isinstance(value, (int, float)) and not isinstance(value, bool)
        else:
            valid = isinstance(value, python_type)
        if not valid:
            raise SchemaValidationError(f"{path}: expected {expected_type}")

    if "enum" in schema and value not in schema["enum"]:
        raise SchemaValidationError(f"{path}: value is not in enum")

    if isinstance(value, Mapping):
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        missing = [key for key in required if key not in value]
        if missing:
            raise SchemaValidationError(f"{path}: missing required keys {missing}")
        if schema.get("additionalProperties", True) is False:
            extras = sorted(set(value) - set(properties))
            if extras:
                raise SchemaValidationError(f"{path}: unexpected keys {extras}")
        for key, child in value.items():
            if key in properties:
                validate(child, properties[key], path=f"{path}.{key}")

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        item_schema = schema.get("items")
        if item_schema:
            for index, item in enumerate(value):
                validate(item, item_schema, path=f"{path}[{index}]")

    if isinstance(value, str):
        minimum = schema.get("minLength")
        maximum = schema.get("maxLength")
        if minimum is not None and len(value) < minimum:
            raise SchemaValidationError(f"{path}: shorter than minLength")
        if maximum is not None and len(value) > maximum:
            raise SchemaValidationError(f"{path}: longer than maxLength")
