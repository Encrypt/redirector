"""Unit tests for health check implementations."""

import pytest
import socket
import errno
from unittest.mock import Mock, patch, MagicMock
from redirector.healthchecks.tcp import TcpHealthCheck
from redirector.healthchecks.base import BaseHealthCheck


class TestTcpHealthCheck:
    """Test cases for TcpHealthCheck."""

    def test_initialization(self):
        """Test successful initialization with config."""
        config = {"port": 8080, "timeout": 5.0}
        healthcheck = TcpHealthCheck(config)
        assert healthcheck._port == 8080
        assert healthcheck._timeout == 5.0

    def test_initialization_with_defaults(self):
        """Test initialization uses default timeout."""
        config = {"port": 8080, "timeout": 10.0}
        healthcheck = TcpHealthCheck(config)
        assert healthcheck._port == 8080
        assert healthcheck._timeout == 10.0

    @patch("socket.socket")
    def test_is_alive_success(self, mock_socket_class):
        """Test successful health check."""
        # Setup mock
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket

        config = {"port": 8080, "timeout": 5.0}
        healthcheck = TcpHealthCheck(config)

        # Perform health check
        alive, message = healthcheck.is_alive("192.168.1.100")

        # Assertions
        assert alive is True
        assert message == "OK"
        mock_socket_class.assert_called_once_with(socket.AF_INET, socket.SOCK_STREAM)
        mock_socket.settimeout.assert_called_once_with(5.0)
        mock_socket.connect.assert_called_once_with(("192.168.1.100", 8080))
        mock_socket.close.assert_called_once()

    @patch("socket.socket")
    def test_is_alive_timeout(self, mock_socket_class):
        """Test health check with timeout."""
        # Setup mock to raise timeout
        mock_socket = MagicMock()
        mock_socket.connect.side_effect = socket.timeout()
        mock_socket_class.return_value = mock_socket

        config = {"port": 8080, "timeout": 5.0}
        healthcheck = TcpHealthCheck(config)

        # Perform health check
        alive, message = healthcheck.is_alive("192.168.1.100")

        # Assertions
        assert alive is False
        assert message == "Timeout (5.0)"

    @patch("socket.socket")
    def test_is_alive_dns_failure(self, mock_socket_class):
        """Test health check with DNS resolution failure."""
        # Setup mock to raise DNS error
        mock_socket = MagicMock()
        mock_socket.connect.side_effect = socket.gaierror()
        mock_socket_class.return_value = mock_socket

        config = {"port": 8080, "timeout": 5.0}
        healthcheck = TcpHealthCheck(config)

        # Perform health check
        alive, message = healthcheck.is_alive("invalid.hostname")

        # Assertions
        assert alive is False
        assert message == "DNS resolution failed"

    @patch("socket.socket")
    def test_is_alive_connection_refused(self, mock_socket_class):
        """Test health check with connection refused."""
        # Setup mock to raise connection refused error
        mock_socket = MagicMock()
        error = OSError()
        error.errno = errno.ECONNREFUSED
        mock_socket.connect.side_effect = error
        mock_socket_class.return_value = mock_socket

        config = {"port": 8080, "timeout": 5.0}
        healthcheck = TcpHealthCheck(config)

        # Perform health check
        alive, message = healthcheck.is_alive("192.168.1.100")

        # Assertions
        assert alive is False
        assert message == "Connection refused"

    @patch("socket.socket")
    def test_is_alive_os_error(self, mock_socket_class):
        """Test health check with generic OS error."""
        # Setup mock to raise generic OS error
        mock_socket = MagicMock()
        error = OSError("Network unreachable")
        error.errno = errno.ENETUNREACH
        mock_socket.connect.side_effect = error
        mock_socket_class.return_value = mock_socket

        config = {"port": 8080, "timeout": 5.0}
        healthcheck = TcpHealthCheck(config)

        # Perform health check
        alive, message = healthcheck.is_alive("192.168.1.100")

        # Assertions
        assert alive is False
        assert "OS error:" in message

    def test_is_alive_different_ports(self):
        """Test health checks on different ports."""
        with patch("socket.socket") as mock_socket_class:
            mock_socket = MagicMock()
            mock_socket_class.return_value = mock_socket

            # Test port 80
            healthcheck1 = TcpHealthCheck({"port": 80, "timeout": 5.0})
            healthcheck1.is_alive("192.168.1.100")
            mock_socket.connect.assert_called_with(("192.168.1.100", 80))

            # Test port 443
            healthcheck2 = TcpHealthCheck({"port": 443, "timeout": 5.0})
            healthcheck2.is_alive("192.168.1.100")
            mock_socket.connect.assert_called_with(("192.168.1.100", 443))


class TestBaseHealthCheck:
    """Test cases for BaseHealthCheck abstract base class."""

    def test_cannot_instantiate_directly(self):
        """Test that BaseHealthCheck cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseHealthCheck()

    def test_subclass_must_implement_is_alive(self):
        """Test that subclasses must implement is_alive method."""

        class IncompleteHealthCheck(BaseHealthCheck):
            pass

        with pytest.raises(TypeError):
            IncompleteHealthCheck()

    def test_subclass_with_implementation_works(self):
        """Test that properly implementing is_alive allows instantiation."""

        class CompleteHealthCheck(BaseHealthCheck):
            def is_alive(self, host):
                return True, "OK"

        # Should not raise an error
        healthcheck = CompleteHealthCheck()
        alive, message = healthcheck.is_alive("test.host")
        assert alive is True
        assert message == "OK"
