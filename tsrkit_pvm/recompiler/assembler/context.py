from tsrkit_asm import ImmKind, MemOp, Operands, PyAssembler, Reg, RegMem, RegSize, Size

from ..vm_context import TEMP_REG, ret_add_offset


class AssemblerContext:
    """Wrapper for Assembler to contain labels"""

    asm: PyAssembler
    labels: dict[int, int]
    halt_label: int
    panic_label: int
    jump_table_len: int
    current_pc: int

    def __init__(self, assembler, labels, halt_label, panic_label, jump_table_len):
        self.asm = assembler
        self.labels = labels
        self.halt_label = halt_label
        self.panic_label = panic_label
        self.jump_table_len = jump_table_len
        self.current_pc = 0

    def mark_panic_pc(self):
        self.mov_imm64(TEMP_REG, self.current_pc + 1)
        self.sub(Operands.RegMem_Imm(RegMem.Reg(Reg.r15), ImmKind.I64(-ret_add_offset)))
        self.store(
            size=Size.U64,
            mem=MemOp.BaseOffset(
                seg=None, size=RegSize.R64, base=Reg.r15, offset=0
            ),
            reg=TEMP_REG,
        )
        self.add(Operands.RegMem_Imm(RegMem.Reg(Reg.r15), ImmKind.I64(-ret_add_offset)))

    def panic(self):
        self.mark_panic_pc()
        self.ret()

    def jcc_panic(self, condition):
        panic_label = self.forward_declare_label()
        continue_label = self.forward_declare_label()
        self.jcc_label32(condition, panic_label)
        self.jmp_label32(continue_label)
        self.define_label(panic_label)
        self.panic()
        self.define_label(continue_label)

    def jcc_halt(self, condition):
        halt_path_label = self.forward_declare_label()
        continue_label = self.forward_declare_label()
        self.jcc_label32(condition, halt_path_label)
        self.jmp_label32(continue_label)
        self.define_label(halt_path_label)
        self.mark_panic_pc()
        self.jmp_label32(self.halt_label)
        self.define_label(continue_label)

    def __getattr__(self, name):
        # Delegate all other attributes to the underlying assembler
        return getattr(self.asm, name)
