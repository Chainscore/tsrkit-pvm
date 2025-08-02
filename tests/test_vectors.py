import json
import logging
from pathlib import Path
import pytest

from tsrkit_pvm.recompiler.vm_context import VMContext

from .types import PvmTestcase

PVM_ROOT = Path(__file__).parent / "ext" / "pvm" / "programs"


def fetch_vectors(pattern: str):
    return [(f.name, json.load(open(f))) for f in PVM_ROOT.glob(pattern)]


@pytest.mark.parametrize(
    "pattern",
    [
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
        "inst_branch*.json",
        "riscv*.json",
    ],
)
def test_vectors(pattern: str):
    """Test PVM vectors with a given pattern"""
    vectors = fetch_vectors(pattern)
    if not vectors:
        pytest.skip(f"No test vectors found for pattern: {pattern}")

    for i, (name, vector) in enumerate(vectors):
        print(f"#--- [{i}/{len(vectors)}] ---#")
        print(f"⏭️Running test case {name} ...")
        from tsrkit_pvm.recompiler.program import Program
        from tsrkit_pvm.recompiler.pvm import PVM
        from tsrkit_pvm.recompiler.memory import GuestMemory

        program = Program.decode(bytes(vector["program"]))
        mem = GuestMemory.from_initial(
            vector["initial-page-map"],
            vector["initial-memory"],
            VMContext.calculate_size(len(program.jump_table)),
        )

        _, counter, rem_gas, registers = PVM.execute(
            program,
            mem,
            int(vector["initial-pc"]),
            vector["initial-regs"],
            int(vector["initial-gas"]),
        )

        assert registers == vector["expected-regs"], f"Register mismatch in {name}"
        print("✅Passed")


def test_pvm_vectors_single_pattern():
    """Test a single pattern - can be modified for quick testing"""
    pattern = "riscv_rv64ui_add.json"
    mode = "native"
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    for name, vector in fetch_vectors(pattern):
        print(f"\n ⏭️Running test case {name} ...")
        print(f"Processing test case: {vector['name']}")
        if mode == "native":
            print("Running in native mode...")
            from tsrkit_pvm.recompiler.program import Program
            from tsrkit_pvm.recompiler.pvm import PVM
            from tsrkit_pvm.recompiler.memory import GuestMemory

            program = Program.decode(bytes(vector["program"]))
            mem = GuestMemory.from_initial(
                vector["initial-page-map"],
                vector["initial-memory"],
                VMContext.calculate_size(len(program.jump_table)),
            )

            status, counter, rem_gas, registers = PVM.execute(
                program,
                mem,
                int(vector["initial-pc"]),
                vector["initial-regs"],
                int(vector["initial-gas"]),
                logger,
            )

            assert registers == vector["expected-regs"], f"Register mismatch in {name}"

            assert status._value_.name == vector["expected-status"]

            print("✅Passed")
        else:
            print("Running in PVM mode...")
            from tsrkit_pvm.interpreter.program import Program
            from tsrkit_pvm.interpreter.pvm import PVM

            tc = PvmTestcase.from_json(vector)

            status, pc, gas, registers, memory = PVM.execute(
                Program.decode(tc.program),
                int(tc.initial_pc),
                int(tc.initial_gas),
                [int(reg) for reg in tc.initial_regs],
                tc.initial_memory.to_memory(tc.initial_page_map),
            )

            assert pc == tc.expected_pc
            assert registers == tc.expected_regs
