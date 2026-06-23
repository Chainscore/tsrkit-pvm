from __future__ import annotations

from dataclasses import dataclass

from tsrkit_pvm.core.opcode import ExecutionUnits

MOVE_REG_OPCODE = 100

MAX_DECODE_SLOTS = 4
MAX_START_SLOTS = 5
MAX_PENDING_ROB = 32
INITIAL_UNITS = ExecutionUnits(4, 4, 4, 1, 1)

STATE_DEC = "DEC"
STATE_WAIT = "WAIT"
STATE_EXE = "EXE"
STATE_FIN = "FIN"
STATE_EMPTY = "EMPTY"


@dataclass
class ReorderBufferEntry:
    state: str
    cycles_left: int
    dependencies: set[int]
    clobbered_registers: set[int]
    units: ExecutionUnits


@dataclass
class GasSimulationState:
    pc: int | None
    cycles: int
    decode_slots: int
    start_slots: int
    units: ExecutionUnits
    rob: list[ReorderBufferEntry]


def _units_fit(required: ExecutionUnits, available: ExecutionUnits) -> bool:
    return (
        required.alu <= available.alu
        and required.load <= available.load
        and required.store <= available.store
        and required.multiply <= available.multiply
        and required.divide <= available.divide
    )


def _add_units(a: ExecutionUnits, b: ExecutionUnits) -> ExecutionUnits:
    return ExecutionUnits(
        a.alu + b.alu,
        a.load + b.load,
        a.store + b.store,
        a.multiply + b.multiply,
        a.divide + b.divide,
    )


def _sub_units(a: ExecutionUnits, b: ExecutionUnits) -> ExecutionUnits:
    return ExecutionUnits(
        a.alu - b.alu,
        a.load - b.load,
        a.store - b.store,
        a.multiply - b.multiply,
        a.divide - b.divide,
    )


def _pending_rob_count(rob: list[ReorderBufferEntry]) -> int:
    return sum(1 for entry in rob if entry.state != STATE_EMPTY)


def select_ready_reorder_buffer_entry(state: GasSimulationState) -> int | None:
    for index, entry in enumerate(state.rob):
        if entry.state != STATE_WAIT:
            continue
        if not _units_fit(entry.units, state.units):
            continue
        if all(state.rob[dependency].cycles_left == 0 for dependency in entry.dependencies):
            return index
    return None


def _decode_move_reg(state: GasSimulationState, instruction: tuple) -> None:
    _, _, _, decode_slots, _, source_registers, destination_registers = instruction
    source_set = set(source_registers)
    destination_set = set(destination_registers)
    for entry in state.rob:
        if entry.state == STATE_EMPTY:
            continue
        if entry.clobbered_registers & source_set:
            entry.clobbered_registers |= destination_set
        else:
            entry.clobbered_registers -= destination_set
    state.decode_slots -= decode_slots
    state.pc = state.pc + 1 if state.pc is not None else None


def _decode_instruction(state: GasSimulationState, instructions: list[tuple]) -> None:
    if state.pc is None:
        return
    pc, opcode, execution_cycles, decode_slots, units, source_registers, destination_registers = instructions[state.pc]
    if opcode == MOVE_REG_OPCODE:
        _decode_move_reg(state, instructions[state.pc])
        return

    source_set = set(source_registers)
    destination_set = set(destination_registers)
    dependencies = {
        index
        for index, entry in enumerate(state.rob)
        if entry.state != STATE_EMPTY and source_set & entry.clobbered_registers
    }
    for entry in state.rob:
        if entry.state != STATE_EMPTY:
            entry.clobbered_registers -= destination_set
    state.rob.append(
        ReorderBufferEntry(
            state=STATE_DEC,
            cycles_left=execution_cycles,
            dependencies=dependencies,
            clobbered_registers=destination_set,
            units=units,
        )
    )
    state.decode_slots -= decode_slots
    state.pc = state.pc + 1
    if state.pc >= len(instructions):
        state.pc = None


def _start_ready_entry(state: GasSimulationState) -> bool:
    if state.start_slots <= 0:
        return False
    index = select_ready_reorder_buffer_entry(state)
    if index is None:
        return False
    entry = state.rob[index]
    entry.state = STATE_EXE
    state.units = _sub_units(state.units, entry.units)
    state.start_slots -= 1
    return True


def _advance_cycle(state: GasSimulationState) -> None:
    old_entries = [
        ReorderBufferEntry(
            entry.state,
            entry.cycles_left,
            set(entry.dependencies),
            set(entry.clobbered_registers),
            entry.units,
        )
        for entry in state.rob
    ]
    units = state.units
    for entry in old_entries:
        if entry.state == STATE_EXE and entry.cycles_left == 1:
            units = _add_units(units, entry.units)

    new_entries: list[ReorderBufferEntry] = []
    for index, entry in enumerate(old_entries):
        if all(old_entries[k].state in (STATE_FIN, STATE_EMPTY) for k in range(index + 1)):
            new_state = STATE_EMPTY
        elif entry.state == STATE_DEC:
            new_state = STATE_WAIT
        elif entry.state == STATE_EXE and entry.cycles_left == 0:
            new_state = STATE_FIN
        else:
            new_state = entry.state

        cycles_left = entry.cycles_left - 1 if entry.state == STATE_EXE and entry.cycles_left > 0 else entry.cycles_left
        new_entries.append(
            ReorderBufferEntry(
                state=new_state,
                cycles_left=cycles_left,
                dependencies=entry.dependencies,
                clobbered_registers=entry.clobbered_registers,
                units=entry.units,
            )
        )

    state.cycles += 1
    state.decode_slots = MAX_DECODE_SLOTS
    state.start_slots = MAX_START_SLOTS
    state.units = units
    state.rob = new_entries


def simulate_basic_block_cycles(instructions: list[tuple]) -> int:
    state = GasSimulationState(
        pc=0 if instructions else None,
        cycles=0,
        decode_slots=MAX_DECODE_SLOTS,
        start_slots=MAX_START_SLOTS,
        units=INITIAL_UNITS,
        rob=[],
    )

    while True:
        if (
            state.pc is not None
            and _pending_rob_count(state.rob) < MAX_PENDING_ROB
            and instructions[state.pc][3] <= state.decode_slots
        ):
            _decode_instruction(state, instructions)
            continue
        if _start_ready_entry(state):
            continue
        if state.pc is None and _pending_rob_count(state.rob) == 0:
            return state.cycles
        _advance_cycle(state)


def compute_basic_block_gas(instructions: list[tuple]) -> int:
    return max(simulate_basic_block_cycles(instructions) - 3, 1)
