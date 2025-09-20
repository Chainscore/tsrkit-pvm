import json
import logging
from pathlib import Path
import pytest

from tsrkit_pvm.recompiler.vm_context import VMContext

from .types import PvmTestcase

PVM_ROOT = Path(__file__).parent / "ext" / "pvm" / "programs"


def fetch_vectors(pattern: str):
    return [(f.name, json.load(open(f))) for f in PVM_ROOT.glob(pattern)]


PATTERNS = [
    "inst_add*.json",
    "inst_sub*.json",
    "inst_mul*.json",
    "inst_div*.json",
    "inst_rem*.json",
    "inst_and*.json",
    "inst_or*.json",
    "inst_xor*.json",
    "inst_shift*.json",
    "inst_set*.json",
    "inst_cmov*.json",
    "inst_load*.json",
    "inst_store*.json",
    "inst_jump*.json",
    "inst_branch*.json",
    "inst_ret*.json",
    "inst_trap*.json",
    "inst_fallthrough*.json",
    "riscv*.json",
]
@pytest.mark.parametrize(
    "pattern",
    PATTERNS,
)
def test_vectors_recompiler(pattern: str):
    """Test PVM vectors with a given pattern"""
    vectors = fetch_vectors(pattern)
    if not vectors:
        pytest.skip(f"No test vectors found for pattern: {pattern}")

    for i, (name, vector) in enumerate(vectors):
        print(f"#--- [{i}/{len(vectors)}] ---#")
        print(f"⏭️Running test case {name} ...")
        from tsrkit_pvm.recompiler.program import REC_Program
        from tsrkit_pvm.recompiler.pvm import PVM
        from tsrkit_pvm.recompiler.memory import REC_Memory

        program = REC_Program.decode(bytes(vector["program"]))
        mem = REC_Memory.from_initial(
            vector["initial-page-map"],
            vector["initial-memory"],
            VMContext.calculate_size(len(program.jump_table)),
        )

        status, counter, rem_gas, registers, mem = PVM.execute(
            program,
            int(vector["initial-pc"]),
            int(vector["initial-gas"]),
            vector["initial-regs"],
            mem,
        )

        assert registers == vector["expected-regs"], f"Register mismatch in {name}"
        print("✅Passed")
        
        
@pytest.mark.parametrize(
    "pattern",
    PATTERNS,
)
def test_vectors_cython(pattern: str):
    """Test PVM vectors with a given pattern"""
    vectors = fetch_vectors(pattern)
    if not vectors:
        pytest.skip(f"No test vectors found for pattern: {pattern}")

    for i, (name, vector) in enumerate(vectors):
        print(f"#--- [{i}/{len(vectors)}] ---#")
        print(f"⏭️Running test case {name} ...")
        from tsrkit_pvm.cpvm.cy_pvm import CyInterpreter
        from tsrkit_pvm.cpvm.cy_memory import CyMemory
        from tsrkit_pvm.cpvm.cy_program import CyProgram
        
        tc = PvmTestcase.from_json(vector)
        tc_prog = CyProgram.decode_from(tc.program)[0]

        status, counter, rem_gas, registers, mem = CyInterpreter.execute(
            tc_prog,
            int(tc.initial_pc),
            int(tc.initial_gas),
            [int(reg) for reg in tc.initial_regs],
            tc.initial_memory.to_cymemory(tc.initial_page_map),
        )

        assert registers == vector["expected-regs"], f"Register mismatch in {name}"
        print("✅Passed")
        
@pytest.mark.parametrize(
    "pattern",
    PATTERNS,
)
def test_vectors_intr(pattern: str):
    """Test PVM vectors with a given pattern"""
    vectors = fetch_vectors(pattern)
    if not vectors:
        pytest.skip(f"No test vectors found for pattern: {pattern}")

    for i, (name, vector) in enumerate(vectors):
        print(f"#--- [{i}/{len(vectors)}] ---#")
        print(f"⏭️Running test case {name} ...")
        from tsrkit_pvm.interpreter.program import INT_Program
        from tsrkit_pvm.interpreter.pvm import Interpreter
        
        tc = PvmTestcase.from_json(vector)
        tc_prog = INT_Program.decode_from(tc.program)[0]
        print(list(tc_prog.instruction_set))

        status, counter, rem_gas, registers, mem = Interpreter.execute(
            tc_prog,
            int(tc.initial_pc),
            int(tc.initial_gas),
            [int(reg) for reg in tc.initial_regs],
            tc.initial_memory.to_memory(tc.initial_page_map),
        )

        assert registers == vector["expected-regs"], f"Register mismatch in {name}"
        print("✅Passed")


def test_pvm_vectors_single_pattern():
    """Test a single pattern - can be modified for quick testing"""
    pattern = "a_debug.json"
    mode = "native_"
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    for name, vector in fetch_vectors(pattern):
        print(f"\n ⏭️Running test case {name} ...")
        print(f"Processing test case: {vector['name']}")
        if mode == "native":
            print("Running in native mode...")
            from tsrkit_pvm.recompiler.program import REC_Program
            from tsrkit_pvm.recompiler.pvm import PVM
            from tsrkit_pvm.recompiler.memory import REC_Memory

            program = REC_Program.decode(bytes(vector["program"]))
            mem = REC_Memory.from_initial(
                vector["initial-page-map"],
                vector["initial-memory"],
                VMContext.calculate_size(len(program.jump_table)),
            )

            status, counter, rem_gas, registers, mem = PVM.execute(
                program,
                int(vector["initial-pc"]),
                int(vector["initial-gas"]),
                vector["initial-regs"],
                mem,
                logger,
            )

            assert registers == vector["expected-regs"], f"Register mismatch in {name}"

            assert status._value_.name == vector["expected-status"]

            print("✅Passed")
        else:
            print("Running in PVM mode...")
            from tsrkit_pvm.interpreter.program import INT_Program
            from tsrkit_pvm.interpreter.pvm import PVM

            tc = PvmTestcase.from_json(vector)

            status, pc, gas, registers, memory = PVM.execute(
                INT_Program.decode(tc.program),
                int(tc.initial_pc),
                int(tc.initial_gas),
                [int(reg) for reg in tc.initial_regs],
                tc.initial_memory.to_memory(tc.initial_page_map),
            )

            print("status", status)

            # assert registers == tc.expected_regs
            # assert pc == tc.expected_pc
