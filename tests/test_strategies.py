"""Unit tests for load balancing strategies."""

import pytest
from redirector.strategies import SequentialStrategy, RandomStrategy, _BaseStrategy


class TestSequentialStrategy:
    """Test cases for SequentialStrategy."""

    def test_initialization_with_empty_hosts(self):
        """Test that initializing with empty host list raises ValueError."""
        with pytest.raises(ValueError, match="Host list cannot be empty"):
            SequentialStrategy([])

    def test_initialization_with_hosts(self):
        """Test successful initialization with valid host list."""
        hosts = ["host1", "host2", "host3"]
        strategy = SequentialStrategy(hosts)
        assert strategy._hosts == hosts
        assert strategy._next_index == 0

    def test_next_host_single_host(self):
        """Test sequential selection with a single host."""
        hosts = ["host1"]
        strategy = SequentialStrategy(hosts)

        # Should always return the same host
        for _ in range(5):
            assert strategy.next_host() == "host1"
            assert strategy._next_index == 0

    def test_next_host_multiple_hosts(self):
        """Test sequential selection with multiple hosts in round-robin fashion."""
        hosts = ["host1", "host2", "host3"]
        strategy = SequentialStrategy(hosts)

        # First round
        assert strategy.next_host() == "host1"
        assert strategy.next_host() == "host2"
        assert strategy.next_host() == "host3"

        # Second round (should wrap around)
        assert strategy.next_host() == "host1"
        assert strategy.next_host() == "host2"
        assert strategy.next_host() == "host3"

    def test_next_host_advances_index(self):
        """Test that internal index advances correctly."""
        hosts = ["host1", "host2", "host3"]
        strategy = SequentialStrategy(hosts)

        assert strategy._next_index == 0
        strategy.next_host()
        assert strategy._next_index == 1
        strategy.next_host()
        assert strategy._next_index == 2
        strategy.next_host()
        assert strategy._next_index == 0  # Wrapped around


class TestRandomStrategy:
    """Test cases for RandomStrategy."""

    def test_initialization_with_empty_hosts(self):
        """Test that initializing with empty host list raises ValueError."""
        with pytest.raises(ValueError, match="Host list cannot be empty"):
            RandomStrategy([])

    def test_initialization_with_hosts(self):
        """Test successful initialization with valid host list."""
        hosts = ["host1", "host2", "host3"]
        strategy = RandomStrategy(hosts)
        assert strategy._hosts == hosts
        assert 0 <= strategy._next_index < len(hosts)

    def test_next_host_single_host(self):
        """Test random selection with a single host."""
        hosts = ["host1"]
        strategy = RandomStrategy(hosts)

        # Should always return the same host
        for _ in range(5):
            assert strategy.next_host() == "host1"

    def test_next_host_multiple_hosts(self):
        """Test random selection with multiple hosts."""
        hosts = ["host1", "host2", "host3"]
        strategy = RandomStrategy(hosts)

        # Collect multiple selections
        selections = [strategy.next_host() for _ in range(20)]

        # All selections should be from the host list
        assert all(host in hosts for host in selections)

        # With 20 selections from 3 hosts, we should see some variety
        # (extremely unlikely to get the same host 20 times)
        unique_hosts = set(selections)
        assert len(unique_hosts) > 1

    def test_next_host_avoids_consecutive_duplicates(self):
        """Test that random strategy avoids selecting the same host consecutively."""
        hosts = ["host1", "host2", "host3"]
        strategy = RandomStrategy(hosts)

        # Track consecutive duplicates
        previous_host = None
        consecutive_duplicates = 0

        for _ in range(50):
            current_host = strategy.next_host()
            if current_host == previous_host:
                consecutive_duplicates += 1
            previous_host = current_host

        # With multiple hosts, there should be no consecutive duplicates
        assert consecutive_duplicates == 0

    def test_next_host_returns_valid_host(self):
        """Test that all returned hosts are from the original list."""
        hosts = ["host1", "host2", "host3", "host4", "host5"]
        strategy = RandomStrategy(hosts)

        for _ in range(30):
            host = strategy.next_host()
            assert host in hosts


class TestBaseStrategy:
    """Test cases for _BaseStrategy abstract base class."""

    def test_cannot_instantiate_directly(self):
        """Test that _BaseStrategy cannot be instantiated directly."""
        with pytest.raises(TypeError):
            _BaseStrategy(["host1", "host2"])

    def test_subclass_must_implement_next_host(self):
        """Test that subclasses must implement next_host method."""

        class IncompleteStrategy(_BaseStrategy):
            pass

        with pytest.raises(TypeError):
            IncompleteStrategy(["host1", "host2"])
