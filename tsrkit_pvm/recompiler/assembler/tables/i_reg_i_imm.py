from typing import Any, Callable, Dict, TYPE_CHECKING

from tsrkit_pvm.interpreter.utils import chi

from ..instruction_table import InstructionTable
from ..opcode import OpCode
from ...vm_context import r_map

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
)


class InstructionsWArgs1Reg1Imm(InstructionTable):
    @property
    def ra(self) -> int:
        return min(12, int(self.program.zeta[self.counter + 1]) % 16)

    @property
    def lx(self) -> int:
        return min(4, max(0, self.skip_index - 1))
    
    @property
    def vx(self) -> int:
        start = self.counter + 2
        end = start + self.lx
        return chi(
            int.from_bytes(
                self.program.zeta[start:end],
                "little"
            ),
            self.lx
        )

    @classmethod
    def table(cls) -> Dict[int, OpCode]:
        return {
            50: OpCode(name="jump_ind", fn=cls.jump_ind, gas=1, is_terminating=False),
            51: OpCode(name="load_imm", fn=cls.load_imm, gas=1, is_terminating=False),
            52: OpCode(name="load_u8", fn=cls.load_u(8), gas=1, is_terminating=False),
            53: OpCode(name="load_i8", fn=cls.load_i(8), gas=1, is_terminating=False),
            54: OpCode(name="load_u16", fn=cls.load_u(16), gas=1, is_terminating=False),
            55: OpCode(name="load_i16", fn=cls.load_i(16), gas=1, is_terminating=False),
            56: OpCode(name="load_u32", fn=cls.load_u(32), gas=1, is_terminating=False),
            57: OpCode(name="load_i32", fn=cls.load_i(32), gas=1, is_terminating=False),
            58: OpCode(name="load_u64", fn=cls.load_u(64), gas=1, is_terminating=False),
            59: OpCode(name="store_u8", fn=cls.store_u(8), gas=1, is_terminating=False),
            60: OpCode(name="store_u16", fn=cls.store_u(16), gas=1, is_terminating=False),
            61: OpCode(name="store_u32", fn=cls.store_u(32), gas=1, is_terminating=False),
            62: OpCode(name="store_u64", fn=cls.store_u(64), gas=1, is_terminating=False),
        }

    def jump_ind(self, asm):
        """Indirect jump to address stored in register RB plus immediate VX."""
        asm.mov(size=RegSize.R64, a=Reg.rdx, b=r_map[self.ra])  # Copy RA to RDX
        asm.add(Operands.RegMem_Imm(reg_mem=RegMem.Reg(Reg.rdx), imm=ImmKind.I64(value=self.vx)))
        asm.ud2()

    def load_imm(self, asm):
        asm.mov_imm64(r_map[self.ra], self.vx)

    @staticmethod
    def load_u(bitsize: int) -> Callable[[Any, PyAssembler], None]:
        size_kind_map = {8: LoadKind.U8, 16: LoadKind.U16, 32: LoadKind.U32, 64: LoadKind.U64}

        def impl(self, asm: PyAssembler):
            mem = MemOp.BaseOffset(seg=None, size=RegSize.R64, base=Reg.r14, offset=int(self.vx))
            asm.load(size_kind_map[bitsize], reg=r_map[self.ra], mem=mem)
        return impl

    @staticmethod
    def load_i(bitsize: int) -> Callable[[Any, PyAssembler], None]:
        size_kind_map = {8: LoadKind.I8, 16: LoadKind.I16, 32: LoadKind.I32}
        def impl(self, asm: PyAssembler):
            mem = MemOp.BaseOffset(seg=None, size=RegSize.R64, base=Reg.r14, offset=int(self.vx))
            asm.load(size_kind_map[bitsize], reg=r_map[self.ra], mem=mem)
        return impl

    @staticmethod
    def store_u(bitsize: int) -> Callable[[Any, PyAssembler], None]:
        size_map = {8: Size.U8, 16: Size.U16, 32: Size.U32, 64: Size.U64}
        def impl(self, asm: PyAssembler):
            mem = MemOp.BaseOffset(seg=None, size=RegSize.R64, base=Reg.r14, offset=int(self.vx))
            asm.store(size_map[bitsize], mem=mem, reg=r_map[self.ra])
        return impl
