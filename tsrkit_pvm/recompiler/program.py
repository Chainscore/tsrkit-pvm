from typing import Dict, Tuple, Optional, Any
import bisect  # Import once at module level for performance
from tsrkit_pvm.core.program_base import Program
from tsrkit_pvm.recompiler.assembler.context import AssemblerContext
from tsrkit_pvm.recompiler.vm_context import gas_offset
from .assembler.inst_map import inst_map

# Import tsrkit_asm with type: ignore for MyPyC
from tsrkit_asm import (  # type: ignore
    Condition,
    ImmKind,
    MemOp,
    Operands,
    PyAssembler,
    Reg,
    RegMem,
    RegSize,
)


class REC_Program(Program):
    """Recompiler program blob for performant PVM execution."""

    # Assembled Machine Code
    msn_code: Optional[bytes]
    # Index to halt label  
    halt_offset: Optional[int]
    # Index to panic label
    panic_offset: Optional[int]    # Optimized lookup structures for performance-critical operations
    # Fast bidirectional mapping between PVM and machine code addresses
    _pvm_to_msn: list[int]           # Direct array: pvm_offset -> msn_offset
    _msn_to_pvm_map: dict[int, int]  # Hash map: msn_offset -> pvm_offset (sparse)
    _msn_breakpoints: list[int]      # Sorted list of valid msn addresses for binary search
    
    # Pre-computed data for O(1) runtime lookups
    _skip_cache: list[int]           # Pre-computed skip values
    _valid_pvm_offsets: set[int]     # Set of valid PVM instruction starts
    
    # Basic block information (keeping for compatibility)
    basic_blocks: list[int]
    bitmask_index: list[int]

    is_recompiler = True

    def __post_init__(self) -> None:
        """
        Optimized initialization with single-pass data structure building.
        
        This replaces the original multi-pass approach with a single iteration
        that builds all required lookup structures simultaneously.
        """
        super().__post_init__()
        
        # Single-pass initialization of all lookup structures
        self._build_optimized_structures()

    def _build_optimized_structures(self) -> None:
        """
        Build all lookup structures in a single pass for maximum efficiency.
        
        Replaces multiple separate loops with one efficient pass.
        """
        len_i_set = len(self.instruction_set)
        offset_bitmask = self.offset_bitmask  # Cache the attribute access
        extended_bitmask = self._extended_bitmask  # Cache the attribute access
        
        # Pre-allocate all structures with exact sizes when possible
        self._skip_cache = [0] * len_i_set
        self._valid_pvm_offsets = set()
        basic_blocks = [0]
        bitmask_index = [0] * len_i_set  # Pre-allocate full size
        pvm_to_msn_builder = []  # Will become _pvm_to_msn
        
        # Count valid instructions first for better allocation
        valid_count = sum(offset_bitmask)
        pvm_to_msn_builder = [0] * valid_count  # Pre-allocate exact size
        
        # Single pass through instruction set
        bb_counter = 0
        last_valid_offset = len_i_set
        
        # Process in reverse for skip calculation efficiency - vectorized approach
        for i in range(len_i_set - 1, -1, -1):
            # Calculate skip value (distance to next valid instruction)
            if i < len_i_set - 1 and extended_bitmask[i + 1]:
                last_valid_offset = i + 1
            self._skip_cache[i] = min(24, last_valid_offset - i - 1) if last_valid_offset < len_i_set else 0
        
        # Forward pass for other structures - avoid repeated attribute lookups
        inst_set = self.instruction_set  # Cache attribute
        dispatch_table = inst_map._dispatch_table  # Cache frequently accessed data
        
        for i in range(len_i_set):
            if offset_bitmask[i]:
                self._valid_pvm_offsets.add(i)
                bitmask_index[i] = bb_counter
                bb_counter += 1
                
                # Check for basic block boundaries - optimized condition checking
                if (i < 256 and 
                    dispatch_table[inst_set[i]] is not None and
                    inst_map.is_terminating(inst_set[i])):
                    next_block = i + 1 + self._skip_cache[i]
                    if next_block < len_i_set:
                        basic_blocks.append(next_block)
            else:
                bitmask_index[i] = -1
        
        # Store computed structures
        self.basic_blocks = basic_blocks
        self.bitmask_index = bitmask_index
        self._pvm_to_msn = pvm_to_msn_builder
        
        # Initialize assembly-related structures
        self.msn_code = None
        self.panic_offset = None
        self.halt_offset = None
        self._msn_to_pvm_map = {}
        self._msn_breakpoints = []

    def assemble(self, gas_enabled: bool = True, logger: Optional[Any] = None) -> Tuple[bytes, dict, int, int]:
        """
        Optimized assembly with efficient lookup table construction.
        """
        asm = PyAssembler()

        # Cache frequently accessed data to reduce attribute lookups
        instruction_set = self.instruction_set
        offset_bitmask = self.offset_bitmask
        jump_table_len = len(self.jump_table)
        
        # Create labels for all basic blocks (jump targets) - use dict comprehension
        labels = {i: asm.forward_declare_label() 
                 for i in range(len(instruction_set)) if offset_bitmask[i]}

        halt_label = asm.forward_declare_label()
        panic_label = asm.forward_declare_label()
        
        # Create context wrapper
        asm_ctx = AssemblerContext(asm, labels, halt_label, panic_label, jump_table_len)

        # Build optimized mapping during assembly
        counter = 0
        pvm_index = 0
        len_inst_set = len(instruction_set)
        
        # Cache frequently accessed objects
        dispatch_table = inst_map._dispatch_table
        pvm_to_msn = self._pvm_to_msn
        msn_to_pvm_map = self._msn_to_pvm_map
        
        while counter < len_inst_set:
            if offset_bitmask[counter]:  # Only process actual opcodes
                # Define label
                asm.define_label(labels[counter])

                # Record machine code address for this PVM instruction
                msn_addr = asm.current_address()
                pvm_to_msn[pvm_index] = msn_addr
                msn_to_pvm_map[msn_addr] = counter
                pvm_index += 1

                opcode = instruction_set[counter]
                handler = dispatch_table[opcode]
                if handler is None:
                    raise RuntimeError(f"No handler found for opcode {opcode}")
                opdata = handler.op_data
                if logger:
                    logger.debug(
                        f"📍 {counter} \t Processing opcode \t {opdata} ({opcode})"
                    )

                if gas_enabled:
                    gas = opdata.gas
                    # --- Gas Computation --- #
                    x61mov_imm = -gas_offset + 0x61
                    asm.sub(
                        Operands.RegMem_Imm(RegMem.Reg(Reg.r15), ImmKind.I64(x61mov_imm))
                    )
                    asm.sub(
                        Operands.RegMem_Imm(
                            RegMem.Mem(
                                MemOp.BaseOffset(
                                    seg=None, size=RegSize.R64, base=Reg.r15, offset=0x61
                                )
                            ),
                            ImmKind.I32(gas),
                        )
                    )
                    asm.jcc_rel32(Condition.Sign, -2)
                    asm.add(
                        Operands.RegMem_Imm(RegMem.Reg(Reg.r15), ImmKind.I64(x61mov_imm))
                    )
                    
                # Process the instruction
                _, gas = inst_map.process_instruction(self, counter, asm_ctx)
            counter += 1

        # If normally returned, then its a panic
        asm.define_label(panic_label)
        panic_addr = asm.current_address()
        asm.ret()

        # Add a block for HALT exit
        asm.define_label(halt_label)
        halt_addr = asm.current_address()
        # Jump to memory, which is non-executable and will throw seg fault
        asm.ud2()

        if logger:
            logger.debug(f"🧩 Assembled program size: {asm.len()} ")

        # Finalize and build sorted breakpoints for efficient binary search
        self.msn_code = asm.finalize()
        self.panic_offset = panic_addr
        self.halt_offset = halt_addr
        # Use sorted() on dict.keys() for better performance with large datasets
        self._msn_breakpoints = sorted(msn_to_pvm_map.keys())

        return self.msn_code, msn_to_pvm_map, panic_addr, halt_addr

    def msn_to_pvm_index(self, msn_offset: int) -> int:
        """
        Machine code to PVM index conversion using binary search.
        O(log n) binary search with direct hash map lookup. 
        """
        # Fast path: direct lookup if exact match
        direct_result = self._msn_to_pvm_map.get(msn_offset)
        if direct_result is not None:
            return direct_result
        
        # Binary search to find the closest valid instruction start
        breakpoints = self._msn_breakpoints
        if not breakpoints or msn_offset < breakpoints[0]:
            return 0
            
        # Use cached bisect module for maximum performance
        pos = bisect.bisect_right(breakpoints, msn_offset)
        if pos == 0:
            return 0
            
        # Get the PVM index for the found machine address
        closest_msn = breakpoints[pos - 1]
        return self._msn_to_pvm_map[closest_msn]

    def pvm_to_msn_index(self, pvm_offset: int) -> int:
        """
        PVM to machine code index conversion using direct array access.
        
        O(1) direct array lookup.
        """
        # Validate input
        if pvm_offset not in self._valid_pvm_offsets:
            # Find the closest valid offset (fallback for edge cases)
            for i in range(pvm_offset, -1, -1):
                if i in self._valid_pvm_offsets:
                    pvm_offset = i
                    break
            else:
                return 0
        
        # Get the bitmap index for this PVM offset
        bb_index = self.bitmask_index[pvm_offset]
        if bb_index == -1:
            # This shouldn't happen with valid offsets, but handle gracefully
            return self.pvm_to_msn_index(pvm_offset - 1) if pvm_offset > 0 else 0
        
        # Direct O(1) lookup
        return self._pvm_to_msn[bb_index]

    def skip(self, pc: int) -> int:
        """
        O(1) skip value lookup using pre-computed cache.
        
        Optimized from runtime computation to direct array access.
        """
        return self._skip_cache[pc] if pc < len(self._skip_cache) else 0
