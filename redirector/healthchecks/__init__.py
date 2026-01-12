from redirector.healthchecks import http, tcp

healthchecks = {"http": http.HttpHealthCheck, "tcp": tcp.TcpHealthCheck}

schemas = {"http": http.CONFIG_SCHEMA, "tcp": tcp.CONFIG_SCHEMA}
