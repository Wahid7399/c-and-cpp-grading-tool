from glob import glob
import os
import subprocess
import sys

def shell_run(cmd):
    print(f"→ Running: {cmd}")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"Command failed: {cmd}")
        sys.exit(1)

def find_entry_point(_dir):
    cpp_files = glob(os.path.join(_dir, "**", "*.cpp"), recursive=True)
    main_file_path = None
    for file in cpp_files:
        with open(file, 'r') as f:
            content = f.read()
            content = ' '.join(content.split())
            if 'int main(' in content or 'void main(' in content:
                main_file_path = file
                break
    return main_file_path
