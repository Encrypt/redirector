# Redirector

Redirector is a "local DNS load balancer" manipulating the /etc/hosts file on Linux-based systems.
It is useful to connect applications to high-availability / distributed systems when only one host can be configured.

It was inspired from [MinIO's sidekick](https://github.com/minio/sidekick), with a more generic approach.

## Table of Contents

- [Use Cases](#use-cases)
- [Requirements](#requirements)
- [Dependencies](#dependencies)
- [Installation](#installation)
  - [Installing uv](#installing-uv)
  - [Installing Redirector](#installing-redirector)
- [Getting Started](#getting-started)
  - [Basic Usage](#basic-usage)
  - [Configuration](#configuration)
- [Healthchecks](#healthchecks)
- [Load Balancing Strategies](#load-balancing-strategies)
- [Development](#development)

## Use Cases

* **Load distribution on distributed systems**

Redirector can help you spread the load on distributed systems by connecting each applicative server directly to one of the nodes of these distributed systems.
For instance, you can connect Elasticsearch data nodes directly to MinIO nodes to make snapshots with maximum network throughput.

* **Per-datacenter DNS configuration**

Similarly to the previous point, Redirector can help you connecting your applicative servers to one of the nodes of your distributed systems *within the same datacenter*.
This reduces inter-datacenter network usage.

* **Simple load balancer**

Finally, Redirector can be used as as "simple" load balancer to connect an applicative server to an effectively alive node of a distributed system.
A few pieces of software don't allow multiple entries in their configuration when you target distributed systems.

All these use cases can potentially be fulfilled by a "real" DNS load balancer, but you may not have one in your infrastructure or it may need a more complex architecture.


## Requirements

- Python 3.6+
- Root/sudo permissions to modify `/etc/hosts`

## Dependencies

Redirector has minimal dependencies:

- **cerberus** (1.3.5 - 1.3.8) - Schema validation for configuration files
- **pyyaml** (6.0.1 - 6.0.3) - YAML parsing for configuration

Development dependencies (optional):
- **pytest** (≥7.0.0) - Testing framework
- **pytest-cov** (≥4.0.0) - Code coverage reports
- **pytest-mock** (≥3.10.0) - Mocking support for tests


## Installation

### Installing uv

Redirector uses [uv](https://github.com/astral-sh/uv) for modern Python package management. Install uv using the standalone installer:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

For more installation options, see the [uv documentation](https://docs.astral.sh/uv/getting-started/installation/).

### Installing Redirector

Clone the repository and install:

```bash
git clone https://github.com/Encrypt/redirector.git
cd redirector
uv venv
source .venv/bin/activate
uv pip install -e .
```

For development with test dependencies:
```bash
uv pip install -e ".[dev]"
```


## Getting Started

Redirector requires root/sudo permissions to modify the `/etc/hosts` file.

### Basic Usage

**Option 1: Run from virtual environment (recommended for development)**

Use the full path to the binary in your virtual environment:

```bash
sudo /home/youruser/Projects/redirector/.venv/bin/redirector -c examples/config.yml
```

**Option 2: System-wide installation (recommended for production)**

Install system-wide to use `redirector` command directly with sudo:

```bash
# From the project directory
sudo uv pip install --system .

# Now you can run:
sudo redirector -c /path/to/config.yml
```

### Configuration

Configuration is made through the [main configuration file](examples/config.yml) (YAML format), which should be given at startup with the `-c|--config` flag.

Each DNS load balancer should be configured under the `lb_configs` directory relative to the main configuration file by default (this behavior can be changed).
YAML files ending with the ".yml" or ".yaml" extensions only are parsed.

See the [examples](examples/) directory for sample configurations:
- [Main configuration](examples/config.yml)
- [TCP healthcheck example](examples/lb_tcp_healthcheck.yml)
- [HTTP healthcheck example](examples/lb_http_healthcheck.yml)


## Healthchecks

Healthchecks are executed periodically to check that the backend server is alive.

Two kind of healthchecks are currently implemented:

* **TCP healthcheck**

A periodic TCP connection is opened and then closed on the backend server.
It is considered successful if the connection succeeds.
An example with all possible configuration options can be found [here](examples/lb_tcp_healthcheck.yml).

* **HTTP healthcheck**

A periodic HTTP request is made on the backend server.
It is considered successful if the connection succeeds.
An example with all possible configuration options can be found [here](examples/lb_http_healthcheck.yml).

If the healthcheck fails, a new host from the `backend_hosts` list is chosen, depending on the selected strategy.


## Load Balancing Strategies

Two load balancing strategies are currently implemented:

* **Sequential strategy**

This strategy will select hosts in a sequential fashion from the `backend_hosts` list.
At startup, the first host of the `backend_hosts` list is used.

* **Random strategy**

This strategy will select a random host from the `backend_hosts` list.

At startup, the first responding host following the chosen strategy will be used to populate the /etc/hosts file.


## Development

### Running Tests

Install development dependencies:
```bash
uv pip install -e ".[dev]"
```

Run all tests:
```bash
pytest
```

Run with coverage:
```bash
pytest --cov=redirector --cov-report=html
```

Run specific test file:
```bash
pytest tests/test_strategies.py -v
```