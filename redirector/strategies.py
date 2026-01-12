from abc import ABC, abstractmethod
from typing import List
import random


class _BaseStrategy(ABC):
    """Abstract base class for load balancing strategies."""

    def __init__(self, hosts: List[str]) -> None:
        """Initialize the strategy with a list of backend hosts.

        :param hosts: List of backend host addresses
        """
        if not hosts:
            raise ValueError("Host list cannot be empty")
        self._hosts = hosts

    @abstractmethod
    def next_host(self) -> str:
        """Get the next host according to the strategy.

        :returns: Host address as string
        """
        pass


class SequentialStrategy(_BaseStrategy):
    """Load balancing strategy that selects hosts sequentially in round-robin fashion."""

    def __init__(self, hosts: List[str]) -> None:
        """Initialize sequential strategy.

        :param hosts: List of backend host addresses
        """
        super().__init__(hosts)
        self._next_index = 0

    def next_host(self) -> str:
        """Get the next host in a sequential fashion.

        :returns: Host address as string
        """
        # Identify the next host
        next_host = self._hosts[self._next_index]

        # Process the index for the next call
        self._next_index = (self._next_index + 1) % len(self._hosts)

        return next_host


class RandomStrategy(_BaseStrategy):
    """Load balancing strategy that selects hosts randomly, avoiding consecutive duplicates."""

    def __init__(self, hosts: List[str]) -> None:
        """Initialize random strategy.

        :param hosts: List of backend host addresses
        """
        super().__init__(hosts)
        self._next_index = random.randint(0, len(self._hosts) - 1)

    def next_host(self) -> str:
        """Get the next host in a random fashion, avoiding same host consecutively.

        :returns: Host address as string
        """
        # Identify the next host
        next_host = self._hosts[self._next_index]

        # Process the index for the next call
        # Avoid selecting the same host consecutively if we have more than one host
        if len(self._hosts) > 1:
            next_candidate_index = self._next_index
            while next_candidate_index == self._next_index:
                next_candidate_index = random.randint(0, len(self._hosts) - 1)
            self._next_index = next_candidate_index

        return next_host


strategies = {"sequential": SequentialStrategy, "random": RandomStrategy}
