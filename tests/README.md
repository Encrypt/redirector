# Tests directory

This directory contains unit tests for the redirector project.

## Running Tests

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
pytest tests/test_strategies.py
```

Run specific test:
```bash
pytest tests/test_strategies.py::TestSequentialStrategy::test_next_host_multiple_hosts
```

## Test Structure

- `test_strategies.py` - Tests for load balancing strategies
- `test_healthchecks.py` - Tests for health check implementations
- `test_hostsmanager.py` - Tests for hosts file management
- `conftest.py` - Pytest configuration and shared fixtures
