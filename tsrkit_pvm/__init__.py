"""Tessera - Polkadot Virtual Machine

A high-performance PVM implementation with interpreter and recompiler
for the Tessera client.

This package provides:
- An interpreter for executing PVM bytecode
- A recompiler for optimizing PVM bytecode execution
- Memory management and program handling
- Status and error handling utilities
"""

__version__ = "0.1.0"
__author__ = "Chainscore Labs"

# Import key components from interpreter
from .interpreter import (
    CONTINUE,
    HALT,
    HOST,
    OUT_OF_GAS,
    PAGE_FAULT,
    PANIC,
    PVM,
    ExecutionStatus,
    Memory,
    Program,
    PvmError,
)


__all__ = [
    # Core classes
    "PVM",
    "Program",
    "Memory",
    # Status and errors
    "ExecutionStatus",
    "PvmError",
    "CONTINUE",
    "HALT",
    "PANIC",
    "OUT_OF_GAS",
    "PAGE_FAULT",
    "HOST",
    # Metadata
    "__version__",
    "__author__",
]
