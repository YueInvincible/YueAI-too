import io
import sys
import unittest
from unittest.mock import patch

from yue_core.cli import _write_stdout_text


class CliTests(unittest.TestCase):
    def test_write_stdout_text_falls_back_to_utf8_bytes(self):
        buffer = io.BytesIO()
        stdout = io.TextIOWrapper(buffer, encoding="cp1252", errors="strict")
        with patch.object(sys, "stdout", stdout):
            _write_stdout_text("Dạ, em đây")
            stdout.flush()
        self.assertEqual(buffer.getvalue(), "Dạ, em đây\n".encode("utf-8"))


if __name__ == "__main__":
    unittest.main()
