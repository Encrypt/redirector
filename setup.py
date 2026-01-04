#!/usr/bin/env python3

from redirector import __version__
from setuptools import setup, find_packages

with open("README.md", "r") as f:
    readme = f.read()

setup(
    name="redirector",
    version=__version__,
    description="The local DNS load balancer",
    log_description=readme,
    long_description_content_type="test/markdown",
    author="Yann Privé",
    author_email="9038199+Encrypt@users.noreply.github.com",
    url="https://github.com/Encrypt/redirector",
    packages=find_packages(exclude=["tests"]),
    install_requires=[
        "cerberus==1.3.8",
        "pyyaml==6.0.3"
    ],
    entry_points={
        "console_scripts": [
            "redirector=redirector.cli:main"
        ]
    },
    python_requires=">=3.9"
)
