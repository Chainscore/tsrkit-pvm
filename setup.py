from setuptools import setup, find_packages

if __name__ == "__main__":
    from mypyc.build import mypycify
    from pathlib import Path
    
    print("MyPyC compilation requested...")
    
    # Get current directory
    current_dir = Path(__file__).parent
    
    # List all Python files to compile 
    python_files = []
    
    target_files = [
        "tsrkit_pvm/common/utils.py",
        "tsrkit_pvm/common/status.py",
        "tsrkit_pvm/common/constants.py",
        "tsrkit_pvm/core/code.py",
        "tsrkit_pvm/core/mapper.py",
        "tsrkit_pvm/interpreter/pvm.py",
        "tsrkit_pvm/interpreter/program.py",
        "tsrkit_pvm/interpreter/memory.py",
        "tsrkit_pvm/interpreter/instructions/tables/wo_args.py",
        "tsrkit_pvm/interpreter/instructions/tables/i_imm.py",
        "tsrkit_pvm/interpreter/instructions/tables/i_offset.py",
        "tsrkit_pvm/interpreter/instructions/tables/i_reg_i_ewimm.py",
        "tsrkit_pvm/interpreter/instructions/tables/i_reg_i_imm.py",
        "tsrkit_pvm/interpreter/instructions/tables/i_reg_i_imm_i_offset.py",
        "tsrkit_pvm/interpreter/instructions/tables/ii_imm.py",
        "tsrkit_pvm/interpreter/instructions/tables/ii_reg.py",
        "tsrkit_pvm/interpreter/instructions/tables/ii_reg_i_imm.py",
        "tsrkit_pvm/interpreter/instructions/tables/ii_reg_i_offset.py",
        "tsrkit_pvm/interpreter/instructions/tables/ii_reg_ii_imm.py",
        "tsrkit_pvm/interpreter/instructions/tables/iii_reg.py",
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
    
    print(f"\nCompilation summary: {compiled_count} succeeded, {failed_count} failed")
    
    setup(
        name="tsrkit_pvm",
        packages=find_packages(),
        ext_modules=ext_modules,
        zip_safe=False,
    )