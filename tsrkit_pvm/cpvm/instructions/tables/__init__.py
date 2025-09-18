"""
Cython optimized instruction tables.

This module contains Cython-optimized implementations of all PVM instruction tables,
organized by argument types:

- wo_args: Instructions without arguments (opcodes 0-9)
- i_imm: Instructions with 1 immediate argument (opcodes 10-19)  
- ii_reg: Instructions with 2 register arguments (opcodes 100-111)
- More tables to be added...

Each table is implemented as a Cython extension class for maximum performance,
with Python-compatible wrapper classes for easy integration.
"""

# Import all Cython instruction tables
from .wo_args import InstructionsWoArgs
from .i_imm import CyInstructionsWArgs1Imm
from .i_offset import CyWArgsOneOffset
from .i_reg_i_imm import CyInstructionsWArgs1Reg1Imm
from .i_reg_i_imm_i_offset import InstructionsWArgs1Reg1Imm1Offset
from .i_reg_i_ewimm import CyInstructionsWArgs1Reg1EwImm
from .i_reg_ii_imm import CyInstructionsWArgs1Reg2Imm
from .ii_imm import CyInstructionsWArgs2Imm
from .ii_reg import CyInstructionsWArgs2Reg
from .ii_reg_i_imm import CyInstructionsWArgs2Reg1Imm
from .ii_reg_i_offset import CyInstructionsWArgs2Reg1Offset
from .ii_reg_ii_imm import CyInstructionsWArgs2Reg2Imm
from .iii_reg import CyInstructionsWArgs3Reg


# List of all available instruction table classes
ALL_CY_TABLES = [
    InstructionsWoArgs,
    CyInstructionsWArgs1Imm,
    CyWArgsOneOffset,
    CyInstructionsWArgs1Reg1Imm, 
    InstructionsWArgs1Reg1Imm1Offset,
    CyInstructionsWArgs1Reg1EwImm,
    CyInstructionsWArgs1Reg2Imm,
    CyInstructionsWArgs2Imm,
    CyInstructionsWArgs2Reg,
    CyInstructionsWArgs2Reg1Imm,
    CyInstructionsWArgs2Reg1Offset,
    CyInstructionsWArgs2Reg2Imm,
    CyInstructionsWArgs3Reg,
]

# Python-compatible wrappers (maintain compatibility)
ALL_TABLES = [
    InstructionsWoArgs,
    CyInstructionsWArgs1Imm,
    CyInstructionsWArgs2Reg,
    CyInstructionsWArgs3Reg,
]

__all__ = [
    # Cython classes
    'InstructionsWoArgs',
    'CyInstructionsWArgs1Imm',
    'CyWArgsOneOffset',
    'CyInstructionsWArgs1Reg1Imm',
    'InstructionsWArgs1Reg1Imm1Offset',
    'CyInstructionsWArgs1Reg1EwImm',
    'CyInstructionsWArgs1Reg2Imm',
    'CyInstructionsWArgs2Imm',
    'CyInstructionsWArgs2Reg',
    'CyInstructionsWArgs2Reg1Imm',
    'CyInstructionsWArgs2Reg1Offset',
    'CyInstructionsWArgs2Reg2Imm',
    'CyInstructionsWArgs3Reg',
    
    # Collections
    'ALL_CY_TABLES',
    'ALL_TABLES',
]
