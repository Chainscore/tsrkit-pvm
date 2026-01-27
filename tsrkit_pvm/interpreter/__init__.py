"""TSR Kit PVM Interpreter

The interpreter module provides the core execution engine for PVM bytecode,
including program loading, memory management, and instruction execution.
"""

from ..common.constants import (
    PVM_ADDR_ALIGNMENT,
    PVM_INIT_DATA_SIZE,
    PVM_INIT_ZONE_SIZE,
    PVM_MEMORY_PAGE_SIZE,
    REGISTER_COUNT,
)
import os
from .memory import INT_Memory as Memory
from .program import INT_Program as Program

from .pvm import Interpreter as PVM
from ..common.status import (
    CONTINUE,
    HALT,
    HOST,
    OUT_OF_GAS,
    PAGE_FAULT,
    PANIC,
    ExecutionStatus,
    PvmError,
)

__all__ = [
    # Core execution engine
    "PVM",
    "Program",
    "Memory",
    # Status and error handling
    "ExecutionStatus",
    "PvmError",
    "CONTINUE",
    "HALT",
    "PANIC",
    "OUT_OF_GAS",
    "PAGE_FAULT",
    "HOST",
    # Constants
    "PVM_ADDR_ALIGNMENT",
    "PVM_INIT_DATA_SIZE",
    "PVM_MEMORY_PAGE_SIZE",
    "PVM_INIT_ZONE_SIZE",
    "REGISTER_COUNT",
]
