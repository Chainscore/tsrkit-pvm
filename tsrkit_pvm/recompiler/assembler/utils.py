from tsrkit_asm import LoadKind, MemOp, Reg, RegSize, Size, PyAssembler
from ..vm_context import r_map, regs_offset


def save_all_regs(asm: PyAssembler) -> None:
    for i, reg in enumerate(r_map):
        asm.store(
            size=Size.U64,
            mem=MemOp.BaseOffset(
                seg=None, size=RegSize.R64, base=Reg.r15, offset=(regs_offset + i * 8)
            ),
            reg=reg,
        )


def load_all_regs(asm: PyAssembler) -> None:
    for i, reg in enumerate(r_map):
        # Load value from offset+i_bytes -> mapped register
        asm.load(
            kind=LoadKind.U64,
            reg=reg,
            mem=MemOp.BaseOffset(
                seg=None,
                size=RegSize.R64,
                base=Reg.r15,
                offset=(regs_offset + i * 8),
            ),
        )


def push_all_regs(asm: PyAssembler) -> None:
    for i in r_map:
        asm.push(i)


def pop_all_regs(asm: PyAssembler) -> None:
    for i in reversed(r_map):
        asm.pop(i)
