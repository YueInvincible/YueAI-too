"""YueAI core service."""

from .app import YueCore
from .contracts import CORE_API_VERSION
from .version import VERSION

__all__ = ["CORE_API_VERSION", "VERSION", "YueCore"]
__version__ = VERSION
