from typing import Dict, Tuple 
from tsrkit_pvm.core.program_base import Program
from tsrkit_pvm.recompiler.assembler.context import AssemblerContext
from tsrkit_pvm.recompiler.vm_context import gas_offset
from .assembler.inst_map import inst_map
from tsrkit_asm import (
    Condition,
    ImmKind,
    MemOp,
    Operands,
    PyAssembler,
    Reg,
    RegMem,
    RegSize,
)


class REC_Program(Program):
    """This is the program blob which the PVM will execute."""

    # Assembled Machine Code
    msn_code: bytes
    # Indexes of machine inst in msn_code
    pvm_msn_map: list[int]
    # Index to halt label
    halt_offset: int
    # Index to panic label
    panic_offset: int

    _skip_cache: Dict[int, int]

    is_recompiler = True

    def __post_init__(self):
        super().__post_init__()
        self._skip_cache: Dict[int, int] = {}
        self._precompute_skip_values()        
        basic_blocks = [0]
        for n in range(len(self.instruction_set)):
            if self.offset_bitmask[n] and inst_map.is_terminating(
                self.instruction_set[n]
            ):
                basic_blocks.append(n + 1 + self.skip(n))
        self.basic_blocks = basic_blocks
        self.msn_code, self.pvm_msn_map, self.panic_offset, self.halt_offset = None, None, None, None

    def _precompute_skip_values(self):
        """Pre-compute skip values for all positions to eliminate runtime overhead."""
        for i in range(len(self.offset_bitmask)):
            skip_value = len(self.offset_bitmask)
            for j in range(i + 1, len(self.offset_bitmask) + 1):
                if self._extended_bitmask[j]:
                    skip_value = j - i - 1
                    break

            self._skip_cache[i] = min(24, skip_value)

    def assemble(self, logger=None) -> Tuple[bytes, dict, int, int]:
        asm = PyAssembler()

        # Create labels for all basic blocks (jump targets)
        labels = {}
        for i in range(len(self.instruction_set)):
            if self.offset_bitmask[i]:
                labels[i] = asm.forward_declare_label()

        halt_label = asm.forward_declare_label()
        panic_label = asm.forward_declare_label()
        # Create context wrapper
        asm_ctx = AssemblerContext(
            asm, labels, halt_label, panic_label, len(self.jump_table)
        )

        counter = 0
        pvm_table = []
        while counter < len(self.instruction_set):
            if self.offset_bitmask[counter]:  # Only process actual opcodes
                # Define labe
                asm.define_label(labels[counter])

                pvm_table.append(asm.current_address())

                opcode = self.instruction_set[counter]
                if logger:
                    logger.debug(
                        f"📍 {counter} \t Processing opcode \t {inst_map._dispatch_table[opcode].fn.__name__} ({opcode})"
                    )
                
                gas = inst_map._dispatch_table[opcode].gas_cost
                # --- Gas Computation --- #
                x61mov_imm = -gas_offset + 0x61
                asm.sub(
                    Operands.RegMem_Imm(RegMem.Reg(Reg.r15), ImmKind.I64(x61mov_imm))
                )
                asm.sub(
                    Operands.RegMem_Imm(
                        RegMem.Mem(
                            MemOp.BaseOffset(
                                seg=None, size=RegSize.R64, base=Reg.r15, offset=0x61
                            )
                        ),
                        ImmKind.I32(gas),
                    )
                )
                asm.jcc_rel32(Condition.Sign, -2)
                asm.add(
                    Operands.RegMem_Imm(RegMem.Reg(Reg.r15), ImmKind.I64(x61mov_imm))
                )
                
                _, gas = inst_map.process_instruction(opcode, self, counter, asm_ctx)

                

            counter += 1

        # If normally returned, then its a panic
        asm.define_label(panic_label)
        panic_addr = asm.current_address()
        asm.ret()

        # Add a block for HALT exit
        asm.define_label(halt_label)
        halt_addr = asm.current_address()
        # Jump to memory, which is non-executable and will throw seg fault
        asm.ud2()

        if logger:
            logger.debug(
                f"🧩 Assembled program size: {asm.len()} "
            )

        (
            self.msn_code, 
            self.pvm_msn_map, 
            self.panic_offset, 
            self.halt_offset
        ) = asm.finalize(), pvm_table, panic_addr, halt_addr

    def msn_to_pvm_index(self, msn_offset: int):
        """Input any location from native code, and this will return its PVM inst start"""
        target = self.pvm_msn_map
        res = 0
        # Binary search to find
        while len(target) != 1:
            res = len(target) // 2
            target = (
                target[:res] if msn_offset < target[res] else target[res:]
            )
        pvm_inst_index = self.pvm_msn_map.index(target[0])

        inst_index = 0
        for i, bm in enumerate(self.offset_bitmask):
            if bm:
                if inst_index == pvm_inst_index:
                    return i
                inst_index += 1
                

    def pvm_to_msn_index(self, pvm_offset: int) -> int:
        """Input any index of PVM inst start [from inst set], and this will return its machine inst start"""
        bms = self.offset_bitmask[:pvm_offset]
        return self.pvm_msn_map[bms.count(True)]

    def skip(self, pc) -> int:
        return self._skip_cache.get(pc, 0)

