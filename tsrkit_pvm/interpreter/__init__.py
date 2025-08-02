"""TSR Kit PVM Interpreter

The interpreter module provides the core execution engine for PVM bytecode,
including program loading, memory management, and instruction execution.
"""

from .code import Code
from .constants import (
    PVM_ADDR_ALIGNMENT,
    PVM_INIT_DATA_SIZE,
    PVM_INIT_ZONE_SIZE,
    PVM_MEMORY_PAGE_SIZE,
    REGISTER_COUNT,
)
from .memory import Memory
from .program import Program
from .pvm import PVM
from .register import from_pc
from .status import (
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
    "from_pc",
    "Code",
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
