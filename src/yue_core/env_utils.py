from __future__ import annotations

import os
from contextlib import contextmanager
from collections.abc import Iterator


@contextmanager
def temporarily_unset_env(name: str) -> Iterator[None]:
    had_value = name in os.environ
    previous = os.environ.get(name)
    if had_value:
        os.environ.pop(name, None)
    try:
        yield
    finally:
        if had_value and previous is not None:
            os.environ[name] = previous
