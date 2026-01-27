# cython: cdivision=True, boundscheck=False, wraparound=False, nonecheck=False
# cython: initializedcheck=False, overflowcheck=False
# cython: profile=False, linetrace=False
# cython: language_level=3, infer_types=True, optimize.unpack_method_calls=True


from libc.stdint cimport uint32_t, uint64_t, uint8_t
from ...cy_status cimport PvmExit, PVM_PANIC, CONTINUE
from ..cy_table cimport CyTable, CyTableEntry, instr_fn_t, InstructionProps
from ...cy_memory cimport CyMemory
from ...cy_program cimport CyProgram


cdef inline uint32_t trap_fn(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """
    OPC0: Trap - Raise panic error.
    All arguments unused for this instruction.
    """
    # Trap instruction causes panic and terminates execution
    raise PvmExit(PVM_PANIC)

cdef inline uint32_t fallthrough_fn(CyProgram program, uint64_t *registers, CyMemory memory, uint32_t counter, uint64_t vx, uint64_t vy, uint8_t ra, uint8_t rb, uint8_t rd):
    """
    OPC1: Fallthrough - Continue execution.
    All arguments unused for this instruction.
    """
    return <uint32_t>0xFFFFFFFF

cdef class InstructionsWoArgs(CyTable):
    """
    Cython optimized instruction table for instructions without arguments.
    """
    
    cdef InstructionProps get_props(self, uint32_t program_counter, CyProgram program, uint32_t skip_index):
        """
        No arguments to extract for these instructions.
        Returns InstructionProps struct with all fields as 0.
        """
        cdef InstructionProps props
        props.vx = 0
        props.vy = 0
        props.ra = 0
        props.rb = 0
        props.rd = 0
        return props
    
    cpdef dict get_table(self):
        """Return the instruction table mapping opcodes to their handlers."""
        return TABLE

cdef dict TABLE = {}
cdef CyTableEntry _e
_e = CyTableEntry(); _e.fn = trap_fn; _e.gas_cost = 1; _e.is_terminating = True; TABLE[0] = _e
_e = CyTableEntry(); _e.fn = fallthrough_fn; _e.gas_cost = 1; _e.is_terminating = True; TABLE[1] = _e


