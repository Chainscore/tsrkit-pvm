import json
from pathlib import Path

from tsrkit_pvm.common.status import ExecutionStatus
from tsrkit_pvm.interpreter.instructions.inst_map import inst_map
from tsrkit_pvm.interpreter.memory import INT_Memory
from tsrkit_pvm.interpreter.program import INT_Program
from tsrkit_pvm.interpreter.pvm import Interpreter


GAS_VECTOR_DIR = Path("tests/ext/pvm/programs")


def _gas_vectors():
    return sorted(GAS_VECTOR_DIR.glob("gas_*.json"))


def _decode_program(data):
    return INT_Program.decode_from(bytes(data["program"]))[0]


def test_block_gas_cost_vectors_match_expected_costs():
    for path in _gas_vectors():
        data = json.loads(path.read_text())
        program = _decode_program(data)
        for entry in data["block-gas-costs"]:
            block = inst_map.get_block(program, entry["pc"])
            assert block.total_gas == entry["cost"], f"{path.name} pc={entry['pc']}"


def test_gas_execution_vectors_match_expected_results():
    for path in _gas_vectors():
        data = json.loads(path.read_text())
        program = _decode_program(data)
        status, pc, gas, registers, _ = Interpreter.execute(
            program,
            data["initial-pc"],
            data["initial-gas"],
            [0] * 13,
            INT_Memory({}, [], []),
        )
        expected = next(step["assert"] for step in data["steps"] if "assert" in step)
        assert status.value.name == expected["status"], path.name
        assert pc == expected["pc"], path.name
        assert gas == expected["gas"], path.name
        assert registers == expected["regs"], path.name


def test_out_of_gas_precharge_leaves_gas_unchanged():
    data = json.loads((GAS_VECTOR_DIR / "gas_basic_consume_all.json").read_text())
    program = _decode_program(data)
    status, pc, gas, registers, _ = Interpreter.execute(
        program,
        data["initial-pc"],
        1,
        [0] * 13,
        INT_Memory({}, [], []),
    )
    assert status == ExecutionStatus.OUT_OF_GAS
    assert pc == data["initial-pc"]
    assert gas == 1
    assert registers == [0] * 13


def test_host_exit_preserves_block_charge_flag():
    program = INT_Program(0, [], bytes([10]), [True])
    status, pc, gas, block_gas_charged, registers, _ = Interpreter.execute_ext(
        program,
        0,
        1_000,
        [0] * 13,
        INT_Memory({}, [], []),
    )
    assert status == ExecutionStatus.HOST
    assert pc == 0
    assert gas < 1_000
    assert block_gas_charged is True
    assert registers == [0] * 13


def _single_immediate_memory_program(opcode: int, address: int) -> INT_Program:
    imm = address.to_bytes(4, "little")
    instruction_set = bytes([opcode, 0, *imm, 0])
    offset_bitmask = [True, False, False, False, False, False, True]
    return INT_Program(0, [], instruction_set, offset_bitmask)


def test_illegal_memory_read_consumes_precharged_gas():
    program = _single_immediate_memory_program(52, 2**16)
    block = inst_map.get_block(program, 0)
    status, pc, gas, registers, _ = Interpreter.execute(
        program,
        0,
        block.total_gas,
        [0] * 13,
        INT_Memory({}, [], []),
    )
    assert status == ExecutionStatus.PAGE_FAULT
    assert pc == 0
    assert gas == 0
    assert registers == [0] * 13


def test_illegal_memory_write_consumes_precharged_gas():
    program = _single_immediate_memory_program(59, 2**16)
    block = inst_map.get_block(program, 0)
    status, pc, gas, registers, _ = Interpreter.execute(
        program,
        0,
        block.total_gas,
        [7] + [0] * 12,
        INT_Memory({}, [], []),
    )
    assert status == ExecutionStatus.PAGE_FAULT
    assert pc == 0
    assert gas == 0
    assert registers == [7] + [0] * 12


def test_out_of_gas_takes_precedence_over_illegal_memory_access():
    program = _single_immediate_memory_program(59, 2**16)
    block = inst_map.get_block(program, 0)
    memory = INT_Memory({}, [], [])
    status, pc, gas, registers, result_memory = Interpreter.execute(
        program,
        0,
        block.total_gas - 1,
        [7] + [0] * 12,
        memory,
    )
    assert status == ExecutionStatus.OUT_OF_GAS
    assert pc == 0
    assert gas == block.total_gas - 1
    assert registers == [7] + [0] * 12
    assert result_memory == memory
