from typing import Any, Callable, Dict, TYPE_CHECKING

from ....core.instruction_table import InstructionTable
from ....core.opcode import OpCode
from ...vm_context import r_map, TEMP_REG

from tsrkit_asm import (
    ImmKind,
    Reg,
    RegSize,
    Size,
    MemOp,
    PyAssembler,
    Operands,
    RegMem,
    RegIndex,
    Scale,
)


class InstructionsWArgs1Reg2Imm(InstructionTable):
    @property
    def ra(self) -> int:
        return min(12, self.program.zeta[self.counter + 1] % 16)

    @property
    def lx(self) -> int:
        return min(4, (self.program.zeta[self.counter + 1] // 16) % 8)

    @property
    def ly(self) -> int:
        return min(4, max(0, int(self.skip_index) - self.lx - 1))

    @property
    def vx(self) -> int:
        start = self.counter + 2
        end = start + self.lx
        return int.from_bytes(self.program.zeta[start:end], "little", signed=False)

    @property
    def vy(self) -> int:
        start = self.counter + 2 + self.lx
        end = start + self.ly
        return int.from_bytes(self.program.zeta[start:end], "little", signed=False)

    @classmethod
    def table(cls) -> Dict[int, OpCode]:
        return {
            70: OpCode("store_imm_ind_u8", cls.store_imm_ind_u8, 1, False),
            71: OpCode("store_imm_ind_u16", cls.store_imm_ind_u16, 1, False),
            72: OpCode("store_imm_ind_u32", cls.store_imm_ind_u32, 1, False),
            73: OpCode("store_imm_ind_u64", cls.store_imm_ind_u64, 1, False),
        }

    def store_imm_ind_u8(self, asm: PyAssembler):
        """Store immediate value vy as u8 at memory [ra + vx]"""
        # Calculate address: [r15 + ra + vx]
        asm.mov(size=RegSize.R64, a=TEMP_REG, b=r_map[self.ra])
        if self.vx != 0:
            asm.add(
                Operands.RegMem_Imm(
                    reg_mem=RegMem.Reg(TEMP_REG), imm=ImmKind.I64(self.vx)
                )
            )
        # Store immediate value to calculated address
        asm.mov_imm(
            RegMem.Mem(
                MemOp.BaseIndexScaleOffset(
                    seg=None,
                    size=RegSize.R64,
                    base=Reg.r15,
                    index=RegIndex.rcx,
                    scale=Scale.x1,
                    offset=0,
                )
            ),
            ImmKind.I8(self.vy % 2**8),
        )

    def store_imm_ind_u16(self, asm: PyAssembler):
        """Store immediate value vy as u16 at memory [ra + vx]"""
        # Calculate address: [r15 + ra + vx]
        asm.mov(size=RegSize.R64, a=TEMP_REG, b=r_map[self.ra])
        if self.vx != 0:
            asm.add(
                Operands.RegMem_Imm(
                    reg_mem=RegMem.Reg(TEMP_REG), imm=ImmKind.I64(self.vx)
                )
            )
        # Store immediate value to calculated address
        asm.mov_imm(
            RegMem.Mem(
                MemOp.BaseIndexScaleOffset(
                    seg=None,
                    size=RegSize.R64,
                    base=Reg.r15,
                    index=RegIndex.rcx,
                    scale=Scale.x1,
                    offset=0,
                )
            ),
            ImmKind.I16(self.vy % 2**16),
        )

    def store_imm_ind_u32(self, asm: PyAssembler):
        """Store immediate value vy as u32 at memory [ra + vx]"""
        # Calculate address: [r15 + ra + vx]
        asm.mov(size=RegSize.R64, a=TEMP_REG, b=r_map[self.ra])
        if self.vx != 0:
            asm.add(
                Operands.RegMem_Imm(
                    reg_mem=RegMem.Reg(TEMP_REG), imm=ImmKind.I64(self.vx)
                )
            )
        # Store immediate value to calculated address
        asm.mov_imm(
            RegMem.Mem(
                MemOp.BaseIndexScaleOffset(
                    seg=None,
                    size=RegSize.R64,
                    base=Reg.r15,
                    index=RegIndex.rcx,
                    scale=Scale.x1,
                    offset=0,
                )
            ),
            ImmKind.I32(self.vy % 2**32),
        )

    def store_imm_ind_u64(self, asm: PyAssembler):
        """Store immediate value vy as u64 at memory [ra + vx]"""
        # Calculate address: [r15 + ra + vx]
        asm.mov(size=RegSize.R64, a=TEMP_REG, b=r_map[self.ra])
        if self.vx != 0:
            asm.add(
                Operands.RegMem_Imm(
                    reg_mem=RegMem.Reg(TEMP_REG), imm=ImmKind.I64(self.vx)
                )
            )
        # Store immediate value to calculated address
        asm.mov_imm(
            RegMem.Mem(
                MemOp.BaseIndexScaleOffset(
                    seg=None,
                    size=RegSize.R64,
                    base=Reg.r15,
                    index=RegIndex.rcx,
                    scale=Scale.x1,
                    offset=0,
                )
            ),
            ImmKind.I64(self.vy),
        )
