import json
from pathlib import Path

from tsrkit_pvm.recompiler.memory import Memory
from tsrkit_pvm.recompiler.program import Program
from tsrkit_pvm.recompiler.pvm import PVM

PVM_ROOT = Path(__file__).parent / "ext" / "pvm" / "programs"

def fetch_vectors(pattern: str):
    return [
        (f.name, json.load(open(f)))
        for f in PVM_ROOT.glob(pattern)
    ]

def test_pvm_vectors():
    pattern = "inst_add_imm_64*.json"
    for name, vector in fetch_vectors(pattern):
        print(f"\n ⏭️Running test case {name} ...")
        print("\nProcessing test case: ", vector["name"])
        

        program = Program.decode(bytes(vector["program"]))
        program.mem = Memory.from_initial(vector["initial-page-map"], vector["initial-memory"])

        _, counter, rem_gas, registers = PVM.execute(
            program,
            int(vector["initial-pc"]),
            vector["initial-regs"],
            int(vector["initial-gas"])
        )
        # assert pc == tc.expected_pc
        # assert status.value.name == tc.expected_status
        assert registers.to_json() == vector["expected-regs"]
        # assert memory == tc.expected_memory.to_memory(tc.initial_page_map)
        print("✅Passed")
