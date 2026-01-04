# Redirector

Redirector is a "local DNS load balancer" manipulating the /etc/hosts file on Linux-based systems.
It is useful to connect applications to high-availability / distributed systems when only one host can be configured.

It was inspired from [MinIO's sidekick](https://github.com/minio/sidekick), with a more generic approach.


## Use cases

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


## Installation

Redirector is developed to work with Python 3.9+ and should preferably be installed in a Python virtual environment to prevent any dependency collision.
It should be running as a service on the server, with sufficient permissions to overwrite the /etc/hosts file.

Configuration is made through the [main configuration file](examples/config.yml) (YAML format) which should be given at startup with the `-c|--config` flag.

Each DNS load balancer should then be configured under the `lb_configs` directory relative to the main configuration file by default (this behaviour is the default and can be changed).
YAML files ending with the ".yml" or ".yaml" extensions only are parsed.


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


## Load balancing strategies

Two load balancing strategies are currently implemented:

* **Sequential strategy**

This strategy will select hosts in a sequential fashion from the `backend_hosts` list.
At startup, the first host of the `backend_hosts` list is used.

* **Random stategy**

This strategy will select a random host from the `backend_hosts` list.

At startup, the first responding host following the chosen strategy will be used to populate the /etc/hosts file.
