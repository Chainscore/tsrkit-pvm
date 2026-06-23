import json
import logging
from pathlib import Path
import pytest

from tsrkit_pvm.common.status import ExecutionStatus
from tsrkit_pvm.recompiler.vm_context import VMContext

from .types import PvmGasOnlyTestcase, PvmStepTestcase, PvmTestcase, is_step_testcase

PVM_ROOT = Path(__file__).parent / "ext" / "pvm" / "programs"
PVM_GAS_ROOT = Path(__file__).parent / "ext" / "pvm" / "gas-tests"


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

V05_PATTERNS = [
    "*.json",
]


def _is_v05_vector(vector: dict) -> bool:
    return is_step_testcase(vector)


def _assert_status(actual, expected_name: str, expected_hostcall=None, expected_page_fault=None):
    if expected_name == "ecalli":
        assert actual.value.name == "host"
        if expected_hostcall is not None:
            assert actual.value.register == expected_hostcall
        return

    assert actual.value.name == expected_name
    if expected_page_fault is not None:
        assert actual.value.register == expected_page_fault


def _run_step_testcase(tc: PvmStepTestcase):
    from tsrkit_pvm.interpreter.memory import INT_Memory
    from tsrkit_pvm.interpreter.program import INT_Program
    from tsrkit_pvm.interpreter.pvm import Interpreter

    program = INT_Program.decode_from(bytes(tc.program))[0]
    registers = [0] * 13
    memory = INT_Memory({}, [], [])
    pc = tc.initial_pc
    resume_pc = tc.initial_pc
    gas = tc.initial_gas
    block_gas_charged = False
    status = None

    for step in tc.steps:
        if step.map is not None:
            step.map.apply(memory)
        elif step.write is not None:
            step.write.write_unchecked(memory)
        elif step.set_reg is not None:
            registers[step.set_reg.reg] = step.set_reg.value
        elif step.run:
            status, pc, gas, block_gas_charged, registers, memory = Interpreter.execute_ext(
                program,
                resume_pc,
                gas,
                registers,
                memory,
                block_gas_charged=block_gas_charged,
            )
            resume_pc = pc
            if status == ExecutionStatus.HOST:
                resume_pc = pc + 1 + program.skip(pc)
        elif step.assert_ is not None:
            expected = step.assert_
            assert status is not None, f"{tc.name}: assert step appeared before run"
            if expected.status is not None:
                _assert_status(
                    status,
                    expected.status,
                    expected_hostcall=expected.hostcall,
                    expected_page_fault=expected.page_fault_address,
                )
            if expected.pc is not None:
                assert pc == expected.pc, tc.name
            if expected.gas is not None:
                assert gas == expected.gas, tc.name
            if expected.regs is not None:
                assert registers == expected.regs, tc.name
            if expected.memory is not None:
                for segment in expected.memory:
                    segment.assert_matches(memory, tc.name)


def _write_unchecked_cymemory(memory, segment):
    address = segment.address & (2**32 - 1)
    for i, byte in enumerate(segment.contents):
        memory._set_byte(address + i, byte)


def _write_unchecked_recmemory(memory, segment):
    memory.write_unchecked(segment.address & (2**32 - 1), bytes(segment.contents))


def _run_step_testcase_cython(tc: PvmStepTestcase):
    from tsrkit_pvm.cpvm.cy_memory import CyMemory
    from tsrkit_pvm.cpvm.cy_program import CyProgram
    from tsrkit_pvm.cpvm.cy_pvm import CyInterpreter

    program = CyProgram.decode_from(bytes(tc.program))[0]
    registers = [0] * 13
    memory = CyMemory({}, [], [])
    pc = tc.initial_pc
    resume_pc = tc.initial_pc
    gas = tc.initial_gas
    block_gas_charged = False
    status = None

    for step in tc.steps:
        if step.map is not None:
            step.map.apply(memory)
        elif step.write is not None:
            _write_unchecked_cymemory(memory, step.write)
        elif step.set_reg is not None:
            registers[step.set_reg.reg] = step.set_reg.value
        elif step.run:
            status, pc, gas, block_gas_charged, registers, memory = CyInterpreter.execute_ext(
                program,
                resume_pc,
                gas,
                registers,
                memory,
                block_gas_charged=block_gas_charged,
            )
            resume_pc = pc
            if status == ExecutionStatus.HOST:
                resume_pc = pc + 1 + program.skip(pc)
        elif step.assert_ is not None:
            expected = step.assert_
            assert status is not None, f"{tc.name}: assert step appeared before run"
            if expected.status is not None:
                _assert_status(
                    status,
                    expected.status,
                    expected_hostcall=expected.hostcall,
                    expected_page_fault=expected.page_fault_address,
                )
            if expected.pc is not None:
                assert pc == expected.pc, tc.name
            if expected.gas is not None:
                assert gas == expected.gas, tc.name
            if expected.regs is not None:
                assert registers == expected.regs, tc.name
            if expected.memory is not None:
                for segment in expected.memory:
                    segment.assert_matches(memory, tc.name)


