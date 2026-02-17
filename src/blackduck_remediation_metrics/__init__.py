"""
Black Duck Remediation Metrics
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A Python module for extracting and analyzing remediation status metrics from Black Duck.

:copyright: (c) 2026 Jouni Lehto
:license: MIT
"""

__version__ = "0.1.20"
__author__ = "Jouni Lehto"

from .blackduck_triage_extract import main

__all__ = ["main"]
