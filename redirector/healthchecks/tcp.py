from redirector.healthchecks.base import BaseHealthCheck

import errno
import socket


CONFIG_SCHEMA = {
    "port": {
        "type": "integer",
        "required": True,
        "min": 1,
        "max": 65535
    },
    "timeout": {
        "type": "float",
        "required": False,
        "min": 0,
        "default": 10
    }
}


class TcpHealthCheck(BaseHealthCheck):

    def __init__(self, config):
        """Constructor of the class.

        :config: Configuration of the healthcheck
        :returns: True if it is alive, False otherwise
        """

        self._port = config["port"]
        self._timeout = config["timeout"]

    def is_alive(self, host):
        """Perform a TCP handshake against the given host.

        :host: Host to check
        :returns: True if successful, False otherwise
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
