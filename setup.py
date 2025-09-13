import os
from setuptools import setup, find_packages

if __name__ == "__main__":
    # Check if Cython mode is requested
    PVM_MODE = os.environ.get("PVM_MODE", "mypyc").lower()
    print(f"Building with PVM_MODE={PVM_MODE}")
    
    if PVM_MODE == "cython":
        # Use Cython compilation
        try:
            from Cython.Build import cythonize
            print("Cython compilation requested...")
            
            compiler_directives = {
                'boundscheck': False,
                'wraparound': False, 
                'nonecheck': False,
                'cdivision': True,
                'language_level': 3,
                'profile': False,
                'embedsignature': True,
            }
            
            cython_files = [
                "tsrkit_pvm/cpvm/cy_memory.pyx",
                "tsrkit_pvm/cpvm/instructions/tables/wo_args.pyx",
                "tsrkit_pvm/cpvm/instructions/tables/i_imm.pyx",
                "tsrkit_pvm/cpvm/instructions/tables/ii_reg.pyx",
                "tsrkit_pvm/cpvm/instructions/tables/iii_reg.pyx",
                "tsrkit_pvm/cpvm/instructions/tables/i_offset.pyx",
                "tsrkit_pvm/cpvm/instructions/tables/ii_imm.pyx",
                "tsrkit_pvm/cpvm/instructions/tables/i_reg_i_imm.pyx",
                "tsrkit_pvm/cpvm/instructions/tables/i_reg_i_ewimm.pyx",
                "tsrkit_pvm/cpvm/instructions/tables/i_reg_ii_imm.pyx",
                "tsrkit_pvm/cpvm/instructions/tables/ii_reg_i_offset.pyx",
                "tsrkit_pvm/cpvm/instructions/tables/i_reg_i_imm_i_offset.pyx",
                "tsrkit_pvm/cpvm/instructions/tables/ii_reg_ii_imm.pyx",
                "tsrkit_pvm/cpvm/instructions/tables/ii_reg_i_imm.pyx",
                "tsrkit_pvm/cpvm/mapper.pyx",
                "tsrkit_pvm/cpvm/cy_pvm.pyx",
            ]
            ext_modules = cythonize(
                cython_files,
                compiler_directives=compiler_directives,
                annotate=os.environ.get("CYTHON_ANNOTATE", "false").lower() == "true",
                language_level=3,
            )
            print(f"✓ Successfully compiled {len(cython_files)} Cython files")
        except ImportError:
            print("❌ Cython not available, falling back to MyPyC")
            PVM_MODE = "mypyc"
    
    if PVM_MODE != "cython":
        # Use existing MyPyC compilation
        from mypyc.build import mypycify
        from pathlib import Path
        
        print("MyPyC compilation requested...")
        
        target_files = [
            # "tsrkit_pvm/common/utils.py",
            # "tsrkit_pvm/common/status.py",
            # "tsrkit_pvm/common/constants.py",
            # "tsrkit_pvm/core/code.py",
            # "tsrkit_pvm/core/mapper.py",
            # "tsrkit_pvm/interpreter/pvm.py",
            # "tsrkit_pvm/interpreter/program.py",
            # "tsrkit_pvm/interpreter/memory.py",
            # "tsrkit_pvm/interpreter/instructions/tables/wo_args.py",
            # "tsrkit_pvm/interpreter/instructions/tables/i_imm.py",
            # "tsrkit_pvm/interpreter/instructions/tables/i_offset.py",
            # "tsrkit_pvm/interpreter/instructions/tables/i_reg_i_ewimm.py",
            # "tsrkit_pvm/interpreter/instructions/tables/i_reg_i_imm.py",
            # "tsrkit_pvm/interpreter/instructions/tables/i_reg_ii_imm.py",
            # "tsrkit_pvm/interpreter/instructions/tables/i_reg_i_imm_i_offset.py",
            # "tsrkit_pvm/interpreter/instructions/tables/ii_imm.py",
            # "tsrkit_pvm/interpreter/instructions/tables/ii_reg.py",
            # "tsrkit_pvm/interpreter/instructions/tables/ii_reg_i_imm.py",
            # "tsrkit_pvm/interpreter/instructions/tables/ii_reg_i_offset.py",
            # "tsrkit_pvm/interpreter/instructions/tables/ii_reg_ii_imm.py",
            # "tsrkit_pvm/interpreter/instructions/tables/iii_reg.py",
        ]
        
        # Try MyPyC compilation
        ext_modules = []
        compiled_count = 0
        failed_count = 0
        
        for py_file in target_files:
            try:
                print(f"Compiling {py_file}...")
                mypycified = mypycify([py_file], opt_level="3")
                if mypycified:
                    ext_modules.extend(mypycified)
                    compiled_count += 1
                    print(f"✓ Successfully compiled {py_file}")
                else:
                    failed_count += 1
                    print(f"✗ Failed to compile {py_file}")
            except Exception as e:
                failed_count += 1
                print(f"✗ Error compiling {py_file}: {e}")
        
        print(f"\nMyPyC compilation summary: {compiled_count} succeeded, {failed_count} failed")
    
    setup(
        name="tsrkit_pvm",
        packages=find_packages(),
        ext_modules=ext_modules,
        zip_safe=False,
    )