import os
import platform
import sys
from setuptools import setup, find_packages, Extension

def should_build_recompiler():
    """Determine if recompiler should be built on this platform."""
    is_linux = sys.platform.startswith('linux')
    is_x86_64 = platform.machine() in ('x86_64', 'AMD64')
    return is_linux and is_x86_64

if __name__ == "__main__":
    # Check if Cython mode is requested
    PVM_BUILD_MODE = os.environ.get("PVM_BUILD_MODE", "plain").lower()
    print(f"Building with PVM_BUILD_MODE={PVM_BUILD_MODE}")
    print(f"Platform: {sys.platform}, Architecture: {platform.machine()}")

    if should_build_recompiler():
        print(f"[+] Runtime modes available: PVM_MODE=interpreter (Cython) or PVM_MODE=recompiler")
    else:
        print(f"[+] Runtime modes available: PVM_MODE=interpreter (Cython only, recompiler requires Linux x86_64)")

    ext_modules = []  # Default to no compiled extensions

    # Build recompiler's segwrap C extension only on Linux x86_64
    if should_build_recompiler():
        segwrap_ext = Extension(
            'tsrkit_pvm.recompiler.segwrap._segwrap',
            sources=['tsrkit_pvm/recompiler/segwrap/segwrap.c'],
            extra_compile_args=['-O3', '-Wall'],
        )
        ext_modules.append(segwrap_ext)
        print("[+] Building recompiler segwrap extension")
    else:
        print("[-] Skipping recompiler segwrap extension (Linux x86_64 only)")

    if PVM_BUILD_MODE == "cython":
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
                "tsrkit_pvm/cpvm/cy_status.pyx",
                "tsrkit_pvm/cpvm/cy_program.pyx",
                "tsrkit_pvm/cpvm/cy_block.pyx",
                "tsrkit_pvm/cpvm/cy_memory.pyx",
                "tsrkit_pvm/cpvm/cy_utils.pyx",
                "tsrkit_pvm/cpvm/instructions/cy_table.pyx",
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
            cython_extensions = cythonize(
                cython_files,
                compiler_directives=compiler_directives,
                annotate=os.environ.get("CYTHON_ANNOTATE", "false").lower() == "true",
                language_level=3,
            )
            ext_modules.extend(cython_extensions)
            print(f"[+] Successfully compiled {len(cython_files)} Cython files")
            if should_build_recompiler():
                print(f"[+] Total extensions: {len(ext_modules)} (Cython interpreter + recompiler segwrap)")
        except ImportError as e:
            print(f"❌ Cython not available: {e}, falling back to MyPyC")
            PVM_BUILD_MODE = "mypyc"

    if PVM_BUILD_MODE == "mypyc":
        # Use existing MyPyC compilation
        from mypyc.build import mypycify
        from pathlib import Path
        import glob
        
        print("MyPyC compilation requested...")
        
        # Collect targets
        core_files = [
            "tsrkit_pvm/common/utils.py",
            "tsrkit_pvm/common/status.py",
            "tsrkit_pvm/common/constants.py",
            # "tsrkit_pvm/core/code.py",
            "tsrkit_pvm/core/opcode.py",
        ]
        recompiler_files = [
            *glob.glob("tsrkit_pvm/recompiler/assembler/tables/*.py", recursive=True),
            "tsrkit_pvm/recompiler/assembler/inst_map.py",
            "tsrkit_pvm/recompiler/assembler/utils.py",
            "tsrkit_pvm/recompiler/memory.py",
            "tsrkit_pvm/recompiler/program.py",
            "tsrkit_pvm/recompiler/vm_context.py",
            "tsrkit_pvm/recompiler/pvm.py",
            *glob.glob("tsrkit_pvm/interpreter/**/*.py", recursive=True)
        ]
        recompiler_files = [f for f in recompiler_files if not f.endswith("__init__.py")]
        target_files = core_files + recompiler_files

        try:
            # Compile each file individually to avoid a top-level hashed __mypyc support module
            mypyc_modules = []
            compiled_count = 0
            failed_count = 0
            for py_file in target_files:
                try:
                    print(f"Compiling {py_file}...")
                    mods = mypycify([py_file], opt_level="3")
                    if mods:
                        mypyc_modules.extend(mods)
                        compiled_count += 1
                        print(f"[+] Successfully compiled {py_file}")
                    else:
                        failed_count += 1
                        print(f"[!] Failed to compile {py_file}")
                except Exception as ce:
                    failed_count += 1
                    print(f"[!] Error compiling {py_file}: {ce}")
            ext_modules.extend(mypyc_modules)
            print(f"\nMyPyC compilation summary: {compiled_count} succeeded, {failed_count} failed")
            if should_build_recompiler():
                print(f"[+] Total extensions: {len(ext_modules)} (MyPyC + recompiler segwrap)")
        except Exception as e:
            print(f"[!] Failed to configure MyPyC: {e}")
    
    setup(
        name="tsrkit_pvm",
        packages=find_packages(),
        ext_modules=ext_modules,
        zip_safe=False,
    )