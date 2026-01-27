"""
Cython optimized instructions module.

This module provides Cython-optimized instruction implementations for the PVM,
including individual instruction tables and the instruction mapper.
"""

from .tables import ALL_CY_TABLES, ALL_TABLES

__all__ = [
    'ALL_CY_TABLES',
    'ALL_TABLES',
]
