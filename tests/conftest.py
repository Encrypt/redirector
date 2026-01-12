"""Pytest configuration and fixtures."""

import pytest
import sys
import os

# Add the redirector package to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
