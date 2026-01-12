from abc import ABC, abstractmethod
from typing import Tuple


class BaseHealthCheck(ABC):
    """Abstract base class for health check implementations."""

    def __init__(self) -> None:
        pass

    @abstractmethod
    def is_alive(self, host: str) -> Tuple[bool, str]:
        """Perform a healthcheck against the given host."""
        pass
