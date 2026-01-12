from redirector.strategies import strategies
from redirector.healthchecks import healthchecks
from threading import Event, Thread

import logging


class LoadBalancer(Thread):

    def __init__(self, config, queue):
        """Constructor of the class.

        :config: Configuration of the load balancer
        :queue: Queue to send new DNS configurations
        """

        # Initialise the Thread object
        super().__init__()

        # Create the strategy object
        self._strategy = strategies[config["strategy"]](config["backend_hosts"])

        # Create the healthcheck service
        self._healthcheck = healthchecks[config["healthcheck"]["type"]](
            config["healthcheck"]["config"]
        )

        # Other instance attributes
        self._lb_name = config["name"]
        self._local_host = config["local_host"]
        self._backend_hosts = config["backend_hosts"]
        self._healthcheck_period = config["healthcheck"]["period"]
        self._queue = queue
        self._stop_event = Event()

    def run(self):
        """Run the load balancer.

        :returns: Nothing
        """

        timeout = 0
        backend_alive = False
        backend_changed = True
        backend_host = self._strategy.next_host()

        # Run while the event flag isn't set and block timeout seconds
        while not self._stop_event.wait(timeout):

            # Check if the backend host responds
            backend_alive, msg = self._healthcheck.is_alive(backend_host)

            # If the backend host isn't alive, get the next host
            if not backend_alive:
                logging.debug(
                    f'Healthcheck for host "{backend_host}" on load balancer "{self._lb_name}" failed. Reason: {msg}.'
                )
                backend_host = self._strategy.next_host()
                backend_changed = True
                timeout = 1

            # If the backend is alive and changed
            if backend_changed and backend_alive:

                logging.info(
                    f'Load balancer "{self._lb_name}" now using backend host "{backend_host}".'
                )

                # Inform the program about the DNS change
                self._queue.put((self._local_host, backend_host))

                # Reset the backend_changed flag
                backend_changed = False

                # Set the next timeout to the healthcheck period
                timeout = self._healthcheck_period

    def stop(self):
        """Stop the load balancer.

        :returns: Nothing
        """

        self._stop_event.set()
