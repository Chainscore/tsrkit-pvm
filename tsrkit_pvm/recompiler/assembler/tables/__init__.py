from .i_offset import WArgsOneOffset
from .i_reg_i_ewimm import InstructionsWArgs1Imm1EwImm
from .i_reg_i_imm import InstructionsWArgs1Reg1Imm
from .ii_reg_i_imm import InstructionsWArgs2Reg1Imm
from .ii_reg_i_offset import InstructionsWArgs2Reg1Offset
from .wo_args import InstructionsWoArgs

__all__ = [
    "WArgsOneOffset",
    "InstructionsWArgs1Imm1EwImm",
    "InstructionsWArgs1Reg1Imm",
    "InstructionsWArgs2Reg1Imm",
    "InstructionsWArgs2Reg1Offset",
    "InstructionsWoArgs",
]