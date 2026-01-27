"""Core abstract base classes for PVM components."""

from .ipvm import PVM
from .program_base import Program
from .memory import Memory
# from .code import Code  # Excluded due to recompiler dependencies

__all__ = ["PVM", "Program", "Memory"]  # Removed "Code"
