from __future__ import annotations

from tsrkit_pvm.core.opcode import ExecutionUnits, GasProfile

ALU = ExecutionUnits(1, 0, 0, 0, 0)
NO_UNITS = ExecutionUnits(0, 0, 0, 0, 0)
LOAD_UNITS = ExecutionUnits(1, 1, 0, 0, 0)
STORE_UNITS = ExecutionUnits(1, 0, 1, 0, 0)
MUL_UNITS = ExecutionUnits(1, 0, 0, 1, 0)
DIV_UNITS = ExecutionUnits(1, 0, 0, 0, 1)


def profile(cycles: int | str, decode_slots: int | tuple, units: ExecutionUnits) -> GasProfile:
    return GasProfile(cycles, decode_slots, units)
