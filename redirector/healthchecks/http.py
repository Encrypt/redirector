from redirector.healthchecks.base import BaseHealthCheck
from urllib.error import HTTPError, URLError
from urllib.parse import urlunparse
from urllib.request import Request, urlopen

import re
import socket


CONFIG_SCHEMA = {
    "method": {
        "type": "string",
        "required": False,
        "allowed": ["HEAD", "GET", "OPTIONS", "POST"],
        "default": "GET",
    },
    "headers": {
        "type": "list",
        "required": False,
        "schema": {
            "type": "dict",
            "keysrules": {"type": "string"},
            "valuesrules": {"type": "string"},
        },
        "default": {},
    },
    "scheme": {
        "type": "string",
        "required": False,
        "allowed": ["http", "https"],
        "default": "http",
    },
    "port": {"type": "integer", "required": True, "min": 1, "max": 65535},
    "path": {"type": "string", "required": True},
    "query": {"type": "string", "required": False, "nullable": True, "default": None},
    "timeout": {"type": "float", "required": False, "min": 0, "default": 10},
    "cacerts": {"type": "string", "required": False, "nullable": True, "default": None},
    "expected_status": {"type": "string", "required": False, "default": "200"},
    "expected_response": {
        "type": "string",
        "required": False,
        "nullable": True,
        "default": None,
    },
    "expected_response_encoding": {
        "type": "string",
        "required": False,
        "default": "utf-8",
    },
}


class HttpHealthCheck(BaseHealthCheck):

    def __init__(self, config):
        """Constructor of the class.

        :config: Configuration of the healthcheck
        :returns: True if it is alive, False otherwise
        """

        self._method = config["method"]
        self._headers = config["headers"]
        self._scheme = config["scheme"]
        self._port = config["port"]
        self._path = config["path"]
        self._query = config["query"]
        self._timeout = config["timeout"]
        self._cacerts = config["cacerts"]
        self._expected_status = config["expected_status"]
        self._expected_response = config["expected_response"]
        self._expected_response_encoding = config["expected_response_encoding"]

    def is_alive(self, host):
        """Perform an HTTP request against the given host.

        :host: Host to check
        :returns: True if successful, False otherwise
        """

        # Build the URL
        netloc = f"{host}:{self._port}"
        url = urlunparse((self._scheme, netloc, self._path, None, self._query, None))

        try:
            request = Request(url, method=self._method, headers=self._headers)

            with urlopen(
                request, timeout=self._timeout, cafile=self._cacerts
            ) as response:

                # Make sure we didn't get a wrong HTTP status code
                if re.search(str(response.code), self._expected_status) is None:
                    return (
                        False,
                        f'Got HTTP code "{response.code}" instead of "{self._expected_status}"',
                    )

                # If <expected_response> was specified, make sure we didn't get a wrong response
                if self._expected_response is not None:
                    decoded_response = response.read().decode(
                        self._expected_response_encoding
                    )
                    if re.search(decoded_response, self._expected_response) is None:
                        return (
                            False,
                            f'The HTTP response didn\'t match the expected response "{self._expected_response}"',
                        )

                # No error was encountered, the host is alive
                return True, "OK"

        except HTTPError as e:
            return False, f"HTTP error ({e.code})"

        except URLError as e:
            return False, f"URL error ({e.reason})"

        except socket.timeout:
            return False, f"Timeout ({self._timeout})"
