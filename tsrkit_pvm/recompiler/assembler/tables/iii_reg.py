from typing import Any, Callable, Dict, TYPE_CHECKING
from ....core.instruction_table import InstructionTable
from ....core.opcode import OpCode
from ....core.program_base import Program

if TYPE_CHECKING:
    from ...program import REC_Program

from ...vm_context import r_map, TEMP_REG
from tsrkit_asm import RegSize, RegMem, Operands, Reg, Condition, Size, ImmKind, MemOp


class InstructionsWArgs3Reg(InstructionTable):
    def __init__(self, counter: int, program: Program, skip_index: int) -> None:
        self.counter = counter
        self.program = program
        self.skip_index = skip_index


    def get_props(self):
        ra = min(12, self.program.zeta[self.counter + 1] % 16)
        rb = min(12, self.program.zeta[self.counter + 1] // 16)
        rd = min(12, self.program.zeta[self.counter + 2])
        return (ra, rb, rd)

    @classmethod
    def table(cls) -> Dict[int, OpCode]:
        return {
            190: OpCode(name="add_32", fn=cls.add_32, gas=1, is_terminating=False),
            191: OpCode(name="sub_32", fn=cls.sub_32, gas=1, is_terminating=False),
            192: OpCode(name="mul_32", fn=cls.mul_32, gas=1, is_terminating=False),
            193: OpCode(name="div_u_32", fn=cls.div_u_32, gas=1, is_terminating=False),
            194: OpCode(name="div_s_32", fn=cls.div_s_32, gas=1, is_terminating=False),
            195: OpCode(name="rem_u_32", fn=cls.rem_u_32, gas=1, is_terminating=False),
            196: OpCode(name="rem_s_32", fn=cls.rem_s_32, gas=1, is_terminating=False),
            197: OpCode(
                name="shlo_l_32", fn=cls.shlo_l_32, gas=1, is_terminating=False
            ),
            198: OpCode(
                name="shlo_r_32", fn=cls.shlo_r_32, gas=1, is_terminating=False
            ),
            199: OpCode(
                name="shar_r_32", fn=cls.shar_r_32, gas=1, is_terminating=False
            ),
            200: OpCode(name="add_64", fn=cls.add_64, gas=1, is_terminating=False),
            201: OpCode(name="sub_64", fn=cls.sub_64, gas=1, is_terminating=False),
            202: OpCode(name="mul_64", fn=cls.mul_64, gas=1, is_terminating=False),
            203: OpCode(name="div_u_64", fn=cls.div_u_64, gas=1, is_terminating=False),
            204: OpCode(name="div_s_64", fn=cls.div_s_64, gas=1, is_terminating=False),
            205: OpCode(name="rem_u_64", fn=cls.rem_u_64, gas=1, is_terminating=False),
            206: OpCode(name="rem_s_64", fn=cls.rem_s_64, gas=1, is_terminating=False),
            207: OpCode(
                name="shlo_l_64", fn=cls.shlo_l_64, gas=1, is_terminating=False
            ),
            208: OpCode(
                name="shlo_r_64", fn=cls.shlo_r_64, gas=1, is_terminating=False
            ),
            209: OpCode(
                name="shar_r_64", fn=cls.shar_r_64, gas=1, is_terminating=False
            ),
            210: OpCode(name="and", fn=cls.and_op, gas=1, is_terminating=False),
            211: OpCode(name="xor", fn=cls.xor_op, gas=1, is_terminating=False),
            212: OpCode(name="or", fn=cls.or_op, gas=1, is_terminating=False),
            213: OpCode(
                name="mul_upper_s_s", fn=cls.mul_upper_s_s, gas=1, is_terminating=False
            ),
            214: OpCode(
                name="mul_upper_u_u", fn=cls.mul_upper_u_u, gas=1, is_terminating=False
            ),
            215: OpCode(
                name="mul_upper_s_u", fn=cls.mul_upper_s_u, gas=1, is_terminating=False
            ),
            216: OpCode(name="set_lt_u", fn=cls.set_lt_u, gas=1, is_terminating=False),
            217: OpCode(name="set_lt_s", fn=cls.set_lt_s, gas=1, is_terminating=False),
            218: OpCode(name="cmov_iz", fn=cls.cmov_iz, gas=1, is_terminating=False),
            219: OpCode(name="cmov_nz", fn=cls.cmov_nz, gas=1, is_terminating=False),
            220: OpCode(name="rot_l_64", fn=cls.rot_l_64, gas=1, is_terminating=False),
            221: OpCode(name="rot_l_32", fn=cls.rot_l_32, gas=1, is_terminating=False),
            222: OpCode(name="rot_r_64", fn=cls.rot_r_64, gas=1, is_terminating=False),
            223: OpCode(name="rot_r_32", fn=cls.rot_r_32, gas=1, is_terminating=False),
            224: OpCode(name="and_inv", fn=cls.and_inv, gas=1, is_terminating=False),
            225: OpCode(name="or_inv", fn=cls.or_inv, gas=1, is_terminating=False),
            226: OpCode(name="xnor", fn=cls.xnor, gas=1, is_terminating=False),
            227: OpCode(name="max", fn=cls.max_op, gas=1, is_terminating=False),
            228: OpCode(name="max_u", fn=cls.max_u, gas=1, is_terminating=False),
            229: OpCode(name="min", fn=cls.min_op, gas=1, is_terminating=False),
            230: OpCode(name="min_u", fn=cls.min_u, gas=1, is_terminating=False),
        }

    def add_32(self, asm, ra: int, rb: int, rd: int):
        """rd = (ra + rb) % 2^32, then sign-extend to 64 bits"""
        if rd == rb:
            asm.add(
                Operands.RegMem_Reg(
                    size=Size.U32,
                    reg_mem=RegMem.Reg(r_map[rd]),
                    reg=r_map[ra],
                )
            )
        elif rd == ra:
            asm.add(
                Operands.RegMem_Reg(
                    size=Size.U32,
                    reg_mem=RegMem.Reg(r_map[rd]),
                    reg=r_map[rb],
                )
            )
        else:
            # Load ra into rd
            asm.mov(size=RegSize.R32, a=r_map[rd], b=r_map[ra])
            # Add rb to rd
            asm.add(
                Operands.RegMem_Reg(
                    size=Size.U32,
                    reg_mem=RegMem.Reg(r_map[rd]),
                    reg=r_map[rb],
                )
            )
        # Sign-extend 32-bit result to 64 bits (PVM requirement)
        asm.movsxd_32_to_64(r_map[rd], r_map[rd])

    def add_64(self, asm, ra: int, rb: int, rd: int):
        """rd = ra + rb (64-bit)"""
        if rd == rb:
            asm.add(
                Operands.RegMem_Reg(
                    size=Size.U64,
                    reg_mem=RegMem.Reg(r_map[rd]),
                    reg=r_map[ra],
                )
            )
        elif rd == ra:
            asm.add(
                Operands.RegMem_Reg(
                    size=Size.U64,
                    reg_mem=RegMem.Reg(r_map[rd]),
                    reg=r_map[rb],
                )
            )
        else:
            # Load ra into rd
            asm.mov(size=RegSize.R64, a=r_map[rd], b=r_map[ra])
            # Add rb to rd
            asm.add(
                Operands.RegMem_Reg(
                    size=Size.U64,
                    reg_mem=RegMem.Reg(r_map[rd]),
                    reg=r_map[rb],
                )
            )

    def sub_32(self, asm, ra: int, rb: int, rd: int):
        """rd = (ra - rb) % 2^32, then sign-extend to 64 bits"""
        if ra == rd:
            asm.sub(
                Operands.RegMem_Reg(
                    size=Size.U32,
                    reg_mem=RegMem.Reg(r_map[rd]),
                    reg=r_map[rb],
                )
            )
        elif rb == rd:
            asm.neg(Size.U32, RegMem.Reg(r_map[rd]))
            asm.add(
                Operands.RegMem_Reg(
                    Size.U32, RegMem.Reg(r_map[rd]), r_map[ra]
                )
            )
        else:
            # Load ra into rd
            asm.mov(size=RegSize.R32, a=r_map[rd], b=r_map[ra])
            # Subtract rb from rd
            asm.sub(
                Operands.RegMem_Reg(
                    size=Size.U32,
                    reg_mem=RegMem.Reg(r_map[rd]),
                    reg=r_map[rb],
                )
            )
        # Sign-extend 32-bit result to 64 bits (PVM requirement)
        asm.movsxd_32_to_64(r_map[rd], r_map[rd])

    def sub_64(self, asm, ra: int, rb: int, rd: int):
        """rd = ra - rb (64-bit)"""
        if ra == rd:
            asm.sub(
                Operands.RegMem_Reg(
                    size=Size.U64,
                    reg_mem=RegMem.Reg(r_map[rd]),
                    reg=r_map[rb],
                )
            )
        elif rb == rd:
            asm.neg(Size.U64, RegMem.Reg(r_map[rd]))
            asm.add(
                Operands.RegMem_Reg(
                    Size.U64, RegMem.Reg(r_map[rd]), r_map[ra]
                )
            )
        else:
            # Load ra into rd
            asm.mov(size=RegSize.R64, a=r_map[rd], b=r_map[ra])
            # Subtract rb from rd
            asm.sub(
                Operands.RegMem_Reg(
                    size=Size.U64,
                    reg_mem=RegMem.Reg(r_map[rd]),
                    reg=r_map[rb],
                )
            )

    def mul_32(self, asm, ra: int, rb: int, rd: int):
        """rd = (ra * rb) % 2^32"""
        if rd == rb:
            asm.imul(RegSize.R32, r_map[rd], RegMem.Reg(r_map[ra]))
        elif rd == ra:
            asm.imul(RegSize.R32, r_map[rd], RegMem.Reg(r_map[rb]))
        else:
            # Load ra into rd
            asm.mov(size=RegSize.R32, a=r_map[rd], b=r_map[ra])
            # Add rb to rd
            asm.imul(RegSize.R32, r_map[rd], RegMem.Reg(r_map[rb]))

    def mul_64(self, asm, ra: int, rb: int, rd: int):
        """rd = (ra * rb) % 2^64"""
        if rd == rb:
            asm.imul(RegSize.R64, r_map[rd], RegMem.Reg(r_map[ra]))
        elif rd == ra:
            asm.imul(RegSize.R64, r_map[rd], RegMem.Reg(r_map[rb]))
        else:
            # Load ra into rd
            asm.mov(size=RegSize.R64, a=r_map[rd], b=r_map[ra])
            # Add rb to rd
            asm.imul(RegSize.R64, r_map[rd], RegMem.Reg(r_map[rb]))

    def div_u_32(self, asm, ra: int, rb: int, rd: int):
        """rd = ra / rb (unsigned 32-bit), rd = 0xffffffff if rb == 0"""
        # Save rax and rdx since they're guest registers and division clobbers them
        asm.push(Reg.rax)
        asm.push(Reg.rdx)

        # Simple check for zero divisor
        asm.test(
            Operands.RegMem_Reg(
                size=Size.U32, reg_mem=RegMem.Reg(r_map[rb]), reg=r_map[rb]
            )
        )

        zero_label = asm.forward_declare_label()
        end_label = asm.forward_declare_label()

        asm.jcc_label32(Condition.Equal, zero_label)

        # Normal division: use direct div instruction
        asm.mov(size=RegSize.R32, a=Reg.rax, b=r_map[ra])  # Load dividend
        asm.xor_(
            Operands.RegMem_Reg(size=Size.U32, reg_mem=RegMem.Reg(Reg.rdx), reg=Reg.rdx)
        )  # Clear rdx
        asm.div(RegSize.R32, RegMem.Reg(r_map[rb]))  # Direct division
        asm.movsxd_32_to_64(r_map[rd], Reg.rax)  # Sign-extend result
        asm.jmp_label32(end_label)

        # Division by zero case
        asm.define_label(zero_label)
        asm.mov_imm64(r_map[rd], 0xFFFFFFFFFFFFFFFF)

        asm.define_label(end_label)
        # Restore rax and rdx
        asm.pop(Reg.rdx)
        asm.pop(Reg.rax)

    def div_s_32(self, asm, ra: int, rb: int, rd: int):
        """rd = ra / rb (signed 32-bit), rd = -1 if rb == 0"""
        # Save rax and rdx since they're guest registers and division clobbers them
        asm.push(Reg.rax)
        asm.push(Reg.rdx)

        # Declare all labels
        zero_label = asm.forward_declare_label()
        overflow_label = asm.forward_declare_label()
        normal_div_label = asm.forward_declare_label()
        end_label = asm.forward_declare_label()

        # Simple check for zero divisor
        asm.test(
            Operands.RegMem_Reg(
                size=Size.U32, reg_mem=RegMem.Reg(r_map[rb]), reg=r_map[rb]
            )
        )
        asm.jcc_label32(Condition.Equal, zero_label)

        # Check for signed overflow: INT32_MIN / -1
        # Compare ra with INT32_MIN (0x80000000)
        asm.cmp(
            Operands.RegMem_Imm(
                reg_mem=RegMem.Reg(r_map[ra]), imm=ImmKind.I32(0x80000000)
            )
        )
        asm.jcc_label32(Condition.NotEqual, normal_div_label)

        # ra == INT32_MIN, now check if rb == -1 (0xffffffff in 32-bit)
        asm.cmp(
            Operands.RegMem_Imm(
                reg_mem=RegMem.Reg(r_map[rb]), imm=ImmKind.I32(0xFFFFFFFF)
            )
        )
        asm.jcc_label32(Condition.Equal, overflow_label)

        # Normal division
        asm.define_label(normal_div_label)
        asm.mov(size=RegSize.R32, a=Reg.rax, b=r_map[ra])  # Load dividend
        asm.cdq()  # Sign extend eax to edx:eax
        asm.idiv(RegSize.R32, RegMem.Reg(r_map[rb]))  # Direct signed division
        asm.movsxd_32_to_64(r_map[rd], Reg.rax)  # Sign extend result to 64-bit
        asm.jmp_label32(end_label)

        # Overflow case: INT32_MIN / -1 = INT32_MIN (sign-extended to 64-bit)
        asm.define_label(overflow_label)
        asm.mov_imm64(r_map[rd], 0xFFFFFFFF80000000)  # INT32_MIN sign-extended
        asm.jmp_label32(end_label)

        # Division by zero case
        asm.define_label(zero_label)
        asm.mov_imm64(r_map[rd], 0xFFFFFFFFFFFFFFFF)  # -1

        asm.define_label(end_label)
        # Restore rax and rdx
        asm.pop(Reg.rdx)
        asm.pop(Reg.rax)

    def div_u_64(self, asm, ra: int, rb: int, rd: int):
        """rd = ra / rb (unsigned 64-bit), rd = -1 if rb == 0"""
        # Save rax and rdx since they're guest registers and division clobbers them
        asm.push(Reg.rax)
        asm.push(Reg.rdx)

        # Simple check for zero divisor
        asm.test(
            Operands.RegMem_Reg(
                size=Size.U64, reg_mem=RegMem.Reg(r_map[rb]), reg=r_map[rb]
            )
        )

        zero_label = asm.forward_declare_label()
        end_label = asm.forward_declare_label()

        asm.jcc_label32(Condition.Equal, zero_label)

        # Normal division: use direct div instruction
        asm.mov(size=RegSize.R64, a=Reg.rax, b=r_map[ra])  # Load dividend
        asm.xor_(
            Operands.RegMem_Reg(size=Size.U64, reg_mem=RegMem.Reg(Reg.rdx), reg=Reg.rdx)
        )  # Clear rdx
        asm.div(RegSize.R64, RegMem.Reg(r_map[rb]))  # Direct division
        asm.mov(size=RegSize.R64, a=r_map[rd], b=Reg.rax)  # Result
        asm.jmp_label32(end_label)

        # Division by zero case
        asm.define_label(zero_label)
        asm.mov_imm64(r_map[rd], 0xFFFFFFFFFFFFFFFF)

        asm.define_label(end_label)
        # Restore rax and rdx in reverse order
        asm.pop(Reg.rdx)
        asm.pop(Reg.rax)

    def div_s_64(self, asm, ra: int, rb: int, rd: int):
        """rd = ra / rb (signed 64-bit), rd = -1 if rb == 0"""
        # Save rax and rdx since they're guest registers and division clobbers them
        asm.push(Reg.rax)
        asm.push(Reg.rdx)

        # Declare all labels
        zero_label = asm.forward_declare_label()
        overflow_label = asm.forward_declare_label()
        normal_div_label = asm.forward_declare_label()
        end_label = asm.forward_declare_label()

        # Simple check for zero divisor
        asm.test(
            Operands.RegMem_Reg(
                size=Size.U64, reg_mem=RegMem.Reg(r_map[rb]), reg=r_map[rb]
            )
        )
        asm.jcc_label32(Condition.Equal, zero_label)

        # Check for signed overflow: INT64_MIN / -1
        # Compare ra with INT64_MIN (0x8000000000000000)
        asm.mov_imm64(TEMP_REG, 0x8000000000000000)
        asm.cmp(
            Operands.RegMem_Reg(
                size=Size.U64, reg_mem=RegMem.Reg(r_map[ra]), reg=TEMP_REG
            )
        )
        asm.jcc_label32(Condition.NotEqual, normal_div_label)

        # ra == INT64_MIN, now check if rb == -1
        asm.cmp(
            Operands.RegMem_Imm(reg_mem=RegMem.Reg(r_map[rb]), imm=ImmKind.I64(-1))
        )
        asm.jcc_label32(Condition.Equal, overflow_label)

        # Normal division
        asm.define_label(normal_div_label)
        asm.mov(size=RegSize.R64, a=Reg.rax, b=r_map[ra])  # Load dividend
        asm.cqo()  # Sign-extend rax into rdx:rax
        asm.idiv(RegSize.R64, RegMem.Reg(r_map[rb]))  # Direct signed division
        asm.mov(size=RegSize.R64, a=r_map[rd], b=Reg.rax)  # Result
        asm.jmp_label32(end_label)

        # Overflow case: INT64_MIN / -1 = INT64_MIN
        asm.define_label(overflow_label)
        asm.mov_imm64(r_map[rd], 0x8000000000000000)
        asm.jmp_label32(end_label)

        # Division by zero case
        asm.define_label(zero_label)
        asm.mov_imm64(r_map[rd], 0xFFFFFFFFFFFFFFFF)  # -1

        asm.define_label(end_label)
        # Restore rax and rdx in reverse order
        asm.pop(Reg.rdx)
        asm.pop(Reg.rax)

    def rem_u_32(self, asm, ra: int, rb: int, rd: int):
        """rd = ra % rb (unsigned 32-bit), rd = ra if rb == 0"""
        # Save rax and rdx since they\'re guest registers and division clobbers them
        asm.push(Reg.rax)
        asm.push(Reg.rdx)

        # Simple check for zero divisor - use 32-bit test for unsigned operation
        asm.test(
            Operands.RegMem_Reg(
                size=Size.U32, reg_mem=RegMem.Reg(r_map[rb]), reg=r_map[rb]
            )
        )

        zero_label = asm.forward_declare_label()
        end_label = asm.forward_declare_label()

        asm.jcc_label32(Condition.Equal, zero_label)

        # Normal remainder: use direct div instruction
        # For unsigned 32-bit remainder, we need to treat inputs as 32-bit unsigned values
        asm.mov(
            size=RegSize.R32, a=Reg.rax, b=r_map[ra]
        )  # Load dividend (auto-zeros upper 32 bits)
        asm.xor_(
            Operands.RegMem_Reg(size=Size.U32, reg_mem=RegMem.Reg(Reg.rdx), reg=Reg.rdx)
        )  # Clear rdx for 64-bit dividend rdx:rax

        # Ensure divisor is treated as 32-bit unsigned by using a temp register
        asm.mov(
            size=RegSize.R32, a=TEMP_REG, b=r_map[rb]
        )  # Load divisor as 32-bit (auto-zeros upper 32 bits)
        asm.div(
            RegSize.R32, RegMem.Reg(TEMP_REG)
        )  # Direct division (32-bit) using temp register
        asm.mov(
            size=RegSize.R32, a=r_map[rd], b=Reg.rdx
        )  # Remainder in rdx, auto-zeros upper 32 bits
        asm.movsxd_32_to_64(r_map[rd], r_map[rd])
        asm.jmp_label32(end_label)

        # Division by zero case - return dividend (sign-extended from 32-bit)
        asm.define_label(zero_label)
        asm.movsxd_32_to_64(r_map[rd], r_map[ra])

        asm.define_label(end_label)
        # Restore rax and rdx in reverse order
        asm.pop(Reg.rdx)
        asm.pop(Reg.rax)

    def rem_s_32(self, asm, ra: int, rb: int, rd: int):
        """rd = ra % rb (signed 32-bit), rd = ra if rb == 0"""
        # Save rax and rdx since they're guest registers and division clobbers them
        asm.push(Reg.rax)
        asm.push(Reg.rdx)

        # Simple check for zero divisor
        asm.test(
            Operands.RegMem_Reg(
                size=Size.U64, reg_mem=RegMem.Reg(r_map[rb]), reg=r_map[rb]
            )
        )

        # Declare all labels
        zero_label = asm.forward_declare_label()
        overflow_label = asm.forward_declare_label()
        normal_label = asm.forward_declare_label()
        end_label = asm.forward_declare_label()

        asm.jcc_label32(Condition.Equal, zero_label)

        # Check for overflow case: INT32_MIN % -1
        asm.cmp(
            Operands.RegMem_Imm(
                reg_mem=RegMem.Reg(r_map[ra]), imm=ImmKind.I32(0x80000000)
            )
        )
        asm.jcc_label32(
            Condition.NotEqual, normal_label
        )  # Skip overflow check if not INT32_MIN

        asm.cmp(
            Operands.RegMem_Imm(
                reg_mem=RegMem.Reg(r_map[rb]), imm=ImmKind.I32(0xFFFFFFFF)
            )
        )
        asm.jcc_label32(Condition.Equal, overflow_label)

        asm.define_label(normal_label)
        # Normal remainder: use direct idiv instruction
        asm.mov(size=RegSize.R32, a=Reg.rax, b=r_map[ra])  # Load dividend
        asm.cdq()  # Sign-extend eax into edx:eax
        asm.idiv(RegSize.R32, RegMem.Reg(r_map[rb]))  # Direct signed division
        asm.movsxd_32_to_64(
            r_map[rd], Reg.rdx
        )  # Remainder in rdx, sign-extend to 64-bit
        asm.jmp_label32(end_label)

        # Overflow case: INT32_MIN % -1 = 0
        asm.define_label(overflow_label)
        asm.mov_imm64(r_map[rd], 0)
        asm.jmp_label32(end_label)

        # Division by zero case - return dividend (sign-extended)
        asm.define_label(zero_label)
        asm.movsxd_32_to_64(r_map[rd], r_map[ra])

        asm.define_label(end_label)
        # Restore rax and rdx in reverse order
        asm.pop(Reg.rdx)
        asm.pop(Reg.rax)

    def rem_u_64(self, asm, ra: int, rb: int, rd: int):
        """rd = ra % rb (unsigned 64-bit), rd = ra if rb == 0"""
        # Save rax and rdx since they\'re guest registers and division clobbers them
        asm.push(Reg.rax)
        asm.push(Reg.rdx)

        # Simple check for zero divisor
        asm.test(
            Operands.RegMem_Reg(
                size=Size.U64, reg_mem=RegMem.Reg(r_map[rb]), reg=r_map[rb]
            )
        )

        zero_label = asm.forward_declare_label()
        end_label = asm.forward_declare_label()

        asm.jcc_label32(Condition.Equal, zero_label)

        # Normal remainder: use direct div instruction
        asm.mov(size=RegSize.R64, a=Reg.rax, b=r_map[ra])  # Load dividend
        asm.xor_(
            Operands.RegMem_Reg(size=Size.U64, reg_mem=RegMem.Reg(Reg.rdx), reg=Reg.rdx)
        )  # Clear rdx
        asm.div(RegSize.R64, RegMem.Reg(r_map[rb]))  # Direct division
        asm.mov(size=RegSize.R64, a=r_map[rd], b=Reg.rdx)  # Remainder in rdx
        asm.jmp_label32(end_label)

        # Division by zero case - return dividend
        asm.define_label(zero_label)
        asm.mov(size=RegSize.R64, a=r_map[rd], b=r_map[ra])

        asm.define_label(end_label)
        # Restore rax and rdx in reverse order
        asm.pop(Reg.rdx)
        asm.pop(Reg.rax)

    def rem_s_64(self, asm, ra: int, rb: int, rd: int):
        """rd = ra % rb (signed 64-bit), rd = ra if rb == 0"""
        # Save rax and rdx since they're guest registers and division clobbers them
        asm.push(Reg.rax)
        asm.push(Reg.rdx)

        # Simple check for zero divisor
        asm.test(
            Operands.RegMem_Reg(
                size=Size.U64, reg_mem=RegMem.Reg(r_map[rb]), reg=r_map[rb]
            )
        )

        # Declare all labels
        zero_label = asm.forward_declare_label()
        overflow_label = asm.forward_declare_label()
        normal_label = asm.forward_declare_label()
        end_label = asm.forward_declare_label()

        asm.jcc_label32(Condition.Equal, zero_label)

        # Check for overflow case: INT64_MIN % -1
        asm.mov_imm64(TEMP_REG, 0x8000000000000000)  # INT64_MIN
        asm.cmp(
            Operands.RegMem_Reg(
                size=Size.U64, reg_mem=RegMem.Reg(r_map[ra]), reg=TEMP_REG
            )
        )
        asm.jcc_label32(
            Condition.NotEqual, normal_label
        )  # Skip overflow check if not INT64_MIN

        asm.cmp(
            Operands.RegMem_Imm(reg_mem=RegMem.Reg(r_map[rb]), imm=ImmKind.I64(-1))
        )
        asm.jcc_label32(Condition.Equal, overflow_label)

        asm.define_label(normal_label)
        # Normal remainder: use direct idiv instruction
        asm.mov(size=RegSize.R64, a=Reg.rax, b=r_map[ra])  # Load dividend
        asm.cqo()  # Sign-extend rax into rdx:rax
        asm.idiv(RegSize.R64, RegMem.Reg(r_map[rb]))  # Direct signed division
        asm.mov(size=RegSize.R64, a=r_map[rd], b=Reg.rdx)  # Remainder in rdx
        asm.jmp_label32(end_label)

        # Overflow case: INT64_MIN % -1 = 0
        asm.define_label(overflow_label)
        asm.mov_imm64(r_map[rd], 0)
        asm.jmp_label32(end_label)

        # Division by zero case - return dividend
        asm.define_label(zero_label)
        asm.mov(size=RegSize.R64, a=r_map[rd], b=r_map[ra])

        asm.define_label(end_label)
        # Restore rax and rdx in reverse order
        asm.pop(Reg.rdx)
        asm.pop(Reg.rax)

    def shlo_l_32(self, asm, ra: int, rb: int, rd: int):
        """rd = (ra << (rb % 32)) % 2^32"""
        # Handle register aliasing - save rb if it will be overwritten
        if rb == rd and rb != ra:
            # rb will be overwritten, save shift amount first
            asm.mov(size=RegSize.R64, a=TEMP_REG, b=r_map[rb])
            asm.mov(size=RegSize.R32, a=r_map[rd], b=r_map[ra])
        else:
            # Normal case: load ra into rd, then rb into rcx
            asm.mov(size=RegSize.R32, a=r_map[rd], b=r_map[ra])
            asm.mov(size=RegSize.R64, a=TEMP_REG, b=r_map[rb])
        # Mask shift amount
        asm.and_(
            Operands.RegMem_Imm(reg_mem=RegMem.Reg(TEMP_REG), imm=ImmKind.I8(0x1F))
        )
        # Shift left by cl
        asm.shl_cl(RegSize.R32, RegMem.Reg(r_map[rd]))
        # Sign-extend 32-bit result to 64 bits (PVM requirement)
        asm.movsxd_32_to_64(r_map[rd], r_map[rd])

    def shlo_l_64(self, asm, ra: int, rb: int, rd: int):
        """rd = ra << (rb % 64)"""
        # Handle register aliasing - save rb if it will be overwritten
        if rb == rd and rb != ra:
            # rb will be overwritten, save shift amount first
            asm.mov(size=RegSize.R64, a=TEMP_REG, b=r_map[rb])
            asm.mov(size=RegSize.R64, a=r_map[rd], b=r_map[ra])
        else:
            # Normal case: load ra into rd, then rb into rcx
            asm.mov(size=RegSize.R64, a=r_map[rd], b=r_map[ra])
            asm.mov(size=RegSize.R64, a=TEMP_REG, b=r_map[rb])
        # Mask shift amount
        asm.and_(
            Operands.RegMem_Imm(reg_mem=RegMem.Reg(TEMP_REG), imm=ImmKind.I8(0x3F))
        )
        # Shift left by cl
        asm.shl_cl(RegSize.R64, RegMem.Reg(r_map[rd]))

    def shlo_r_32(self, asm, ra: int, rb: int, rd: int):
        """rd = ra >> (rb % 32) (logical right shift)"""
        # Handle register aliasing - save rb if it will be overwritten
        if rb == rd and rb != ra:
            # rb will be overwritten, save shift amount first
            asm.mov(size=RegSize.R64, a=TEMP_REG, b=r_map[rb])
            asm.mov(size=RegSize.R32, a=r_map[rd], b=r_map[ra])
        else:
            # Normal case: load ra into rd, then rb into rcx
            asm.mov(size=RegSize.R32, a=r_map[rd], b=r_map[ra])
            asm.mov(size=RegSize.R64, a=TEMP_REG, b=r_map[rb])
        asm.and_(
            Operands.RegMem_Imm(reg_mem=RegMem.Reg(TEMP_REG), imm=ImmKind.I8(0x1F))
        )
        asm.shr_cl(RegSize.R32, RegMem.Reg(r_map[rd]))
        # Sign-extend 32-bit result to 64 bits (PVM requirement)
        asm.movsxd_32_to_64(r_map[rd], r_map[rd])

    def shlo_r_64(self, asm, ra: int, rb: int, rd: int):
        """rd = ra >> (rb % 64) (logical right shift)"""
        # Handle register aliasing - save rb if it will be overwritten
        if rb == rd and rb != ra:
            # rb will be overwritten, save shift amount first
            asm.mov(size=RegSize.R64, a=TEMP_REG, b=r_map[rb])
            asm.mov(size=RegSize.R64, a=r_map[rd], b=r_map[ra])
        else:
            # Normal case: load ra into rd, then rb into rcx
            asm.mov(size=RegSize.R64, a=r_map[rd], b=r_map[ra])
            asm.mov(size=RegSize.R64, a=TEMP_REG, b=r_map[rb])
        asm.and_(
            Operands.RegMem_Imm(reg_mem=RegMem.Reg(TEMP_REG), imm=ImmKind.I8(0x3F))
        )
        asm.shr_cl(RegSize.R64, RegMem.Reg(r_map[rd]))

    def shar_r_32(self, asm, ra: int, rb: int, rd: int):
        """rd = ra >> (rb % 32) (arithmetic right shift)"""
        # Handle register aliasing - save rb if it will be overwritten
        if rb == rd and rb != ra:
            # rb will be overwritten, save shift amount first
            asm.mov(size=RegSize.R64, a=TEMP_REG, b=r_map[rb])
            asm.mov(size=RegSize.R32, a=r_map[rd], b=r_map[ra])
        else:
            # Normal case: load ra into rd, then rb into rcx
            asm.mov(size=RegSize.R32, a=r_map[rd], b=r_map[ra])
            asm.mov(size=RegSize.R64, a=TEMP_REG, b=r_map[rb])
        asm.and_(
            Operands.RegMem_Imm(reg_mem=RegMem.Reg(TEMP_REG), imm=ImmKind.I8(0x1F))
        )
        asm.sar_cl(RegSize.R32, RegMem.Reg(r_map[rd]))
        # Sign-extend 32-bit result to 64 bits (PVM requirement)
        asm.movsxd_32_to_64(r_map[rd], r_map[rd])

    def shar_r_64(self, asm, ra: int, rb: int, rd: int):
        """rd = ra >> (rb % 64) (arithmetic right shift)"""
        # Handle register aliasing - save rb if it will be overwritten
        if rb == rd and rb != ra:
            # rb will be overwritten, save shift amount first
            asm.mov(size=RegSize.R64, a=TEMP_REG, b=r_map[rb])
            asm.mov(size=RegSize.R64, a=r_map[rd], b=r_map[ra])
        else:
            # Normal case: load ra into rd, then rb into rcx
            asm.mov(size=RegSize.R64, a=r_map[rd], b=r_map[ra])
            asm.mov(size=RegSize.R64, a=TEMP_REG, b=r_map[rb])
        asm.and_(
            Operands.RegMem_Imm(reg_mem=RegMem.Reg(TEMP_REG), imm=ImmKind.I8(0x3F))
        )
        asm.sar_cl(RegSize.R64, RegMem.Reg(r_map[rd]))

    def and_op(self, asm, ra: int, rb: int, rd: int):
        """rd = ra & rb (bitwise AND)"""
        if rd == rb:
            asm.and_(
                Operands.RegMem_Reg(
                    size=Size.U64,
                    reg_mem=RegMem.Reg(r_map[rd]),
                    reg=r_map[ra],
                )
            )
        elif rd == ra:
            asm.and_(
                Operands.RegMem_Reg(
                    size=Size.U64,
                    reg_mem=RegMem.Reg(r_map[rd]),
                    reg=r_map[rb],
                )
            )
        else:
            asm.mov(size=RegSize.R64, a=r_map[rd], b=r_map[ra])
            asm.and_(
                Operands.RegMem_Reg(
                    size=Size.U64,
                    reg_mem=RegMem.Reg(r_map[rd]),
                    reg=r_map[rb],
                )
            )

    def xor_op(self, asm, ra: int, rb: int, rd: int):
        """rd = ra ^ rb (bitwise XOR)"""
        if rd == rb:
            asm.xor_(
                Operands.RegMem_Reg(
                    size=Size.U64,
                    reg_mem=RegMem.Reg(r_map[rd]),
                    reg=r_map[ra],
                )
            )
        elif rd == ra:
            asm.xor_(
                Operands.RegMem_Reg(
                    size=Size.U64,
                    reg_mem=RegMem.Reg(r_map[rd]),
                    reg=r_map[rb],
                )
            )
        else:
            asm.mov(size=RegSize.R64, a=r_map[rd], b=r_map[ra])
            asm.xor_(
                Operands.RegMem_Reg(
                    size=Size.U64,
                    reg_mem=RegMem.Reg(r_map[rd]),
                    reg=r_map[rb],
                )
            )

    def or_op(self, asm, ra: int, rb: int, rd: int):
        """rd = ra | rb (bitwise OR)"""
        if rd == rb:
            asm.or_(
                Operands.RegMem_Reg(
                    size=Size.U64,
                    reg_mem=RegMem.Reg(r_map[rd]),
                    reg=r_map[ra],
                )
            )
        elif rd == ra:
            asm.or_(
                Operands.RegMem_Reg(
                    size=Size.U64,
                    reg_mem=RegMem.Reg(r_map[rd]),
                    reg=r_map[rb],
                )
            )
        else:
            asm.mov(size=RegSize.R64, a=r_map[rd], b=r_map[ra])
            asm.or_(
                Operands.RegMem_Reg(
                    size=Size.U64,
                    reg_mem=RegMem.Reg(r_map[rd]),
                    reg=r_map[rb],
                )
            )

    def mul_upper_s_s(self, asm, ra: int, rb: int, rd: int):
        """rd = (ra * rb) >> 64 (signed multiplication, upper 64 bits)"""
        asm.push(Reg.rax)
        asm.push(Reg.rdx)

        asm.mov(size=RegSize.R64, a=TEMP_REG, b=r_map[ra])
        asm.mov(size=RegSize.R64, a=Reg.rax, b=r_map[rb])
        asm.imul_dx_ax(RegSize.R64, RegMem.Reg(TEMP_REG))

        if rd == 1:  # rd is rax
            asm.mov(size=RegSize.R64, a=Reg.rax, b=Reg.rdx)
            asm.pop(Reg.rdx)
            asm.add_imm8(Reg.rsp, 8)  # discard original rax
        elif rd == 4:  # rd is rdx
            asm.pop(Reg.rax)
            asm.add_imm8(Reg.rsp, 8)  # discard original rdx
        else:
            if rd != 0:
                asm.mov(size=RegSize.R64, a=r_map[rd], b=Reg.rdx)
            asm.pop(Reg.rdx)
            asm.pop(Reg.rax)

    def mul_upper_u_u(self, asm, ra: int, rb: int, rd: int):
        """rd = (ra * rb) >> 64 (unsigned multiplication, upper 64 bits)"""
        asm.push(Reg.rax)
        asm.push(Reg.rdx)

        asm.mov(size=RegSize.R64, a=TEMP_REG, b=r_map[ra])
        asm.mov(size=RegSize.R64, a=Reg.rax, b=r_map[rb])
        asm.mul_dx_ax(RegSize.R64, RegMem.Reg(TEMP_REG))

        if rd == 1:  # rd is rax
            asm.mov(size=RegSize.R64, a=Reg.rax, b=Reg.rdx)
            asm.pop(Reg.rdx)
            asm.add_imm8(Reg.rsp, 8)  # discard original rax
        elif rd == 4:  # rd is rdx
            asm.pop(Reg.rax)
            asm.add_imm8(Reg.rsp, 8)  # discard original rdx
        else:
            if rd != 0:
                asm.mov(size=RegSize.R64, a=r_map[rd], b=Reg.rdx)
            asm.pop(Reg.rdx)
            asm.pop(Reg.rax)

    def mul_upper_s_u(self, asm, ra: int, rb: int, rd: int):
        """rd = (ra_signed * rb_unsigned) >> 64 (mixed multiplication, upper 64 bits)"""
        # This implements floor(signed(ra) * unsigned(rb) / 2**64).
        # For ra < 0, this is equivalent to -ceil(|ra| * rb / 2**64).
        # We calculate ceil(N/D) as (hi + (lo != 0)).

        # Save registers that are clobbered by this logic.
        # We use rax, rdx for multiplication, and rcx as a temporary.
        asm.push(Reg.rax)
        asm.push(Reg.rdx)
        asm.push(TEMP_REG)

        # Load operands: ra (signed) into rcx, rb (unsigned) into rax.
        asm.mov(size=RegSize.R64, a=TEMP_REG, b=r_map[ra])
        asm.mov(size=RegSize.R64, a=Reg.rax, b=r_map[rb])

        label_pos = asm.forward_declare_label()
        label_end = asm.forward_declare_label()

        # Test if ra (in rcx) is negative
        asm.test(
            Operands.RegMem_Reg(
                size=Size.U64, reg_mem=RegMem.Reg(TEMP_REG), reg=TEMP_REG
            )
        )
        asm.jcc_label32(Condition.NotSign, label_pos)

        # --- Negative case: ra < 0 ---
        asm.neg(Size.U64, RegMem.Reg(TEMP_REG))  # rcx = |ra|
        asm.mul_dx_ax(RegSize.R64, RegMem.Reg(TEMP_REG))  # RDX:RAX = |ra| * rb

        # Now, calculate -(hi + carry). Result should end up in rdx.
        # hi is in rdx, lo is in rax. We reuse rcx for the carry.
        asm.mov_imm64(TEMP_REG, 0)
        asm.test(
            Operands.RegMem_Reg(size=Size.U64, reg_mem=RegMem.Reg(Reg.rax), reg=Reg.rax)
        )
        asm.setcc(Condition.NotEqual, RegMem.Reg(TEMP_REG))  # rcx = (rax != 0) ? 1 : 0
        asm.add(
            Operands.RegMem_Reg(
                size=Size.U64, reg_mem=RegMem.Reg(Reg.rdx), reg=TEMP_REG
            )
        )  # rdx = hi + carry
        asm.neg(Size.U64, RegMem.Reg(Reg.rdx))  # rdx = -(hi + carry)
        asm.jmp_label32(label_end)

        # --- Positive case: ra >= 0 ---
        asm.define_label(label_pos)
        asm.mul_dx_ax(RegSize.R64, RegMem.Reg(TEMP_REG))  # RDX:RAX = ra * rb
        # result is in rdx (high part)

        asm.define_label(label_end)

        # The final result is in RDX.
        # Now, move it to the destination register `rd` and restore clobbered registers.
        # The stack contains: [original rcx], [original rdx], [original rax]
        if rd == 1:  # rd is rax
            asm.mov(size=RegSize.R64, a=Reg.rax, b=Reg.rdx)  # Move result to rax
            asm.pop(TEMP_REG)
            asm.pop(Reg.rdx)
            asm.add_imm8(Reg.rsp, 8)  # Discard original rax from stack
        elif rd == 2:  # rd is rcx
            asm.mov(size=RegSize.R64, a=TEMP_REG, b=Reg.rdx)  # Move result to rcx
            asm.add_imm8(Reg.rsp, 8)  # Discard original rcx from stack
            asm.pop(Reg.rdx)
            asm.pop(Reg.rax)
        elif rd == 4:  # rd is rdx
            # Result is already in rdx.
            asm.pop(TEMP_REG)
            asm.add_imm8(Reg.rsp, 8)  # Discard original rdx from stack
            asm.pop(Reg.rax)
        else:
            # No aliasing with rax, rdx, rcx.
            if rd != 0:
                asm.mov(size=RegSize.R64, a=r_map[rd], b=Reg.rdx)
            asm.pop(TEMP_REG)
            asm.pop(Reg.rdx)
            asm.pop(Reg.rax)

    def set_lt_u(self, asm, ra: int, rb: int, rd: int):
        """rd = (ra < rb) ? 1 : 0 (unsigned comparison)"""
        if rd == 0:
            return
        # Compare ra with rb
        asm.cmp(
            Operands.RegMem_Reg(
                size=Size.U64, reg_mem=RegMem.Reg(r_map[ra]), reg=r_map[rb]
            )
        )
        # Clear rd register first (setcc only sets the low 8 bits)
        asm.mov_imm64(r_map[rd], 0)
        # Set byte if below (unsigned less than)
        asm.setcc(Condition.Below, RegMem.Reg(r_map[rd]))

    def set_lt_s(self, asm, ra: int, rb: int, rd: int):
        """rd = (ra < rb) ? 1 : 0 (signed comparison)"""
        # Compare ra with rb
        asm.cmp(
            Operands.RegMem_Reg(
                size=Size.U64, reg_mem=RegMem.Reg(r_map[ra]), reg=r_map[rb]
            )
        )
        # Clear rd register first (setcc only sets the low 8 bits)
        asm.mov_imm64(r_map[rd], 0)
        # Set byte if less (signed less than)
        asm.setcc(Condition.Less, RegMem.Reg(r_map[rd]))

    def cmov_iz(self, asm, ra: int, rb: int, rd: int):
        """rd = (rb == 0) ? ra : rd (conditional move if zero)"""
        # Test if rb is zero
        asm.test(
            Operands.RegMem_Reg(
                size=Size.U64, reg_mem=RegMem.Reg(r_map[rb]), reg=r_map[rb]
            )
        )
        # Conditional move if zero
        asm.cmov(
            Condition.Equal, RegSize.R64, r_map[rd], RegMem.Reg(r_map[ra])
        )

    def cmov_nz(self, asm, ra: int, rb: int, rd: int):
        """rd = (rb != 0) ? ra : rd (conditional move if not zero)"""
        # Test if rb is zero
        asm.test(
            Operands.RegMem_Reg(
                size=Size.U64, reg_mem=RegMem.Reg(r_map[rb]), reg=r_map[rb]
            )
        )
        # Conditional move if not zero
        asm.cmov(
            Condition.NotEqual, RegSize.R64, r_map[rd], RegMem.Reg(r_map[ra])
        )

    def rot_l_64(self, asm, ra: int, rb: int, rd: int):
        """rd = rotate_left(ra, rb) (64-bit)"""
        # Handle register aliasing - save rb if it will be overwritten
        if rb == rd and rb != ra:
            # rb will be overwritten, save rotate amount first
            asm.mov(size=RegSize.R64, a=TEMP_REG, b=r_map[rb])
            asm.mov(size=RegSize.R64, a=r_map[rd], b=r_map[ra])
        else:
            # Normal case: load ra into rd, then rb into rcx
            asm.mov(size=RegSize.R64, a=r_map[rd], b=r_map[ra])
            asm.mov(size=RegSize.R64, a=TEMP_REG, b=r_map[rb])
        # Mask the rotate amount
        asm.and_(
            Operands.RegMem_Imm(reg_mem=RegMem.Reg(TEMP_REG), imm=ImmKind.I8(0x3F))
        )
        # Rotate left by cl
        asm.rol_cl(RegSize.R64, RegMem.Reg(r_map[rd]))

    def rot_l_32(self, asm, ra: int, rb: int, rd: int):
        """rd = rotate_left(ra, rb) (32-bit)"""
        # Handle register aliasing - save rb if it will be overwritten
        if rb == rd and rb != ra:
            # rb will be overwritten, save rotate amount first
            asm.mov(size=RegSize.R64, a=TEMP_REG, b=r_map[rb])
            asm.mov(size=RegSize.R32, a=r_map[rd], b=r_map[ra])
        else:
            # Normal case: load ra into rd, then rb into rcx
            asm.mov(size=RegSize.R32, a=r_map[rd], b=r_map[ra])
            asm.mov(size=RegSize.R64, a=TEMP_REG, b=r_map[rb])
        # Mask the rotate amount
        asm.and_(
            Operands.RegMem_Imm(reg_mem=RegMem.Reg(TEMP_REG), imm=ImmKind.I8(0x1F))
        )
        # Rotate left by cl
        asm.rol_cl(RegSize.R32, RegMem.Reg(r_map[rd]))
        # Sign-extend 32-bit result to 64 bits (PVM requirement)
        asm.movsxd_32_to_64(r_map[rd], r_map[rd])

    def rot_r_64(self, asm, ra: int, rb: int, rd: int):
        """rd = rotate_right(ra, rb) (64-bit)"""
        # Handle register aliasing - save rb if it will be overwritten
        if rb == rd and rb != ra:
            # rb will be overwritten, save rotate amount first
            asm.mov(size=RegSize.R64, a=TEMP_REG, b=r_map[rb])
            asm.mov(size=RegSize.R64, a=r_map[rd], b=r_map[ra])
        else:
            # Normal case: load ra into rd, then rb into rcx
            asm.mov(size=RegSize.R64, a=r_map[rd], b=r_map[ra])
            asm.mov(size=RegSize.R64, a=TEMP_REG, b=r_map[rb])
        # Mask the rotate amount
        asm.and_(
            Operands.RegMem_Imm(reg_mem=RegMem.Reg(TEMP_REG), imm=ImmKind.I8(0x3F))
        )
        # Rotate right by cl
        asm.ror_cl(RegSize.R64, RegMem.Reg(r_map[rd]))

    def rot_r_32(self, asm, ra: int, rb: int, rd: int):
        """rd = rotate_right(ra, rb) (32-bit)"""
        # Handle register aliasing - save rb if it will be overwritten
        if rb == rd and rb != ra:
            # rb will be overwritten, save rotate amount first
            asm.mov(size=RegSize.R64, a=TEMP_REG, b=r_map[rb])
            asm.mov(size=RegSize.R32, a=r_map[rd], b=r_map[ra])
        else:
            # Normal case: load ra into rd, then rb into rcx
            asm.mov(size=RegSize.R32, a=r_map[rd], b=r_map[ra])
            asm.mov(size=RegSize.R64, a=TEMP_REG, b=r_map[rb])
        # Mask the rotate amount
        asm.and_(
            Operands.RegMem_Imm(reg_mem=RegMem.Reg(TEMP_REG), imm=ImmKind.I8(0x1F))
        )
        # Rotate right by cl
        asm.ror_cl(RegSize.R32, RegMem.Reg(r_map[rd]))
        # Sign-extend 32-bit result to 64 bits (PVM requirement)
        asm.movsxd_32_to_64(r_map[rd], r_map[rd])

    def and_inv(self, asm, ra: int, rb: int, rd: int):
        """rd = ra & (~rb) (AND with inverted second operand)"""
        # Handle register aliasing - need to be careful with rcx usage
        if rb == rd and rb != ra:
            # rb will be overwritten, save and invert rb first
            asm.mov(size=RegSize.R64, a=TEMP_REG, b=r_map[rb])
            asm.not_(Size.U64, RegMem.Reg(TEMP_REG))
            asm.mov(size=RegSize.R64, a=r_map[rd], b=r_map[ra])
            asm.and_(
                Operands.RegMem_Reg(
                    size=Size.U64, reg_mem=RegMem.Reg(r_map[rd]), reg=TEMP_REG
                )
            )
        elif ra == rd:
            # ra is already in rd, just invert rb and AND
            asm.mov(size=RegSize.R64, a=TEMP_REG, b=r_map[rb])
            asm.not_(Size.U64, RegMem.Reg(TEMP_REG))
            asm.and_(
                Operands.RegMem_Reg(
                    size=Size.U64, reg_mem=RegMem.Reg(r_map[rd]), reg=TEMP_REG
                )
            )
        else:
            # Normal case: load ra into rd, invert rb in temp, then AND
            asm.mov(size=RegSize.R64, a=r_map[rd], b=r_map[ra])
            asm.mov(size=RegSize.R64, a=TEMP_REG, b=r_map[rb])
            asm.not_(Size.U64, RegMem.Reg(TEMP_REG))
            asm.and_(
                Operands.RegMem_Reg(
                    size=Size.U64, reg_mem=RegMem.Reg(r_map[rd]), reg=TEMP_REG
                )
            )

    def or_inv(self, asm, ra: int, rb: int, rd: int):
        """rd = ra | (~rb) (OR with inverted second operand)"""
        # Handle register aliasing - need to be careful with rcx usage
        if rb == rd and rb != ra:
            # rb will be overwritten, save and invert rb first
            asm.mov(size=RegSize.R64, a=TEMP_REG, b=r_map[rb])
            asm.not_(Size.U64, RegMem.Reg(TEMP_REG))
            asm.mov(size=RegSize.R64, a=r_map[rd], b=r_map[ra])
            asm.or_(
                Operands.RegMem_Reg(
                    size=Size.U64, reg_mem=RegMem.Reg(r_map[rd]), reg=TEMP_REG
                )
            )
        elif ra == rd:
            # ra is already in rd, just invert rb and OR
            asm.mov(size=RegSize.R64, a=TEMP_REG, b=r_map[rb])
            asm.not_(Size.U64, RegMem.Reg(TEMP_REG))
            asm.or_(
                Operands.RegMem_Reg(
                    size=Size.U64, reg_mem=RegMem.Reg(r_map[rd]), reg=TEMP_REG
                )
            )
        else:
            # Normal case: load ra into rd, invert rb in temp, then OR
            asm.mov(size=RegSize.R64, a=r_map[rd], b=r_map[ra])
            asm.mov(size=RegSize.R64, a=TEMP_REG, b=r_map[rb])
            asm.not_(Size.U64, RegMem.Reg(TEMP_REG))
            asm.or_(
                Operands.RegMem_Reg(
                    size=Size.U64, reg_mem=RegMem.Reg(r_map[rd]), reg=TEMP_REG
                )
            )

    def xnor(self, asm, ra: int, rb: int, rd: int):
        """rd = ~(ra ^ rb) (XOR then invert result)"""
        # Handle register aliasing for XOR operation
        if rd == rb:
            asm.xor_(
                Operands.RegMem_Reg(
                    size=Size.U64,
                    reg_mem=RegMem.Reg(r_map[rd]),
                    reg=r_map[ra],
                )
            )
        elif rd == ra:
            asm.xor_(
                Operands.RegMem_Reg(
                    size=Size.U64,
                    reg_mem=RegMem.Reg(r_map[rd]),
                    reg=r_map[rb],
                )
            )
        else:
            # Load ra into rd
            asm.mov(size=RegSize.R64, a=r_map[rd], b=r_map[ra])
            # XOR with rb
            asm.xor_(
                Operands.RegMem_Reg(
                    size=Size.U64,
                    reg_mem=RegMem.Reg(r_map[rd]),
                    reg=r_map[rb],
                )
            )
        # Invert result
        asm.not_(Size.U64, RegMem.Reg(r_map[rd]))

    def max_op(self, asm, ra: int, rb: int, rd: int):
        """rd = max(ra, rb) (signed comparison)"""
        # Handle register aliasing by saving values if needed
        if rb == rd and ra != rb:
            # rb will be overwritten, save rb value first
            asm.mov(size=RegSize.R64, a=TEMP_REG, b=r_map[rb])
            asm.cmp(
                Operands.RegMem_Reg(
                    size=Size.U64, reg_mem=RegMem.Reg(r_map[ra]), reg=TEMP_REG
                )
            )
            asm.mov(size=RegSize.R64, a=r_map[rd], b=r_map[ra])
            asm.cmov(Condition.Less, RegSize.R64, r_map[rd], RegMem.Reg(TEMP_REG))
        else:
            # Normal case or ra == rd (which is fine)
            asm.cmp(
                Operands.RegMem_Reg(
                    size=Size.U64,
                    reg_mem=RegMem.Reg(r_map[ra]),
                    reg=r_map[rb],
                )
            )
            asm.mov(size=RegSize.R64, a=r_map[rd], b=r_map[ra])
            asm.cmov(
                Condition.Less, RegSize.R64, r_map[rd], RegMem.Reg(r_map[rb])
            )

    def max_u(self, asm, ra: int, rb: int, rd: int):
        """rd = max(ra, rb) (unsigned comparison)"""
        # Handle register aliasing by saving values if needed
        if rb == rd and ra != rb:
            # rb will be overwritten, save rb value first
            asm.mov(size=RegSize.R64, a=TEMP_REG, b=r_map[rb])
            asm.cmp(
                Operands.RegMem_Reg(
                    size=Size.U64, reg_mem=RegMem.Reg(r_map[ra]), reg=TEMP_REG
                )
            )
            asm.mov(size=RegSize.R64, a=r_map[rd], b=r_map[ra])
            asm.cmov(Condition.Below, RegSize.R64, r_map[rd], RegMem.Reg(TEMP_REG))
        else:
            # Normal case or ra == rd (which is fine)
            asm.cmp(
                Operands.RegMem_Reg(
                    size=Size.U64,
                    reg_mem=RegMem.Reg(r_map[ra]),
                    reg=r_map[rb],
                )
            )
            asm.mov(size=RegSize.R64, a=r_map[rd], b=r_map[ra])
            asm.cmov(
                Condition.Below, RegSize.R64, r_map[rd], RegMem.Reg(r_map[rb])
            )

    def min_op(self, asm, ra: int, rb: int, rd: int):
        """rd = min(ra, rb) (signed comparison)"""
        # Handle register aliasing by saving values if needed
        if rb == rd and ra != rb:
            # rb will be overwritten, save rb value first
            asm.mov(size=RegSize.R64, a=TEMP_REG, b=r_map[rb])
            asm.cmp(
                Operands.RegMem_Reg(
                    size=Size.U64, reg_mem=RegMem.Reg(r_map[ra]), reg=TEMP_REG
                )
            )
            asm.mov(size=RegSize.R64, a=r_map[rd], b=r_map[ra])
            asm.cmov(
                Condition.Greater, RegSize.R64, r_map[rd], RegMem.Reg(TEMP_REG)
            )
        else:
            # Normal case or ra == rd (which is fine)
            asm.cmp(
                Operands.RegMem_Reg(
                    size=Size.U64,
                    reg_mem=RegMem.Reg(r_map[ra]),
                    reg=r_map[rb],
                )
            )
            asm.mov(size=RegSize.R64, a=r_map[rd], b=r_map[ra])
            asm.cmov(
                Condition.Greater,
                RegSize.R64,
                r_map[rd],
                RegMem.Reg(r_map[rb]),
            )

    def min_u(self, asm, ra: int, rb: int, rd: int):
        """rd = min(ra, rb) (unsigned comparison)"""
        # Handle register aliasing by saving values if needed
        if rb == rd and ra != rb:
            # rb will be overwritten, save rb value first
            asm.mov(size=RegSize.R64, a=TEMP_REG, b=r_map[rb])
            asm.cmp(
                Operands.RegMem_Reg(
                    size=Size.U64, reg_mem=RegMem.Reg(r_map[ra]), reg=TEMP_REG
                )
            )
            asm.mov(size=RegSize.R64, a=r_map[rd], b=r_map[ra])
            asm.cmov(Condition.Above, RegSize.R64, r_map[rd], RegMem.Reg(TEMP_REG))
        else:
            # Normal case or ra == rd (which is fine)
            asm.cmp(
                Operands.RegMem_Reg(
                    size=Size.U64,
                    reg_mem=RegMem.Reg(r_map[ra]),
                    reg=r_map[rb],
                )
            )
            asm.mov(size=RegSize.R64, a=r_map[rd], b=r_map[ra])
            asm.cmov(
                Condition.Above, RegSize.R64, r_map[rd], RegMem.Reg(r_map[rb])
            )
