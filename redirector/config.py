from cerberus import Validator
from redirector.healthchecks import healthchecks, schemas
from redirector.strategies import strategies

import logging
import os
import yaml


_CORE_SCHEMA = {
    "log_level": {
        "type": "string",
        "required": False,
        "allowed": ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"],
        "default": "INFO",
    },
    "log_format": {
        "type": "string",
        "required": False,
        "default": "%(asctime)s :: %(levelname)s :: %(message)s",
    },
    "log_file_path": {
        "type": "string",
        "required": False,
        "default": "/var/log/redirector.log",
    },
    "log_file_max_bytes": {"type": "integer", "required": False, "default": 5000000},
    "log_file_max_backups": {"type": "integer", "required": False, "default": 5},
    "lb_configs_dir": {"type": "string", "required": False, "default": "lb_configs"},
    "persist_hosts_block": {"type": "boolean", "required": False, "default": True},
    "pid_file": {
        "type": "string",
        "required": False,
        "nullable": True,
        "default": None,
    },
}

_LOADBALANCER_SCHEMA = {
    "name": {"type": "string", "required": True},
    "local_host": {"type": "string", "required": True},
    "backend_hosts": {
        "type": "list",
        "required": True,
        "minlength": 1,
        "schema": {"type": "string", "required": True},
    },
    "strategy": {
        "type": "string",
        "required": True,
        "allowed": list(strategies.keys()),
    },
    "healthcheck": {
        "schema": {
            "type": {
                "type": "string",
                "required": True,
                "allowed": list(healthchecks.keys()),
            },
            "period": {"type": "float", "required": True, "min": 0},
            "config": {"type": "dict", "required": True},
        }
    },
}


class ConfigError(Exception):
    pass


class ConfigLoader(object):

    def __init__(self, config_file):
        self._config_file = config_file
        self._lb_configs_dir = None

    def _validate_or_raise(self, schema, document, errdesc):
        """Validate a configuration of raise an error.

        :schema: Schema to use for validation
        :document: Document to validate agains the schema
        :errdesc: Base error description
        :kwargs: Extra normalization rules
        :returns: Validated document
        :raises: ConfigError in case of error
        """

        # Validate the configuration
        validator = Validator(schema, purge_unknown=True)
        if not validator.validate(document):

            # Return the errors
            errors = ", ".join([f"{k}: {v}" for k, v in validator.errors.items()])
            raise ConfigError(f"{errdesc}: {errors}.")

        return validator.document

    def load_core_config(self):
        """Load the core configuration from the YAML configuration file.

        :returns: Dict with the configuration
        :raises: ConfigError in case of problem
        """

        # Load the YAML configuration
        logging.debug(f'Loading core configuration from "{self._config_file}"')
        try:
            with open(self._config_file, "r") as f:
                config = yaml.safe_load(f)
        except FileNotFoundError:
            raise ConfigError(
                f'The configuration file "{self._config_file}" doesn\'t exist.'
            )

        # Handle empty/commented YAML files
        if config is None:
            logging.debug("Configuration file is empty or contains only comments, using defaults")
            config = {}

        # Validate the configuration file
        config = self._validate_or_raise(
            _CORE_SCHEMA, config, "Failed to parse the configuration file"
        )

        # Identify the load balancers configuration directory
        self._lb_configs_dir = os.path.join(
            os.path.dirname(self._config_file), config["lb_configs_dir"]
        )

        return config

    def load_lb_configs(self):
        """Load the load balancers configuration files.

        :returns: Generator with the load balancer configs
        :raises: ConfigError in case of error
        """

        # Make sure the load balancers configuration directory exists
        if not os.path.exists(self._lb_configs_dir):
            raise ConfigError(
                f"The load balancers configuration directory {self._lb_configs_dir} doesn't exist."
            )

        # Identify all load balancers configuration files ending with .yml or .yaml
        config_files = []
        for config_file in os.listdir(self._lb_configs_dir):
            if config_file.endswith((".yml", ".yaml")):
                config_files.append(config_file)

        logging.debug(f"Found {len(config_files)} load balancer configuration file(s) in {self._lb_configs_dir}")

        # For each configuration file...
        for config_file in config_files:

            schema = _LOADBALANCER_SCHEMA.copy()
            validation_error = (
                f"Failed to parse the load balancer configuration file {config_file}"
            )

            # Load the YAML configuration
            config_path = os.path.join(self._lb_configs_dir, config_file)
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)

            # Handle empty/commented YAML files
            if config is None:
                raise ConfigError(
                    f"Load balancer configuration file {config_file} is empty or contains only comments"
                )

            # Perform a first validation of the load balancer configuration
            self._validate_or_raise(schema, config, validation_error)

            # Perform a second validation of the load balancer configuration with the healthcheck schema
            schema["healthcheck"]["schema"]["config"]["schema"] = schemas[
                config["healthcheck"]["type"]
            ]
            yield self._validate_or_raise(schema, config, validation_error)
