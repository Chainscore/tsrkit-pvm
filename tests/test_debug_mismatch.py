import json
from pathlib import Path

from tests.types import PvmTestcase

PVM_ROOT = Path(__file__).parent / "ext" / "pvm" / "programs"


def fetch_vectors(pattern: str):
    return [(f.name, json.load(open(f))) for f in PVM_ROOT.glob(pattern)]


def test_debug_mismatch():
    """Test a single pattern - can be modified for quick testing"""
    pattern = "riscv_rv64ui_sub.json"
    all_matches = fetch_vectors(pattern)
    if len(all_matches) == 0:
        print(f"No matches found for pattern -- {pattern}")
        return 
    name, vector = all_matches[0]
    print(f"\n ⏭️Running test case {name} ...")
    print(f"Processing test case: {vector['name']}")

    steps = 1
    while True:
        print(f"|------ Step {steps} ------|")
        print(f"[1] Running in PVM mode...")
        from tsrkit_pvm.interpreter.program import Program
        from tsrkit_pvm.interpreter.pvm import PVM

        tc = PvmTestcase.from_json(vector)

        i_status, i_pc, i_gas, i_registers, i_memory = PVM.execute(
            Program.decode(tc.program),
            int(tc.initial_pc),
            steps,
            [int(reg) for reg in tc.initial_regs],
            tc.initial_memory.to_memory(tc.initial_page_map),
        )
        print("i_out", i_registers)


        print(f"[2] Running in native mode...")
        from tsrkit_pvm.recompiler.program import Program
        from tsrkit_pvm.recompiler.pvm import PVM
        from tsrkit_pvm.recompiler.memory import GuestMemory

        program = Program.decode(bytes(vector["program"]))
        mem = GuestMemory.from_initial(
            vector["initial-page-map"],
            vector["initial-memory"],
            jump_len=len(program.jump_table),
        )

        r_status, r_counter, r_gas, r_registers = PVM.execute(
            program,
            mem,
            int(vector["initial-pc"]),
            vector["initial-regs"],
            steps,
        )

        print("r_out", r_registers)

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
