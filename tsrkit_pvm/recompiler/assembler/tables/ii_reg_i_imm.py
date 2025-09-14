from typing import Any, Callable, Dict, TYPE_CHECKING

from tsrkit_pvm.common.utils import chi, z
from tsrkit_asm import (
    Reg,
    RegSize,
    MemOp,
    Operands,
    RegMem,
    ImmKind,
    Size,
    LoadKind,
    Condition,
    RegIndex,
    Scale,
)
from ....core.instruction_table import InstructionTable
from ....core.opcode import OpCode
from ....core.program_base import Program

if TYPE_CHECKING:
    from ...program import REC_Program

from ...vm_context import r_map, rindex_map, TEMP_REG


class InstructionsWArgs2Reg1Imm(InstructionTable):
    def __init__(self, counter: int, program: Program, skip_index: int) -> None:
        self.counter = counter
        self.program = program
        self.skip_index = skip_index


    def get_props(self):
        ra = min(12, self.program.zeta[self.counter + 1] % 16)
        rb = min(12, self.program.zeta[self.counter + 1] // 16)
        lx = min(4, max(0, self.skip_index - 1))
        start = self.counter + 2
        end = start + lx
        vx_signed = int.from_bytes(self.program.zeta[start:end], "little")
        vx = chi(vx_signed, lx)
        return (ra, rb, lx, vx_signed, vx)

    @classmethod
    def table(cls) -> Dict[int, OpCode]:
        return {
            120: OpCode(
                name="store_ind_u8", fn=cls.store_ind_u8, gas=1, is_terminating=False
            ),
            121: OpCode(
                name="store_ind_u16", fn=cls.store_ind_u16, gas=1, is_terminating=False
            ),
            122: OpCode(
                name="store_ind_u32", fn=cls.store_ind_u32, gas=1, is_terminating=False
            ),
            123: OpCode(
                name="store_ind_u64", fn=cls.store_ind_u64, gas=1, is_terminating=False
            ),
            124: OpCode(
                name="load_ind_u8", fn=cls.load_ind_u8, gas=1, is_terminating=False
            ),
            125: OpCode(
                name="load_ind_i8", fn=cls.load_ind_i8, gas=1, is_terminating=False
            ),
            126: OpCode(
                name="load_ind_u16", fn=cls.load_ind_u16, gas=1, is_terminating=False
            ),
            127: OpCode(
                name="load_ind_i16", fn=cls.load_ind_i16, gas=1, is_terminating=False
            ),
            128: OpCode(
                name="load_ind_u32", fn=cls.load_ind_u32, gas=1, is_terminating=False
            ),
            129: OpCode(
                name="load_ind_i32", fn=cls.load_ind_i32, gas=1, is_terminating=False
            ),
            130: OpCode(
                name="load_ind_u64", fn=cls.load_ind_u64, gas=1, is_terminating=False
            ),
            131: OpCode(
                name="add_imm_32", fn=cls.add_imm_32, gas=1, is_terminating=False
            ),
            132: OpCode(name="and_imm", fn=cls.and_imm, gas=1, is_terminating=False),
            133: OpCode(name="xor_imm", fn=cls.xor_imm, gas=1, is_terminating=False),
            134: OpCode(name="or_imm", fn=cls.or_imm, gas=1, is_terminating=False),
            135: OpCode(
                name="mul_imm_32", fn=cls.mul_imm_32, gas=1, is_terminating=False
            ),
            136: OpCode(
                name="set_lt_u_imm", fn=cls.set_lt_u_imm, gas=1, is_terminating=False
            ),
            137: OpCode(
                name="set_lt_s_imm", fn=cls.set_lt_s_imm, gas=1, is_terminating=False
            ),
            138: OpCode(
                name="shlo_l_imm_32", fn=cls.shlo_l_imm_32, gas=1, is_terminating=False
            ),
            139: OpCode(
                name="shlo_r_imm_32", fn=cls.shlo_r_imm_32, gas=1, is_terminating=False
            ),
            140: OpCode(
                name="shar_r_imm_32", fn=cls.shar_r_imm_32, gas=1, is_terminating=False
            ),
            141: OpCode(
                name="neg_add_imm_32",
                fn=cls.neg_add_imm_32,
                gas=1,
                is_terminating=False,
            ),
            142: OpCode(
                name="set_gt_u_imm", fn=cls.set_gt_u_imm, gas=1, is_terminating=False
            ),
            143: OpCode(
                name="set_gt_s_imm", fn=cls.set_gt_s_imm, gas=1, is_terminating=False
            ),
            144: OpCode(
                name="shlo_l_imm_alt_32",
                fn=cls.shlo_l_imm_alt_32,
                gas=1,
                is_terminating=False,
            ),
            145: OpCode(
                name="shlo_r_imm_alt_32",
                fn=cls.shlo_r_imm_alt_32,
                gas=1,
                is_terminating=False,
            ),
            146: OpCode(
                name="shar_r_imm_alt_32",
                fn=cls.shar_r_imm_alt_32,
                gas=1,
                is_terminating=False,
            ),
            147: OpCode(
                name="cmov_iz_imm", fn=cls.cmov_iz_imm, gas=1, is_terminating=False
            ),
            148: OpCode(
                name="cmov_nz_imm", fn=cls.cmov_nz_imm, gas=1, is_terminating=False
            ),
            149: OpCode(
                name="add_imm_64", fn=cls.add_imm_64, gas=1, is_terminating=False
            ),
            150: OpCode(
                name="mul_imm_64", fn=cls.mul_imm_64, gas=1, is_terminating=False
            ),
            151: OpCode(
                name="shlo_l_imm_64", fn=cls.shlo_l_imm_64, gas=1, is_terminating=False
            ),
            152: OpCode(
                name="shlo_r_imm_64", fn=cls.shlo_r_imm_64, gas=1, is_terminating=False
            ),
            153: OpCode(
                name="shar_r_imm_64", fn=cls.shar_r_imm_64, gas=1, is_terminating=False
            ),
            154: OpCode(
                name="neg_add_imm_64",
                fn=cls.neg_add_imm_64,
                gas=1,
                is_terminating=False,
            ),
            155: OpCode(
                name="shlo_l_imm_alt_64",
                fn=cls.shlo_l_imm_alt_64,
                gas=1,
                is_terminating=False,
            ),
            156: OpCode(
                name="shlo_r_imm_alt_64",
                fn=cls.shlo_r_imm_alt_64,
                gas=1,
                is_terminating=False,
            ),
            157: OpCode(
                name="shar_r_imm_alt_64",
                fn=cls.shar_r_imm_alt_64,
                gas=1,
                is_terminating=False,
            ),
            158: OpCode(
                name="rot_r_64_imm", fn=cls.rot_r_64_imm, gas=1, is_terminating=False
            ),
            159: OpCode(
                name="rot_r_64_imm_alt",
                fn=cls.rot_r_64_imm_alt,
                gas=1,
                is_terminating=False,
            ),
            160: OpCode(
                name="rot_r_32_imm", fn=cls.rot_r_32_imm, gas=1, is_terminating=False
            ),
            161: OpCode(
                name="rot_r_32_imm_alt",
                fn=cls.rot_r_32_imm_alt,
                gas=1,
                is_terminating=False,
            ),
        }

    def store_ind_u8(self, asm, ra: int, rb: int, lx: int, vx_signed: int, vx: int):
        """u8 [rb + vx] = ra"""
        asm.store(
            size=Size.U8,
            mem=MemOp.BaseIndexScaleOffset(
                seg=None,
                size=RegSize.R64,
                base=Reg.r15,
                index=rindex_map[rb],
                scale=Scale.x1,
                offset=z(vx, 8),
            ),
            reg=r_map[ra],
        )

    def store_ind_u16(self, asm, ra: int, rb: int, lx: int, vx_signed: int, vx: int):
        """u16 [rb + vx] = ra"""
        asm.store(
            size=Size.U16,
            mem=MemOp.BaseIndexScaleOffset(
                seg=None,
                size=RegSize.R64,
                base=Reg.r15,
                index=rindex_map[rb],
                scale=Scale.x1,
                offset=z(vx, 8),
            ),
            reg=r_map[ra],
        )

    def store_ind_u32(self, asm, ra: int, rb: int, lx: int, vx_signed: int, vx: int):
        """u32 [rb + vx] = ra"""
        asm.store(
            size=Size.U32,
            mem=MemOp.BaseIndexScaleOffset(
                seg=None,
                size=RegSize.R64,
                base=Reg.r15,
                index=rindex_map[rb],
                scale=Scale.x1,
                offset=z(vx, 8),
            ),
            reg=r_map[ra],
        )

    def store_ind_u64(self, asm, ra: int, rb: int, lx: int, vx_signed: int, vx: int):
        """u64 [rb + vx] = ra"""
        asm.store(
            size=Size.U64,
            mem=MemOp.BaseIndexScaleOffset(
                seg=None,
                size=RegSize.R64,
                base=Reg.r15,
                index=rindex_map[rb],
                scale=Scale.x1,
                offset=z(vx, 8),
            ),
            reg=r_map[ra],
        )

    def load_ind_u8(self, asm, ra: int, rb: int, lx: int, vx_signed: int, vx: int):
        """ra = u8 [rb + vx]"""
        asm.load(
            kind=LoadKind.U8,
            reg=r_map[ra],
            mem=MemOp.BaseIndexScaleOffset(
                seg=None,
                size=RegSize.R64,
                base=Reg.r15,
                index=rindex_map[rb],
                scale=Scale.x1,
                offset=z(vx, 8),
            ),
        )

    def load_ind_i8(self, asm, ra: int, rb: int, lx: int, vx_signed: int, vx: int):
        """ra = i8 [rb + vx] (sign extended)"""
        asm.load(
            kind=LoadKind.I8,
            reg=r_map[ra],
            mem=MemOp.BaseIndexScaleOffset(
                seg=None,
                size=RegSize.R64,
                base=Reg.r15,
                index=rindex_map[rb],
                scale=Scale.x1,
                offset=z(vx, 8),
            ),
        )

    def load_ind_u16(self, asm, ra: int, rb: int, lx: int, vx_signed: int, vx: int):
        """ra = u16 [rb + vx]"""
        asm.load(
            kind=LoadKind.U16,
            reg=r_map[ra],
            mem=MemOp.BaseIndexScaleOffset(
                seg=None,
                size=RegSize.R64,
                base=Reg.r15,
                index=rindex_map[rb],
                scale=Scale.x1,
                offset=z(vx, 8),
            ),
        )

    def load_ind_i16(self, asm, ra: int, rb: int, lx: int, vx_signed: int, vx: int):
        """ra = i16 [rb + vx] (sign extended)"""
        asm.load(
            kind=LoadKind.I16,
            reg=r_map[ra],
            mem=MemOp.BaseIndexScaleOffset(
                seg=None,
                size=RegSize.R64,
                base=Reg.r15,
                index=rindex_map[rb],
                scale=Scale.x1,
                offset=z(vx, 8),
            ),
        )

    def load_ind_u32(self, asm, ra: int, rb: int, lx: int, vx_signed: int, vx: int):
        """ra = u32 [rb + vx]"""
        asm.load(
            kind=LoadKind.U32,
            reg=r_map[ra],
            mem=MemOp.BaseIndexScaleOffset(
                seg=None,
                size=RegSize.R64,
                base=Reg.r15,
                index=rindex_map[rb],
                scale=Scale.x1,
                offset=z(vx, 8),
            ),
        )

    def load_ind_i32(self, asm, ra: int, rb: int, lx: int, vx_signed: int, vx: int):
        """ra = i32 [rb + vx] (sign extended)"""
        asm.load(
            kind=LoadKind.I32,
            reg=r_map[ra],
            mem=MemOp.BaseIndexScaleOffset(
                seg=None,
                size=RegSize.R64,
                base=Reg.r15,
                index=rindex_map[rb],
                scale=Scale.x1,
                offset=z(vx, 8),
            ),
        )

    def load_ind_u64(self, asm, ra: int, rb: int, lx: int, vx_signed: int, vx: int):
        """ra = u64 [rb + vx]"""
        asm.load(
            kind=LoadKind.U64,
            reg=r_map[ra],
            mem=MemOp.BaseIndexScaleOffset(
                seg=None,
                size=RegSize.R64,
                base=Reg.r15,
                index=rindex_map[rb],
                scale=Scale.x1,
                offset=z(vx, 8),
            ),
        )

    def add_imm_32(self, asm, ra: int, rb: int, lx: int, vx_signed: int, vx: int):
        """ra = (rb + vx) % 2^32, then sign-extend to 64 bits"""
        if ra != rb:
            # Load rb into ra (32-bit)
            asm.mov(size=RegSize.R32, a=r_map[ra], b=r_map[rb])
        # Add vx to ra
        asm.add(
            Operands.RegMem_Imm(
                reg_mem=RegMem.Reg(r_map[ra]),
                imm=ImmKind.I64(z(vx, 8)),
            )
        )
        # Sign-extend 32-bit result to 64 bits (PVM requirement)
        asm.movsxd_32_to_64(r_map[ra], r_map[ra])

    def and_imm(self, asm, ra: int, rb: int, lx: int, vx_signed: int, vx: int):
        """ra = rb & vx (bitwise AND)"""
        # Load rb into ra
        asm.mov(size=RegSize.R64, a=r_map[ra], b=r_map[rb])
        # AND with immediate
        asm.and_(
            Operands.RegMem_Imm(
                reg_mem=RegMem.Reg(r_map[ra]), imm=ImmKind.I64(z(vx, 8))
            )
        )

    def xor_imm(self, asm, ra: int, rb: int, lx: int, vx_signed: int, vx: int):
        """ra = rb ^ vx (bitwise XOR)"""
        # Load rb into ra
        asm.mov(size=RegSize.R64, a=r_map[ra], b=r_map[rb])
        # XOR with immediate
        asm.xor_(
            Operands.RegMem_Imm(
                reg_mem=RegMem.Reg(r_map[ra]), imm=ImmKind.I64(z(vx, 8))
            )
        )

    def or_imm(self, asm, ra: int, rb: int, lx: int, vx_signed: int, vx: int):
        """ra = rb | vx (bitwise OR)"""
        # Load rb into ra
        asm.mov(size=RegSize.R64, a=r_map[ra], b=r_map[rb])
        # OR with immediate
        asm.or_(
            Operands.RegMem_Imm(
                reg_mem=RegMem.Reg(r_map[ra]), imm=ImmKind.I64(z(vx, 8))
            )
        )

    def mul_imm_32(self, asm, ra: int, rb: int, lx: int, vx_signed: int, vx: int):
        """ra = (rb * vx) % 2^32"""
        # Load immediate into temp register
        asm.mov_imm64(TEMP_REG, vx & 0xFFFFFFFF)
        # Load rb into ra (32-bit)
        asm.mov(size=RegSize.R32, a=r_map[ra], b=r_map[rb])
        # Multiply ra by rcx (32-bit)
        asm.imul(RegSize.R32, r_map[ra], RegMem.Reg(TEMP_REG))
        # Sign-extend 32-bit result to 64 bits (PVM requirement)
        asm.movsxd_32_to_64(r_map[ra], r_map[ra])

    def set_lt_u_imm(self, asm, ra: int, rb: int, lx: int, vx_signed: int, vx: int):
        """ra = (rb < vx) ? 1 : 0 (unsigned)"""
        # Handle large immediate values by using a temporary register
        if abs(vx) > 0x7FFFFFFFFFFFFFFF:  # If too large for signed I64
            asm.mov_imm64(TEMP_REG, vx)
            asm.cmp(
                Operands.RegMem_Reg(
                    size=Size.U64, reg_mem=RegMem.Reg(r_map[rb]), reg=TEMP_REG
                )
            )
        else:
            asm.cmp(
                Operands.RegMem_Imm(
                    reg_mem=RegMem.Reg(r_map[rb]), imm=ImmKind.I64(vx)
                )
            )
        # Clear ra register first (setcc only sets the low 8 bits)
        asm.mov_imm64(r_map[ra], 0)
        # Set ra based on unsigned less than condition
        asm.setcc(Condition.Below, RegMem.Reg(r_map[ra]))

    def set_lt_s_imm(self, asm, ra: int, rb: int, lx: int, vx_signed: int, vx: int):
        """ra = (rb < vx) ? 1 : 0 (signed)"""
        # Handle large immediate values by using a temporary register
        if abs(vx) > 0x7FFFFFFFFFFFFFFF:  # If too large for signed I64
            asm.mov_imm64(TEMP_REG, vx)
            asm.cmp(
                Operands.RegMem_Reg(
                    size=Size.U64, reg_mem=RegMem.Reg(r_map[rb]), reg=TEMP_REG
                )
            )
        else:
            asm.cmp(
                Operands.RegMem_Imm(
                    reg_mem=RegMem.Reg(r_map[rb]), imm=ImmKind.I64(vx)
                )
            )
        # Clear ra register first (setcc only sets the low 8 bits)
        asm.mov_imm64(r_map[ra], 0)
        # Set ra based on signed less than condition
        asm.setcc(Condition.Less, RegMem.Reg(r_map[ra]))

    def shlo_l_imm_32(self, asm, ra: int, rb: int, lx: int, vx_signed: int, vx: int):
        """ra = (rb << (vx % 32)) % 2^32 (left shift logical)"""
        # Load rb into ra (32-bit)
        asm.mov(size=RegSize.R32, a=r_map[ra], b=r_map[rb])
        # Shift left by immediate
        asm.shl_imm(RegSize.R32, RegMem.Reg(r_map[ra]), vx & 0x1F)
        # Sign-extend 32-bit result to 64 bits (PVM requirement)
        asm.movsxd_32_to_64(r_map[ra], r_map[ra])

    def shlo_r_imm_32(self, asm, ra: int, rb: int, lx: int, vx_signed: int, vx: int):
        """ra = (rb >> (vx % 32)) (right shift logical 32-bit)"""
        # Load rb into ra (32-bit)
        asm.mov(size=RegSize.R32, a=r_map[ra], b=r_map[rb])
        # Shift right logical by immediate
        asm.shr_imm(RegSize.R32, RegMem.Reg(r_map[ra]), vx & 0x1F)
        # Sign-extend 32-bit result to 64 bits (PVM requirement)
        asm.movsxd_32_to_64(r_map[ra], r_map[ra])

    def shar_r_imm_32(self, asm, ra: int, rb: int, lx: int, vx_signed: int, vx: int):
        """ra = (rb >> (vx % 32)) (arithmetic right shift 32-bit)"""
        # Load rb into ra (32-bit)
        asm.mov(size=RegSize.R32, a=r_map[ra], b=r_map[rb])
        # Shift right arithmetic by immediate
        asm.sar_imm(RegSize.R32, RegMem.Reg(r_map[ra]), vx & 0x1F)
        # Sign-extend 32-bit result to 64 bits (PVM requirement)
        asm.movsxd_32_to_64(r_map[ra], r_map[ra])

    def neg_add_imm_32(self, asm, ra: int, rb: int, lx: int, vx_signed: int, vx: int):
        """ra = (vx - rb) % 2^32"""
        if ra == rb:
            asm.neg(Size.U32, RegMem.Reg(r_map[ra]))

            asm.add(
                Operands.RegMem_Imm(
                    reg_mem=RegMem.Reg(r_map[ra]),
                    imm=ImmKind.I32(vx & 0xFFFFFFFF),
                )
            )
        else:
            # Load immediate into ra
            asm.mov_imm(RegMem.Reg(r_map[ra]), ImmKind.I32(vx & 0xFFFFFFFF))
            # Subtract rb from ra
            asm.sub(
                Operands.RegMem_Reg(
                    Size.U32, reg_mem=RegMem.Reg(r_map[ra]), reg=r_map[rb]
                )
            )
        # Sign-extend 32-bit result to 64 bits (PVM requirement)
        asm.movsxd_32_to_64(r_map[ra], r_map[ra])

    def set_gt_u_imm(self, asm, ra: int, rb: int, lx: int, vx_signed: int, vx: int):
        """ra = (rb > vx) ? 1 : 0 (unsigned)"""
        # Handle large immediate values by using a temporary register
        if abs(vx) > 0x7FFFFFFFFFFFFFFF:  # If too large for signed I64
            asm.mov_imm64(TEMP_REG, vx)
            asm.cmp(
                Operands.RegMem_Reg(
                    size=Size.U64, reg_mem=RegMem.Reg(r_map[rb]), reg=TEMP_REG
                )
            )
        else:
            asm.cmp(
                Operands.RegMem_Imm(
                    reg_mem=RegMem.Reg(r_map[rb]), imm=ImmKind.I64(vx)
                )
            )
        # Clear ra register first (setcc only sets the low 8 bits)
        asm.mov_imm64(r_map[ra], 0)
        # Set ra based on unsigned greater than condition
        asm.setcc(Condition.Above, RegMem.Reg(r_map[ra]))

    def set_gt_s_imm(self, asm, ra: int, rb: int, lx: int, vx_signed: int, vx: int):
        """ra = (rb > vx) ? 1 : 0 (signed)"""
        # Handle large immediate values by using a temporary register
        if abs(vx) > 0x7FFFFFFFFFFFFFFF:  # If too large for signed I64
            asm.mov_imm64(TEMP_REG, vx)
            asm.cmp(
                Operands.RegMem_Reg(
                    size=Size.U64, reg_mem=RegMem.Reg(r_map[rb]), reg=TEMP_REG
                )
            )
        else:
            asm.cmp(
                Operands.RegMem_Imm(
                    reg_mem=RegMem.Reg(r_map[rb]), imm=ImmKind.I64(vx)
                )
            )
        # Clear ra register first (setcc only sets the low 8 bits)
        asm.mov_imm64(r_map[ra], 0)
        # Set ra based on signed greater than condition
        asm.setcc(Condition.Greater, RegMem.Reg(r_map[ra]))

    def shlo_l_imm_alt_32(self, asm, ra: int, rb: int, lx: int, vx_signed: int, vx: int):
        """ra = (vx << (rb % 32)) % 2^32 (alternate: immediate shifted by register)"""
        # Load rb into rcx (shift amount) - cl is the low 8 bits of rcx
        asm.mov(size=RegSize.R64, a=TEMP_REG, b=r_map[rb])
        # Load immediate into ra (32-bit)
        asm.mov_imm(RegMem.Reg(r_map[ra]), ImmKind.I32(vx & 0xFFFFFFFF))
        # Mask shift amount
        asm.and_(
            Operands.RegMem_Imm(reg_mem=RegMem.Reg(TEMP_REG), imm=ImmKind.I8(0x1F))
        )
        # Shift left by cl (using shl_cl method) - 32-bit operation
        asm.shl_cl(RegSize.R32, RegMem.Reg(r_map[ra]))
        # Sign-extend 32-bit result to 64 bits (PVM requirement)
        asm.movsxd_32_to_64(r_map[ra], r_map[ra])

    def shlo_r_imm_alt_32(self, asm, ra: int, rb: int, lx: int, vx_signed: int, vx: int):
        """ra = (vx >> (rb % 32)) (alternate: immediate shifted by register)"""
        # Load rb into rcx (shift amount) - cl is the low 8 bits of rcx
        asm.mov(size=RegSize.R64, a=TEMP_REG, b=r_map[rb])
        # Load immediate into ra (32-bit)
        asm.mov_imm(RegMem.Reg(r_map[ra]), ImmKind.I32(vx & 0xFFFFFFFF))
        # Mask shift amount
        asm.and_(
            Operands.RegMem_Imm(reg_mem=RegMem.Reg(TEMP_REG), imm=ImmKind.I8(0x1F))
        )
        # Shift right logical by cl (using shr_cl method) - 32-bit operation
        asm.shr_cl(RegSize.R32, RegMem.Reg(r_map[ra]))
        # Sign-extend 32-bit result to 64 bits (PVM requirement)
        asm.movsxd_32_to_64(r_map[ra], r_map[ra])

    def shar_r_imm_alt_32(self, asm, ra: int, rb: int, lx: int, vx_signed: int, vx: int):
        """ra = (vx >> (rb % 32)) arithmetic (alternate: immediate shifted by register)"""
        # Load rb into rcx (shift amount) - cl is the low 8 bits of rcx
        asm.mov(size=RegSize.R64, a=TEMP_REG, b=r_map[rb])
        # Load immediate into ra (32-bit)
        asm.mov_imm(RegMem.Reg(r_map[ra]), ImmKind.I32(vx & 0xFFFFFFFF))
        # Mask shift amount
        asm.and_(
            Operands.RegMem_Imm(reg_mem=RegMem.Reg(TEMP_REG), imm=ImmKind.I8(0x1F))
        )
        # Shift right arithmetic by cl (using sar_cl method) - 32-bit operation
        asm.sar_cl(RegSize.R32, RegMem.Reg(r_map[ra]))
        # Sign-extend 32-bit result to 64 bits (PVM requirement)
        asm.movsxd_32_to_64(r_map[ra], r_map[ra])

    def cmov_iz_imm(self, asm, ra: int, rb: int, lx: int, vx_signed: int, vx: int):
        """ra = (rb == 0) ? vx : ra (conditional move if zero)"""
        # Test if rb is zero by testing against itself
        asm.test(
            Operands.RegMem_Reg(
                size=Size.U64, reg_mem=RegMem.Reg(r_map[rb]), reg=r_map[rb]
            )
        )
        # Load immediate into a temp register
        asm.mov_imm64(TEMP_REG, vx)
        # Conditionally move if zero (using cmov with Equal condition)
        asm.cmov(Condition.Equal, RegSize.R64, r_map[ra], RegMem.Reg(TEMP_REG))

    def cmov_nz_imm(self, asm, ra: int, rb: int, lx: int, vx_signed: int, vx: int):
        """ra = (rb != 0) ? vx : ra (conditional move if not zero)"""
        # Test if rb is zero by testing against itself
        asm.test(
            Operands.RegMem_Reg(
                size=Size.U64, reg_mem=RegMem.Reg(r_map[rb]), reg=r_map[rb]
            )
        )
        # Load immediate into a temp register
        asm.mov_imm64(TEMP_REG, vx)
        # Conditionally move if not zero (using cmov with NotEqual condition)
        asm.cmov(Condition.NotEqual, RegSize.R64, r_map[ra], RegMem.Reg(TEMP_REG))

    def add_imm_64(self, asm, ra: int, rb: int, lx: int, vx_signed: int, vx: int):
        """ra = rb + vx"""
        # Load rb into ra
        if rb != ra:
            asm.mov(size=RegSize.R64, a=r_map[ra], b=r_map[rb])
        asm.add(
            Operands.RegMem_Imm(
                reg_mem=RegMem.Reg(r_map[ra]), imm=ImmKind.I64(z(vx, 8))
            )
        )

    def mul_imm_64(self, asm, ra: int, rb: int, lx: int, vx_signed: int, vx: int):
        """ra = (rb * vx) % 2^64"""
        # Load immediate into a temp register
        asm.mov_imm64(TEMP_REG, vx)
        # Load rb into ra
        asm.mov(size=RegSize.R64, a=r_map[ra], b=r_map[rb])
        # Multiply ra by rcx
        asm.imul(RegSize.R64, r_map[ra], RegMem.Reg(TEMP_REG))

    def shlo_l_imm_64(self, asm, ra: int, rb: int, lx: int, vx_signed: int, vx: int):
        """ra = rb << (vx % 64) (left shift logical 64-bit)"""
        # Load rb into ra
        asm.mov(size=RegSize.R64, a=r_map[ra], b=r_map[rb])
        # Shift left by immediate
        asm.shl_imm(RegSize.R64, RegMem.Reg(r_map[ra]), vx & 0x3F)

    def shlo_r_imm_64(self, asm, ra: int, rb: int, lx: int, vx_signed: int, vx: int):
        """ra = rb >> (vx % 64) (right shift logical 64-bit)"""
        # Load rb into ra
        asm.mov(size=RegSize.R64, a=r_map[ra], b=r_map[rb])
        # Shift right logical by immediate
        asm.shr_imm(RegSize.R64, RegMem.Reg(r_map[ra]), vx & 0x3F)

    def shar_r_imm_64(self, asm, ra: int, rb: int, lx: int, vx_signed: int, vx: int):
        """ra = rb >> (vx % 64) (arithmetic right shift 64-bit)"""
        # Load rb into ra
        asm.mov(size=RegSize.R64, a=r_map[ra], b=r_map[rb])
        # Shift right arithmetic by immediate
        asm.sar_imm(RegSize.R64, RegMem.Reg(r_map[ra]), vx & 0x3F)

    def neg_add_imm_64(self, asm, ra: int, rb: int, lx: int, vx_signed: int, vx: int):
        """ra = vx - rb"""
        if ra == rb:
            asm.neg(Size.U64, RegMem.Reg(r_map[ra]))
            asm.add(
                Operands.RegMem_Imm(
                    reg_mem=RegMem.Reg(r_map[ra]), imm=ImmKind.I64(z(vx, 8))
                )
            )
        else:
            # Load immediate into ra
            asm.mov_imm64(r_map[ra], vx)
            # Subtract rb from ra
            asm.sub(
                Operands.RegMem_Reg(
                    size=Size.U64,
                    reg_mem=RegMem.Reg(r_map[ra]),
                    reg=r_map[rb],
                )
            )

    def shlo_l_imm_alt_64(self, asm, ra: int, rb: int, lx: int, vx_signed: int, vx: int):
        """ra = vx << (rb % 64) (alternate: immediate shifted by register)"""
        # Load rb into rcx (shift amount) - cl is the low 8 bits of rcx
        asm.mov(size=RegSize.R64, a=TEMP_REG, b=r_map[rb])
        # Load immediate into ra
        asm.mov_imm64(r_map[ra], vx)
        # Mask shift amount
        asm.and_(
            Operands.RegMem_Imm(reg_mem=RegMem.Reg(TEMP_REG), imm=ImmKind.I8(0x3F))
        )
        # Shift left by cl (using shl_cl method)
        asm.shl_cl(RegSize.R64, RegMem.Reg(r_map[ra]))

    def shlo_r_imm_alt_64(self, asm, ra: int, rb: int, lx: int, vx_signed: int, vx: int):
        """ra = vx >> (rb % 64) (alternate: immediate shifted by register)"""
        # Load rb into rcx (shift amount) - cl is the low 8 bits of rcx
        asm.mov(size=RegSize.R64, a=TEMP_REG, b=r_map[rb])
        # Load immediate into ra
        asm.mov_imm64(r_map[ra], vx)
        # Mask shift amount
        asm.and_(
            Operands.RegMem_Imm(reg_mem=RegMem.Reg(TEMP_REG), imm=ImmKind.I8(0x3F))
        )
        # Shift right logical by cl (using shr_cl method)
        asm.shr_cl(RegSize.R64, RegMem.Reg(r_map[ra]))

    def shar_r_imm_alt_64(self, asm, ra: int, rb: int, lx: int, vx_signed: int, vx: int):
        """ra = vx >> (rb % 64) arithmetic (alternate: immediate shifted by register)"""
        # Load rb into rcx (shift amount) - cl is the low 8 bits of rcx
        asm.mov(size=RegSize.R64, a=TEMP_REG, b=r_map[rb])
        # Load immediate into ra
        asm.mov_imm64(r_map[ra], vx)
        # Mask shift amount
        asm.and_(
            Operands.RegMem_Imm(reg_mem=RegMem.Reg(TEMP_REG), imm=ImmKind.I8(0x3F))
        )
        # Shift right arithmetic by cl (using sar_cl method)
        asm.sar_cl(RegSize.R64, RegMem.Reg(r_map[ra]))

    def rot_r_64_imm(self, asm, ra: int, rb: int, lx: int, vx_signed: int, vx: int):
        """ra = rotate_right(rb, vx) (64-bit)"""
        # Load rb into ra
        asm.mov(size=RegSize.R64, a=r_map[ra], b=r_map[rb])
        # Rotate right by immediate
        asm.ror_imm(RegSize.R64, RegMem.Reg(r_map[ra]), vx & 0x3F)

    def rot_r_64_imm_alt(self, asm, ra: int, rb: int, lx: int, vx_signed: int, vx: int):
        """ra = rotate_right(vx, rb) (alternate: immediate rotated by register)"""
        # Load rb into rcx (rotate amount) - cl is the low 8 bits of rcx
        asm.mov(size=RegSize.R64, a=TEMP_REG, b=r_map[rb])
        # Load immediate into ra
        asm.mov_imm64(r_map[ra], vx)
        # Mask the rotate amount
        asm.and_(
            Operands.RegMem_Imm(reg_mem=RegMem.Reg(TEMP_REG), imm=ImmKind.I8(0x3F))
        )
        # Rotate right by cl (using ror_cl method)
        asm.ror_cl(RegSize.R64, RegMem.Reg(r_map[ra]))

    def rot_r_32_imm(self, asm, ra: int, rb: int, lx: int, vx_signed: int, vx: int):
        """ra = rotate_right(rb, vx) (32-bit)"""
        # Load rb into ra (32-bit)
        asm.mov(size=RegSize.R32, a=r_map[ra], b=r_map[rb])
        # Rotate right by immediate
        asm.ror_imm(RegSize.R32, RegMem.Reg(r_map[ra]), vx & 0x1F)
        asm.movsxd_32_to_64(r_map[ra], r_map[ra])

    def rot_r_32_imm_alt(self, asm, ra: int, rb: int, lx: int, vx_signed: int, vx: int):
        """ra = rotate_right(vx, rb) (alternate: immediate rotated by register, 32-bit)"""
        # Load rb into rcx (rotate amount) - cl is the low 8 bits of rcx
        asm.mov(size=RegSize.R64, a=TEMP_REG, b=r_map[rb])
        # Load immediate into ra (32-bit)
        asm.mov_imm(RegMem.Reg(r_map[ra]), ImmKind.I32(vx & 0xFFFFFFFF))
        # Mask the rotate amount
        asm.and_(
            Operands.RegMem_Imm(reg_mem=RegMem.Reg(TEMP_REG), imm=ImmKind.I8(0x1F))
        )
        # Rotate right by cl (using ror_cl method)
        asm.ror_cl(RegSize.R32, RegMem.Reg(r_map[ra]))
