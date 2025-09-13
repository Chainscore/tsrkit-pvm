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

# Dynamic PVM implementation selection based on PVM_MODE
PVM_MODE = os.environ.get("PVM_MODE", "mypyc").lower()

if PVM_MODE == "cython":
    try:
        from .cy_pvm import Interpreter as PVM
        print("🚀 Using Cython-optimized PVM")
    except ImportError as e:
        print(f"⚠️  Cython PVM not available ({e}), falling back to standard interpreter")
        from .pvm import Interpreter as PVM
else:
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