def _run_step_testcase_recompiler(tc: PvmStepTestcase):
    from tsrkit_pvm.recompiler.memory import REC_Memory
    from tsrkit_pvm.recompiler.program import REC_Program
    from tsrkit_pvm.recompiler.pvm import Recompiler

    program = REC_Program.decode_from(bytes(tc.program))[0]
    registers = [0] * 13
    memory = REC_Memory.from_initial([], [], VMContext.calculate_size(len(program.jump_table)))
    pc = tc.initial_pc
    resume_pc = tc.initial_pc
    gas = tc.initial_gas
    status = None

    for step in tc.steps:
        if step.map is not None:
            step.map.apply(memory)
        elif step.write is not None:
            _write_unchecked_recmemory(memory, step.write)
        elif step.set_reg is not None:
            registers[step.set_reg.reg] = step.set_reg.value
        elif step.run:
            status, pc, gas, registers, memory = Recompiler.execute(
                program,
                resume_pc,
                gas,
                registers,
                memory,
            )
            resume_pc = pc
            if status == ExecutionStatus.HOST:
                resume_pc = pc + 1 + program.skip(pc)
        elif step.assert_ is not None:
            expected = step.assert_
            assert status is not None, f"{tc.name}: assert step appeared before run"
            if expected.status is not None:
                _assert_status(
                    status,
                    expected.status,
                    expected_hostcall=expected.hostcall,
                    expected_page_fault=expected.page_fault_address,
                )
            if expected.pc is not None:
                assert pc == expected.pc, tc.name
            if expected.gas is not None:
                assert gas == expected.gas, tc.name
            if expected.regs is not None:
                assert registers == expected.regs, tc.name
            if expected.memory is not None:
                for segment in expected.memory:
                    segment.assert_matches(memory, tc.name)


def _assert_block_gas_costs(name: str, vector: PvmGasOnlyTestcase | PvmStepTestcase):
    from tsrkit_pvm.interpreter.instructions.inst_map import inst_map
    from tsrkit_pvm.interpreter.program import INT_Program

    program = INT_Program.decode_from(bytes(vector.program))[0]
    for entry in vector.block_gas_costs:
        block = inst_map.get_block(program, entry.pc)
        assert block.total_gas == entry.cost, f"{name} pc={entry.pc}"
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
        if _is_v05_vector(vector):
            tc = PvmStepTestcase.from_json(vector)
            _run_step_testcase_recompiler(tc)
            continue
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
        if _is_v05_vector(vector):
            tc = PvmStepTestcase.from_json(vector)
            _run_step_testcase_cython(tc)
            continue
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
        
@pytest.mark.parametrize("pattern", V05_PATTERNS)
def test_vectors_intr(pattern: str):
    """Test PVM v0.5 step vectors with a given pattern."""
    vectors = fetch_vectors(pattern)
    if not vectors:
        pytest.skip(f"No test vectors found for pattern: {pattern}")

    for i, (name, vector) in enumerate(vectors):
        print(f"#--- [{i}/{len(vectors)}] ---#")
        print(f"⏭️Running test case {name} ...")
        if not _is_v05_vector(vector):
            pytest.skip("legacy v0.4 vector shape is not present in current ext/pvm")
        tc = PvmStepTestcase.from_json(vector)
        _assert_block_gas_costs(name, tc)
        _run_step_testcase(tc)
        print("✅Passed")


def test_vectors_gas_only_block_costs():
    vectors = sorted(PVM_GAS_ROOT.glob("*.json"))
    if not vectors:
        pytest.skip("No gas-only vectors found")

    for path in vectors:
        tc = PvmGasOnlyTestcase.from_json(json.loads(path.read_text()))
        _assert_block_gas_costs(path.name, tc)


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
