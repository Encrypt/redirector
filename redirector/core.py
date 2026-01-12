from logging.handlers import RotatingFileHandler
from redirector.config import ConfigError, ConfigLoader
from redirector.hostsmanager import HostsManager, HostsManagerError
from redirector.loadbalancer import LoadBalancer

import logging
import os
import queue


class Redirector(object):

    def __init__(self, config_path):

        # Class attributes
        self._config = None
        self._configloader = ConfigLoader(config_path)
        self._hostsmanager = HostsManager()
        self._load_balancers = {}
        self._queue = queue.Queue()
        self._run = True

    def _setup_logging(self):
        """Setup logging for the application.

        :returns: Nothing
        """

        # Create the rotating file handler with the log format
        formatter = logging.Formatter(self._config["log_format"])
        handler = RotatingFileHandler(
            self._config["log_file_path"],
            maxBytes=self._config["log_file_max_bytes"],
            backupCount=self._config["log_file_max_backups"],
        )
        handler.setFormatter(formatter)

        # Configure the root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(self._config["log_level"])
        root_logger.addHandler(handler)

    def _initialise_components(self):
        """Initialise the components.

        :returns: Nothing
        """

        try:

            # Load the already defined entries in the /etc/hosts file
            self._hostsmanager.load_persisted_entries()

            expected_hostnames = []

            # Load the load balancer configurations
            for config in self._configloader.load_lb_configs():

                lb_name = config["name"]

                # Make sure the load balancer name is unique
                if lb_name in self._load_balancers.keys():
                    logging.critical(
                        'Two load balancers named "{lb_name}" were defined.'
                    )
                    raise RuntimeError()

                # Create the load balancer object
                load_balancer = LoadBalancer(config, self._queue)
                logging.info(f'Load balancer "{lb_name}" loaded.')
                self._load_balancers[lb_name] = load_balancer

                # Add the hostname to the list of expected hostnames
                expected_hostnames.append(config["local_host"])

            # Make sure at least one load balancer was configured
            if len(self._load_balancers) == 0:
                logging.critical("No load balancer was defined.")
                raise RuntimeError()

            # Inform the HostsManager about expected hostnames
            self._hostsmanager.remove_unexpected_entries(expected_hostnames)

        except (ConfigError, HostsManagerError) as e:
            logging.critical(e)
            raise RuntimeError()

    def initialise(self):
        """Initialise the program.

        :returns: Nothing
        """

        # Load the core configuration
        try:
            self._config = self._configloader.load_core_config()
        except ConfigError as e:
            raise RuntimeError(e)

        # Write the PID file if configured
        if self._config["pid_file"] is not None:
            with open(self._config["pid_file"], "w") as f:
                f.write(f"{os.getpid()}\n")

        # Setup logging
        self._setup_logging()

        logging.info("Redirector is starting...")

        # Initialise the components
        self._initialise_components()

    def _do_stop(self):
        """Stop the program.

        :returns: Nothing
        """

        # Stop load balancers
        for lb in self._load_balancers.values():
            lb.stop()

        # Wait for all load balancer threads to finish
        for lb in self._load_balancers.values():
            lb.join()

        # Remove the block in the /etc/hosts file if configured
        if not self._config["persist_hosts_block"]:
            self._hostsmanager.remove_redirector_block()

        # Remove the PID fule if configured
        if self._config["pid_file"] is not None:
            os.remove(self._config["pid_file"])

    def run(self):
        """Run Redirector.

        :returns: Nothing
        """

        # Start the load balancer threads
        for lb in self._load_balancers.values():
            lb.start()

        logging.info("Redirector started.")

        while self._run:

            try:

                # Get a potentially new DNS configuration from the queue
                local_host, backend_host = self._queue.get(timeout=1)

                # Update or insert it to the DNS configuration
                self._hostsmanager.upsert_entry(local_host, backend_host)

            except queue.Empty:
                pass

            except HostsManagerError as e:
                logging.critical(e)
                self._run = False

        # Stop components
        self._do_stop()

        logging.info("Redirector stopped.")

    def stop(self):
        """Stop active load balancers.

        :returns: Nothing
        """

        self._run = False
