from tsrkit_pvm.interpreter.program import INT_Program


def create_sbrk_test_program(rd: int, ra: int):
    """Create a simple program that just executes sbrk instruction.

    Args:
        rd: destination register (0-12)
        ra: source register containing bytes to allocate (0-12)

    Returns:
        Program object for the test
    """
    # sbrk instruction: opcode 101, register encoding (ra << 4) | rd
    sbrk_opcode = 101
    reg_encoding = (ra << 4) | rd

    # Create instruction sequence - just sbrk
    instruction_set = bytes([sbrk_opcode, reg_encoding])

    # Offset bitmask: True for opcodes, False for arguments
    offset_bitmask = [True, False]

    # Create program with no jump table (z=0, empty jump_table)
    return INT_Program(
        z=0,
        jump_table=[],
        instruction_set=instruction_set,
        offset_bitmask=offset_bitmask,
    )
