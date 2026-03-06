"""
setup.py
NeonFlood v2.0.0 — pip-installable package configuration.

Install:
    pip install .                    # core (stdlib only)
    pip install ".[proxy]"           # core + SOCKS5 proxy support

After install the `neonflood` command becomes available system-wide.
"""

import os
from setuptools import setup, find_packages


def _read(fname):
    path = os.path.join(os.path.dirname(__file__), fname)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return f.read()
    return ""


setup(
    name="neonflood",
    version="2.0.0",
    author="NH Prince",
    author_email="",
    description="Professional cyberpunk HTTP stress testing suite (GUI + CLI)",
    long_description=_read("README.md"),
    long_description_content_type="text/markdown",
    url="https://nhprince.dpdns.org",
    project_urls={
        "Source": "https://github.com/nhprince/NeonFlood",
    },
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[],           # all core features use Python stdlib
    extras_require={
        "proxy": ["PySocks>=1.7.1"],
    },
    entry_points={
        "console_scripts": [
            "neonflood=neonflood.cli:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
        "Environment :: Console",
        "Topic :: Security",
        "Topic :: System :: Networking",
        "Intended Audience :: Developers",
    ],
)
