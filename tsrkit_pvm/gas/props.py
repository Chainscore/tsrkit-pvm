from __future__ import annotations

from typing import Any

from tsrkit_pvm.core.opcode import ExecutionUnits, GasProfile

TRAP_OPCODE = 0
UNLIKELY_OPCODE = 2
MEMORY_ACCESS_CYCLES = 25


def _branch_target(opcode: int, args: list[int]) -> int:
    if 81 <= opcode <= 90:
        return args[4]
    if 170 <= opcode <= 175:
        return args[3]
    raise ValueError(f"Opcode {opcode} does not use branch gas")


def get_destination_registers(opcode: int, args: list[int]) -> tuple[int, ...]:
    if opcode in (20, 51):
        return (args[0],)
    if 52 <= opcode <= 58:
        return (args[0],)
    if opcode == 80:
        return (args[0],)
    if 100 <= opcode <= 110:
        return (args[0],)
    if 124 <= opcode <= 161:
        return (args[0],)
    if 190 <= opcode <= 230:
        return (args[2],)
    return ()


def get_source_registers(opcode: int, args: list[int]) -> tuple[int, ...]:
    if opcode == 50:
        return (args[0],)
    if 59 <= opcode <= 62:
        return (args[0],)
    if 70 <= opcode <= 73:
        return (args[0],)
    if 81 <= opcode <= 90:
        return (args[0],)
    if 100 <= opcode <= 110:
        return (args[1],)
    if 120 <= opcode <= 123:
        return (args[0], args[1])
    if 124 <= opcode <= 161:
        return (args[1],)
    if 170 <= opcode <= 175:
        return (args[0], args[1])
    if opcode == 180:
        return (args[1],)
    if 190 <= opcode <= 230:
        return (args[0], args[1])
    return ()


def _resolve_decode_slots(
    decode_slots: int | tuple,
    source_registers: tuple[int, ...],
    destination_registers: tuple[int, ...],
) -> int:
    if isinstance(decode_slots, int):
        return decode_slots
    kind, first, second = decode_slots
    if kind == "P":
        return first if set(source_registers) & set(destination_registers) else second
    if kind == "PS":
        return first if source_registers and destination_registers and source_registers[0] == destination_registers[0] else second
    raise ValueError(f"Unknown decode slot rule: {decode_slots!r}")


def _resolve_execution_cycles(program: Any, pc: int, opcode: int, args: list[int], execution_cycles: int | str) -> int:
    if isinstance(execution_cycles, int):
        return execution_cycles
    if execution_cycles == "memory":
        return MEMORY_ACCESS_CYCLES
    if execution_cycles == "branch":
        fallthrough = pc + 1 + program.skip(pc)
        target = _branch_target(opcode, args)
        if program.zeta[fallthrough] in (TRAP_OPCODE, UNLIKELY_OPCODE) or program.zeta[target] in (TRAP_OPCODE, UNLIKELY_OPCODE):
            return 1
        return 20
    raise ValueError(f"Unknown execution cycle rule: {execution_cycles!r}")


def resolve_gas_profile(
    program: Any,
    pc: int,
    opcode: int,
    args: list[int],
    profile: GasProfile,
) -> tuple[int, int, int, int, ExecutionUnits, tuple[int, ...], tuple[int, ...]]:
    source_registers = get_source_registers(opcode, args)
    destination_registers = get_destination_registers(opcode, args)
    execution_cycles = _resolve_execution_cycles(program, pc, opcode, args, profile.execution_cycles)
    decode_slots = _resolve_decode_slots(profile.decode_slots, source_registers, destination_registers)
    return (
        pc,
        opcode,
        execution_cycles,
        decode_slots,
        profile.units,
        source_registers,
        destination_registers,
    )
