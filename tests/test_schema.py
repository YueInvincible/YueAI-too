import unittest

from yue_core.errors import SchemaValidationError
from yue_core.schema import validate, validate_schema


class SchemaTests(unittest.TestCase):
    def test_valid_object(self):
        validate(
            {"text": "hello"},
            {
                "type": "object",
                "properties": {"text": {"type": "string"}},
                "required": ["text"],
                "additionalProperties": False,
            },
        )

    def test_rejects_extra_property(self):
        with self.assertRaises(SchemaValidationError):
            validate(
                {"text": "hello", "extra": True},
                {
                    "type": "object",
                    "properties": {"text": {"type": "string"}},
                    "additionalProperties": False,
                },
            )

    def test_bool_is_not_integer(self):
        with self.assertRaises(SchemaValidationError):
            validate(True, {"type": "integer"})

    def test_schema_rejects_unknown_required_key(self):
        with self.assertRaises(SchemaValidationError):
            validate_schema(
                {
                    "type": "object",
                    "properties": {},
                    "required": ["missing"],
                }
            )


if __name__ == "__main__":
    unittest.main()
