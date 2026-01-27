"""
Cython optimized PVM (cpvm) module.

This module contains Cython-optimized implementations of the PVM interpreter
components for maximum performance:

- cy_pvm: Main Cython PVM interpreter with optimized execution loop
- mapper: Cython instruction mapper with C-level dispatch tables
- instructions: Cython instruction table implementations

Key Performance Features:
- C-level integer operations for gas accounting and program counter
- Optimized dispatch tables with direct memory access
- Vectorized bit operations for instruction processing
- Minimal Python object creation in tight loops

Usage:
    from tsrkit_pvm.cpvm.cy_pvm import CyInterpreter
    from tsrkit_pvm.cpvm.mapper import CyInstMapper
    from tsrkit_pvm.cpvm.instructions import ALL_CY_TABLES
"""

# Import main Cython components
from .cy_pvm import CyInterpreter
from .mapper import CyInstMapper
from .cy_block import CyCompiledInstruction, CyBlockInfo
from .instructions import ALL_CY_TABLES, ALL_TABLES
from .cy_memory import CyMemory
from .cy_program import CyProgram

__all__ = [
    # Main interpreter
    'CyInterpreter',
    
    # Instruction mapper
    'CyInstMapper',
    'CyCompiledInstruction',
    'CyBlockInfo',
    
    # Instruction tables
    'ALL_CY_TABLES',
    'ALL_TABLES',
    
    # Memory system
    'CyMemory',
    
    # Program classes
    'CyProgram',
]
