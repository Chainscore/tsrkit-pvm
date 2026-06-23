from tsrkit_asm import ImmKind, LoadKind, MemOp, Operands, Reg, RegMem, RegSize, Size, PyAssembler
from ..vm_context import r_map, regs_offset


def _context_mem_access(asm: PyAssembler, offset: int):
    asm.sub(Operands.RegMem_Imm(RegMem.Reg(Reg.r15), ImmKind.I64(-offset)))
    return MemOp.BaseOffset(seg=None, size=RegSize.R64, base=Reg.r15, offset=0)


def _restore_context_base(asm: PyAssembler, offset: int):
    asm.add(Operands.RegMem_Imm(RegMem.Reg(Reg.r15), ImmKind.I64(-offset)))


def save_all_regs(asm: PyAssembler) -> None:
    for i, reg in enumerate(r_map):
        offset = regs_offset + i * 8
        mem = _context_mem_access(asm, offset)
        asm.store(
            size=Size.U64,
            mem=mem,
            reg=reg,
        )
        _restore_context_base(asm, offset)


def load_all_regs(asm: PyAssembler) -> None:
    for i, reg in enumerate(r_map):
        offset = regs_offset + i * 8
        mem = _context_mem_access(asm, offset)
        # Load value from offset+i_bytes -> mapped register
        asm.load(
            kind=LoadKind.U64,
            reg=reg,
            mem=mem,
        )
        _restore_context_base(asm, offset)


def push_all_regs(asm: PyAssembler) -> None:
    for i in r_map:
        asm.push(i)


def pop_all_regs(asm: PyAssembler) -> None:
    for i in reversed(r_map):
        asm.pop(i)
