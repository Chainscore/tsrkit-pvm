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

# Lazy import for recompiler to avoid loading Linux-specific native libraries
# unless explicitly requested on a compatible platform
import platform
import sys

def _get_recompiler_classes():
    """Lazy loader for recompiler classes that require platform-specific native libraries."""
    if platform.system() != "Linux" or platform.machine() not in ["x86_64", "AMD64"]:
        raise ImportError(
            f"Recompiler is only supported on Linux x86_64, current platform: "
            f"{platform.system()} {platform.machine()}"
        )
    
    try:
        from .recompiler.memory import REC_Memory
        from .recompiler.program import REC_Program  
        from .recompiler.pvm import Recompiler
        return REC_Memory, REC_Program, Recompiler
    except OSError as e:
        if "libsegwrap" in str(e):
            raise ImportError(
                f"Recompiler native library not available: {e}\n"
                "The recompiler requires Linux-specific native libraries that are not "
                "available on this platform."
            ) from e
        raise

# Create lazy properties for recompiler classes
class _LazyRecompilerModule:
    """Module-like object that provides lazy loading for recompiler classes."""
    
    def __getattr__(self, name):
        if name in ("REC_Memory", "REC_Program", "Recompiler"):
            try:
                REC_Memory, REC_Program, Recompiler = _get_recompiler_classes()
                # Cache the imported classes
                self.REC_Memory = REC_Memory
                self.REC_Program = REC_Program
                self.Recompiler = Recompiler
                return getattr(self, name)
            except ImportError as e:
                raise ImportError(f"Cannot import {name}: {e}") from e
        raise AttributeError(f"module has no attribute '{name}'")

# Create lazy loader instance
_recompiler_loader = _LazyRecompilerModule()

# Create module-level properties that delegate to the lazy loader
def __getattr__(name):
    if name in ("REC_Memory", "REC_Program", "Recompiler"):
        return getattr(_recompiler_loader, name)
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


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
