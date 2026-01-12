from redirector.healthchecks.base import BaseHealthCheck
from typing import Dict, Tuple

import errno
import socket


CONFIG_SCHEMA = {
    "port": {"type": "integer", "required": True, "min": 1, "max": 65535},
    "timeout": {"type": "float", "required": False, "min": 0, "default": 10},
}


class TcpHealthCheck(BaseHealthCheck):
    """TCP-based health check implementation."""

    def __init__(self, config: Dict) -> None:
        """Initialize TCP health check with configuration.

        :param config: Configuration dictionary with 'port' and optional 'timeout'
        """
        super().__init__()
        self._port = config["port"]
        self._timeout = config["timeout"]

    def is_alive(self, host: str) -> Tuple[bool, str]:
        """Perform a TCP handshake against the given host.

        :param host: Host address to check
        :returns: Tuple (success boolean, message string)
        """
        try:
            # Create the TCP socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self._timeout)

            # Connect to the backend
            sock.connect((host, self._port))
            sock.close()

            return True, "OK"

        except socket.timeout:
            return False, f"Timeout ({self._timeout})"

        except socket.gaierror:
            return False, "DNS resolution failed"

        except OSError as e:
            if e.errno == errno.ECONNREFUSED:
                return False, "Connection refused"
            else:
                return False, f"OS error: {e}"
