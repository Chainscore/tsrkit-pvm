from tsrkit_asm import PyAssembler


class AssemblerContext:
    """Wrapper for Assembler to contain labels"""

    asm: PyAssembler
    labels: dict[int, int]
    halt_label: int
    panic_label: int
    jump_table_len: int

    def __init__(self, assembler, labels, halt_label, panic_label, jump_table_len):
        self.asm = assembler
        self.labels = labels
        self.halt_label = halt_label
        self.panic_label = panic_label
        self.jump_table_len = jump_table_len

    def __getattr__(self, name):
        # Delegate all other attributes to the underlying assembler
        return getattr(self.asm, name)
