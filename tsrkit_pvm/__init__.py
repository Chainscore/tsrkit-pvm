"""Tessera - Polkadot Virtual Machine

A PVM implementation with interpreter and recompiler
for the Tessera client.
"""

__version__ = "0.1.0"
__author__ = "Chainscore Labs"

# Import common constants and utilities
from .core.memory import Memory
from .core.program_base import Program
from .core.ipvm import PVM
from .core.code import Code, y_function
from .common.types import Accessibility
from .common.status import (
    CONTINUE,
    HALT,
    HOST,
    OUT_OF_GAS,
    PAGE_FAULT,
    PANIC,
    ExecutionStatus,
    PvmError,
    HostStatus,
)

from .common.constants import (
    PVM_ADDR_ALIGNMENT,
    PVM_INIT_DATA_SIZE,
    PVM_MEMORY_PAGE_SIZE,
    PVM_INIT_ZONE_SIZE,
    REGISTER_COUNT,
)

from .interpreter.memory import INT_Memory
from .interpreter.program import INT_Program
from .interpreter.pvm import Interpreter

# Try to import recompiler if available
try:
    from .recompiler.memory import REC_Memory
    from .recompiler.program import REC_Program
    from .recompiler.pvm import Recompiler, _segwrap_available
    if not _segwrap_available:
        raise ImportError("segwrap not available")
    _HAS_RECOMPILER = True
except (ImportError, OSError):
    REC_Memory = None
    REC_Program = None
    Recompiler = None
    _HAS_RECOMPILER = False

# Try to import Cython PVM if available
try:
    from .cpvm.cy_pvm import CyInterpreter
    _HAS_CYTHON = True
except ImportError:
    CyInterpreter = None
    _HAS_CYTHON = False

__all__ = [
    # Core
    "Memory",
    "PVM",
    "Program",
    "Code",
    "y_function",
    # PVM
    "INT_Memory",
    "INT_Program",
    "Interpreter",
    "REC_Memory",
    "REC_Program",
    "Recompiler",
    "CyInterpreter",
    "_HAS_RECOMPILER",
    "_HAS_CYTHON",
    # Common constants
    "PVM_ADDR_ALIGNMENT",
    "PVM_INIT_DATA_SIZE",
    "PVM_INIT_ZONE_SIZE",
    "PVM_MEMORY_PAGE_SIZE",
    "REGISTER_COUNT",
    # Execution status and errors
    "CONTINUE",
    "HALT",
    "HOST",
    "OUT_OF_GAS",
    "PAGE_FAULT",
    "PANIC",
    "ExecutionStatus",
    "PvmError",
    "HostStatus",
    # Types
    "Accessibility",
    # Metadata
    "__version__",
    "__author__",
]
