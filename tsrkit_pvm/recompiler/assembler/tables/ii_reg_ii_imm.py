from typing import Any, Callable, Dict, TYPE_CHECKING

from ..instruction_table import InstructionTable
from ..opcode import OpCode

class InstructionsWArgs2Reg2Imm(InstructionTable):
    @classmethod
    def table(cls) -> Dict[int, OpCode]:
       return {} 
