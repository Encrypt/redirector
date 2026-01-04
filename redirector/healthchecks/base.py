class BaseHealthCheck(object):
    def __init__(self):
        pass

    def is_alive(self, host):
        """Perform an healthcheck against the given host.

        :host: Host to check
        :returns: Tuple (Host alive, message)
        """

        raise NotImplementedError
