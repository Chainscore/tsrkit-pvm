from copy import deepcopy
import json
import os
from pathlib import Path

import pytest

from tests.types import PvmTestcase
from tsrkit_pvm.recompiler.assembler.inst_map import inst_map
from tsrkit_pvm.recompiler.vm_context import VMContext

PVM_ROOT = Path(__file__).parent / "ext" / "pvm" / "programs"


def fetch_vectors(pattern: str):
    return [(f.name, json.load(open(f))) for f in PVM_ROOT.glob(pattern)]

@pytest.mark.skip
def test_debug_mismatch():
    """Test a single pattern - can be modified for quick testing"""
    pattern = os.environ["PTRN"] or "riscv_rv64ui_lw.json"
    all_matches = fetch_vectors(pattern)
    if len(all_matches) == 0:
        print(f"No matches found for pattern -- {pattern}")
        return 
    name, vector = all_matches[0]
    print(f"\n ⏭️Running test case {name} ...")
    print(f"Processing test case: {vector['name']}")


    from tsrkit_pvm.interpreter.program import Program
    tc = PvmTestcase.from_json(vector)
    tc_prog = Program.decode(tc.program)
    
    c = 0
    for i, inst in enumerate(tc_prog.instruction_set):
        if tc_prog.offset_bitmask[i]:
            print(f" [{c - tc.initial_pc}] {inst_map._dispatch_table[inst].name}")
            c += 1

    steps = 1
    while True:
        print(f"|------ Step {steps} ------|")
        print(f"[1] Running in PVM mode...")
        from tsrkit_pvm.interpreter.pvm import PVM


        i_status, i_pc, i_gas, i_registers, i_memory = PVM.execute(
            tc_prog,
            int(tc.initial_pc),
            deepcopy(steps),
            [int(reg) for reg in tc.initial_regs],
            tc.initial_memory.to_memory(tc.initial_page_map),
        )
        
        print(f"[2] Running in native mode...")
        from tsrkit_pvm.recompiler.program import Program
        from tsrkit_pvm.recompiler.pvm import PVM
        from tsrkit_pvm.recompiler.memory import GuestMemory

        program = Program.decode(bytes(vector["program"]))
        mem = GuestMemory.from_initial(
            vector["initial-page-map"],
            vector["initial-memory"],
            VMContext.calculate_size(len(program.jump_table)),
        )

        r_status, r_counter, r_gas, r_registers = PVM.execute(
            program,
            mem,
            int(vector["initial-pc"]),
            vector["initial-regs"],
            deepcopy(steps),
        )

        assert r_status == i_status, "Should have same status"

        print("\t i", i_registers)
        print("\t r", r_registers)

        if i_registers != r_registers:
            print(f"Mismatch found")
            break

        if i_status._value_.name != "out-of-gas":
            print("Interpreter exiting...")
            break
        elif r_status._value_.name != "out-of-gas":
            print("Recompiler exiting...")
            break

        steps += 1
