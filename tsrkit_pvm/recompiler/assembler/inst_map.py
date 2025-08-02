from tsrkit_pvm.core.mapper import InstMapper
from .tables.i_offset import WArgsOneOffset
from .tables.i_reg_i_ewimm import InstructionsWArgs1Imm1EwImm
from .tables.i_reg_i_imm import InstructionsWArgs1Reg1Imm
from .tables.i_reg_i_imm_i_offset import InstructionsWArgs1Reg1Imm1Offset
from .tables.ii_reg_i_imm import InstructionsWArgs2Reg1Imm
from .tables.ii_reg_i_offset import InstructionsWArgs2Reg1Offset
from .tables.ii_imm import InstructionsWArgs2Imm
from .tables.wo_args import InstructionsWoArgs
from .tables.i_imm import InstructionsWArgs1Imm
from .tables.i_reg_ii_imm import InstructionsWArgs1Reg2Imm
from .tables.ii_reg import InstructionsWArgs2Reg
from .tables.ii_reg_ii_imm import InstructionsWArgs2Reg2Imm
from .tables.iii_reg import InstructionsWArgs3Reg


# Global dispatcher instance - created once at init
inst_map = InstMapper([
    InstructionsWoArgs,
    InstructionsWArgs1Imm1EwImm,
    WArgsOneOffset,
    InstructionsWArgs1Reg1Imm,
    InstructionsWArgs1Reg1Imm1Offset,
    InstructionsWArgs2Imm,
    InstructionsWArgs2Reg1Imm,
    InstructionsWArgs2Reg1Offset,
    InstructionsWArgs1Imm,
    InstructionsWArgs1Reg2Imm,
    InstructionsWArgs2Reg,
    InstructionsWArgs2Reg2Imm,
    InstructionsWArgs3Reg,
])
