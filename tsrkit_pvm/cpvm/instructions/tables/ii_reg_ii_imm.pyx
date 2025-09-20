# cython: cdivision=True, boundscheck=False, wraparound=False, nonecheck=False
# cython: initializedcheck=False, overflowcheck=False
# cython: profile=False, linetrace=False
# cython: language_level=3, infer_types=True, optimize.unpack_method_calls=True

from libc.stdint cimport uint32_t, int64_t, uint64_t, uint8_t, int8_t
from ...cy_utils cimport chi, clamp_12, clamp_4, clamp_4_max0
from ..cy_table cimport CyTable, CyTableEntry, instr_fn_t, InstructionProps
from ...cy_memory cimport CyMemory
from ...cy_program cimport CyProgram

cdef inline uint32_t load_imm_jump_ind_fn(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """OPC180: Load immediate value into register and jump indirect."""
    wb = registers[rb]
    registers[ra] = vx
    return program.djump(counter, (wb + vy) % 2**32)

cdef class CyInstructionsWArgs2Reg2Imm(CyTable):
    """
    Cython optimized instruction table for instructions with 2 register + 2 immediate arguments.
    """
    
    cdef InstructionProps get_props(self, uint32_t program_counter, CyProgram program, uint32_t skip_index):
        """
        Extract two registers and two immediate arguments from program bytes.
        Returns InstructionProps struct where vx/vy are immediates, ra/rb are registers, rd is 0.
        """
        cdef uint8_t* zeta_ptr = program.zeta
        cdef uint32_t byte1_val = zeta_ptr[program_counter + 1]
        cdef uint32_t byte2_val = zeta_ptr[program_counter + 2] if program_counter + 2 < program.zeta_len else 0
        
        # Parse registers from first byte
        cdef uint8_t ra = clamp_12(<uint8_t>(byte1_val & 0x0F))         # Lower 4 bits
        cdef uint8_t rb = clamp_12(<uint8_t>((byte1_val >> 4) & 0x0F))  # Upper 4 bits
        
        # Parse immediate lengths from second byte  
        cdef uint32_t lx = clamp_4(<uint8_t>(byte2_val & 0x07))          # Lower 3 bits
        cdef uint32_t ly = clamp_4(<uint8_t>((byte2_val >> 3) & 0x07))   # Next 3 bits
        
        # Clamp ly based on available space
        ly = clamp_4_max0(<int8_t>(int(skip_index) - lx - 2))
        
        # Extract first immediate value using pointer arithmetic
        cdef uint64_t vx = 0
        cdef uint32_t i
        cdef uint32_t start_x = program_counter + 3
        if lx > 0:
            for i in range(lx):
                vx |= (<uint64_t>zeta_ptr[start_x + i]) << (8 * i)
            vx = <uint64_t>chi(<uint64_t>vx, <uint8_t>lx)
        
        # Extract second immediate value using pointer arithmetic
        cdef uint64_t vy = 0
        cdef uint32_t start_y = start_x + lx
        if ly > 0:
            for i in range(ly):
                vy |= (<uint64_t>zeta_ptr[start_y + i]) << (8 * i)
            vy = <uint64_t>chi(<uint64_t>vy, <uint8_t>ly)
        
        # Return InstructionProps struct
        cdef InstructionProps props
        props.vx = vx
        props.vy = vy
        props.ra = ra
        props.rb = rb
        props.rd = 0  # Not used in this instruction type
        
        return props

    cpdef dict get_table(self):
        """Return the instruction table mapping opcodes to their handlers."""
        return TABLE

# Prebuilt table (opcode -> CyTableEntry)
cdef dict TABLE = {}
cdef CyTableEntry _e
_e = CyTableEntry(); _e.fn = load_imm_jump_ind_fn; _e.gas_cost = 1; _e.is_terminating = True; TABLE[180] = _e


