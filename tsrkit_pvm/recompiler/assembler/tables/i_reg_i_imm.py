from os import wait
from typing import Any, Callable, Dict, TYPE_CHECKING

from tsrkit_pvm.common.utils import chi, z, z_inv

from ....core.instruction_table import InstructionTable
from ....core.opcode import OpCode
from ....core.program_base import Program

if TYPE_CHECKING:
    from ...program import REC_Program

from ...vm_context import VMContext, r_map, TEMP_REG

from tsrkit_asm import (
    PyAssembler,
    Reg,
    RegSize,
    RegMem,
    Operands,
    ImmKind,
    MemOp,
    LoadKind,
    Size,
    Condition,
    RegIndex,
    Scale,
)


class InstructionsWArgs1Reg1Imm(InstructionTable):
    def __init__(self, counter: int, program: Program, skip_index: int) -> None:
        self.counter = counter
        self.program = program
        self.skip_index = skip_index


    def get_props(self):
        ra = min(12, int(self.program.zeta[self.counter + 1]) % 16)
        lx = min(4, max(0, self.skip_index - 1))
        start = self.counter + 2
        end = start + lx
        vx = chi(int.from_bytes(self.program.zeta[start:end], "little"), lx)
        return (ra, lx, vx)

    @classmethod
    def table(cls) -> Dict[int, OpCode]:
        return {
            50: OpCode(name="jump_ind", fn=cls.jump_ind, gas=1, is_terminating=True),
            51: OpCode(name="load_imm", fn=cls.load_imm, gas=1, is_terminating=False),
            52: OpCode(name="load_u8", fn=cls.load_u8, gas=1, is_terminating=False),
            53: OpCode(name="load_i8", fn=cls.load_i8, gas=1, is_terminating=False),
            54: OpCode(name="load_u16", fn=cls.load_u16, gas=1, is_terminating=False),
            55: OpCode(name="load_i16", fn=cls.load_i16, gas=1, is_terminating=False),
            56: OpCode(name="load_u32", fn=cls.load_u32, gas=1, is_terminating=False),
            57: OpCode(name="load_i32", fn=cls.load_i32, gas=1, is_terminating=False),
            58: OpCode(name="load_u64", fn=cls.load_u64, gas=1, is_terminating=False),
            59: OpCode(name="store_u8", fn=cls.store_u8, gas=1, is_terminating=False),
            60: OpCode(name="store_u16", fn=cls.store_u16, gas=1, is_terminating=False),
            61: OpCode(name="store_u32", fn=cls.store_u32, gas=1, is_terminating=False),
            62: OpCode(name="store_u64", fn=cls.store_u64, gas=1, is_terminating=False),
        }

    def jump_ind(self, asm, ra: int, lx: int, vx: int):
        """Indirect jump to address stored in register ra plus immediate vx."""
        # Part 1: Load immediate vx into register ra
        # Part 2: Calculate the PVM address: rb + vy
        # Use rcx as temp register for address calculation
        if vx != 0:
            asm.mov(size=RegSize.R64, a=TEMP_REG, b=r_map[ra])
            asm.add(
                Operands.RegMem_Imm(
                    reg_mem=RegMem.Reg(TEMP_REG), imm=ImmKind.I64(vx)
                )
            )
        else:
            asm.mov(size=RegSize.R64, a=TEMP_REG, b=r_map[ra])

        # Ensure 32-bit wrap: rcx = rcx % 2**32
        asm.mov(size=RegSize.R32, a=TEMP_REG, b=TEMP_REG)

        # Part 3: Check if it's the halt value (2**32 - 2**16)
        asm.cmp(
            Operands.RegMem_Imm(
                reg_mem=RegMem.Reg(TEMP_REG), imm=ImmKind.I32(2**32 - 2**16)
            )
        )
        asm.jcc_label32(Condition.Equal, asm.halt_label)

        # Part 4: Validate PVM address (check alignment, bounds, etc.)
        # Check if pvm_address == 0 (invalid)
        asm.test(
            Operands.RegMem_Reg(
                size=Size.U32, reg_mem=RegMem.Reg(TEMP_REG), reg=TEMP_REG
            )
        )
        asm.jcc_label32(Condition.Equal, asm.panic_label)

        # Check alignment: pvm_address % 2 == 0
        asm.test(Operands.RegMem_Imm(reg_mem=RegMem.Reg(TEMP_REG), imm=ImmKind.I32(1)))
        asm.jcc_label32(Condition.NotEqual, asm.panic_label)

        # Calculate jump table index: (pvm_address / 2) - 1
        asm.shr_imm(RegSize.R64, RegMem.Reg(TEMP_REG), 1)  # rcx = pvm_address / 2
        asm.dec(Size.U64, RegMem.Reg(TEMP_REG))

        # Check bounds: index >= jump_table_len
        asm.cmp(
            Operands.RegMem_Imm(
                reg_mem=RegMem.Reg(TEMP_REG), imm=ImmKind.I32(asm.jump_table_len)
            )
        )
        asm.jcc_label32(Condition.AboveOrEqual, asm.panic_label)

        # Jump to the machine code address
        asm.jmp(
            RegMem.Mem(
                MemOp.BaseIndexScaleOffset(
                    seg=None,
                    size=RegSize.R64,
                    base=Reg.r15,
                    index=RegIndex.rcx,
                    scale=Scale.x8,
                    offset=-VMContext.calculate_size(asm.jump_table_len),
                )
            )
        )

    def load_imm(self, asm, ra: int, lx: int, vx: int):
        """Load immediate value vx into register ra."""
        asm.mov_imm64(r_map[ra], z_inv(vx, 8))

    def load_u8(self, asm, ra: int, lx: int, vx: int):
        """Load unsigned 8-bit value from memory address vx into register ra."""
        mem = MemOp.BaseOffset(seg=None, size=RegSize.R64, base=Reg.r15, offset=vx)
        asm.load(kind=LoadKind.U8, reg=r_map[ra], mem=mem)

    def load_i8(self, asm, ra: int, lx: int, vx: int):
        """Load signed 8-bit value from memory address vx into register ra (sign extended)."""
        mem = MemOp.BaseOffset(seg=None, size=RegSize.R64, base=Reg.r15, offset=vx)
        asm.load(kind=LoadKind.I8, reg=r_map[ra], mem=mem)

    def load_u16(self, asm, ra: int, lx: int, vx: int):
        """Load unsigned 16-bit value from memory address vx into register ra."""
        mem = MemOp.BaseOffset(seg=None, size=RegSize.R64, base=Reg.r15, offset=vx)
        asm.load(kind=LoadKind.U16, reg=r_map[ra], mem=mem)

    def load_i16(self, asm, ra: int, lx: int, vx: int):
        """Load signed 16-bit value from memory address vx into register ra (sign extended)."""
        mem = MemOp.BaseOffset(seg=None, size=RegSize.R64, base=Reg.r15, offset=vx)
        asm.load(kind=LoadKind.I16, reg=r_map[ra], mem=mem)

    def load_u32(self, asm, ra: int, lx: int, vx: int):
        """Load unsigned 32-bit value from memory address vx into register ra."""
        mem = MemOp.BaseOffset(seg=None, size=RegSize.R64, base=Reg.r15, offset=vx)
        asm.load(kind=LoadKind.U32, reg=r_map[ra], mem=mem)

    def load_i32(self, asm, ra: int, lx: int, vx: int):
        """Load signed 32-bit value from memory address vx into register ra (sign extended)."""
        mem = MemOp.BaseOffset(seg=None, size=RegSize.R64, base=Reg.r15, offset=vx)
        asm.load(kind=LoadKind.I32, reg=r_map[ra], mem=mem)

    def load_u64(self, asm, ra: int, lx: int, vx: int):
        """Load unsigned 64-bit value from memory address vx into register ra."""
        mem = MemOp.BaseOffset(seg=None, size=RegSize.R64, base=Reg.r15, offset=vx)
        asm.load(kind=LoadKind.U64, reg=r_map[ra], mem=mem)

    def store_u8(self, asm, ra: int, lx: int, vx: int):
        """Store register ra as unsigned 8-bit value to memory address vx."""
        mem = MemOp.BaseOffset(seg=None, size=RegSize.R64, base=Reg.r15, offset=vx)
        asm.store(size=Size.U8, mem=mem, reg=r_map[ra])

    def store_u16(self, asm, ra: int, lx: int, vx: int):
        """Store register ra as unsigned 16-bit value to memory address vx."""
        mem = MemOp.BaseOffset(seg=None, size=RegSize.R64, base=Reg.r15, offset=vx)
        asm.store(size=Size.U16, mem=mem, reg=r_map[ra])

    def store_u32(self, asm, ra: int, lx: int, vx: int):
        """Store register ra as unsigned 32-bit value to memory address vx."""
        mem = MemOp.BaseOffset(seg=None, size=RegSize.R64, base=Reg.r15, offset=vx)
        asm.store(size=Size.U32, mem=mem, reg=r_map[ra])

    def store_u64(self, asm, ra: int, lx: int, vx: int):
        """Store register ra as unsigned 64-bit value to memory address vx."""
        mem = MemOp.BaseOffset(seg=None, size=RegSize.R64, base=Reg.r15, offset=vx)
        asm.store(size=Size.U64, mem=mem, reg=r_map[ra])
