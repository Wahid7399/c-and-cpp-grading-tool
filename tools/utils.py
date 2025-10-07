import itertools
from zipfile import ZipFile
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

def find_entry_points(_dir):
    cpp_files = list(itertools.chain.from_iterable(
        glob(os.path.join(_dir, "**", ext), recursive=True)
        for ext in ("*.c", "*.cpp")
    ))
    main_file_paths = []
    for file in cpp_files:
        if not os.path.isfile(file):
            continue
        try:
            with open(file, 'r') as f:
                content = f.read()
                content = ' '.join(content.split())
                if 'int main(' in content or 'void main(' in content:
                    main_file_paths.append(file)
        except Exception as e:
            print(f"⚠️ Error reading {file}: {e}")
            continue
    return main_file_paths

def find_entry_point(_dir):
    return find_entry_points(_dir)[0] if find_entry_points(_dir) else None

def create_single_entry_point(_dir, entry_point="main.cpp"):
    cpp_files = list(itertools.chain.from_iterable(
        glob(os.path.join(_dir, "**", ext), recursive=True)
        for ext in ("*.c", "*.cpp")
    ))
    if not cpp_files:
        return None
    includes = set()
    code = {}
    # Remove main function from the file, keep includes separately
    for file_path in cpp_files:
        if not os.path.isfile(file_path):
            continue
        try:
            with open(file_path, 'r') as f:
                lines = f.readlines()
        except Exception as e:
            print(f"⚠️ Error reading {file_path}: {e}")
            continue
        for line in lines:
            line = ' '.join(line.split())
            if line.startswith('#include'):
                includes.add(line)
        # replace int isTrivialOutput with int isTrivialOutput_
        lines = [line.replace('int isTrivialOutput', 'int isTrivialOutput_') for line in lines]
        # Remove main function
        main_start = -1
        main_end = -1
        brace_count = 0
        for i, line in enumerate(lines):
            line = ' '.join(line.split())
            if 'int main(' in line or 'void main(' in line:
                main_start = i
                brace_count += line.count('{') - line.count('}')
                if brace_count == 0 and line.count('{') > 0:
                    main_end = i
                    break            
            elif main_start != -1:
                brace_count += line.count('{') - line.count('}')
                if brace_count == 0:
                    main_end = i
                    break
        if main_start != -1 and main_end != -1:
            del lines[main_start:main_end + 1]
        code[file_path] = ''.join(lines)    
    # Create a new main.c or main.cpp file with all main functions
    with open(os.path.join(_dir, entry_point), 'w') as f:
        for include in includes:
            f.write(f"{include}\n")
        f.write("\n")
        for file_path, content in code.items():
            f.write(f"// From {file_path}\n")
            f.write(content)
            f.write("\n")
    return os.path.join(_dir, entry_point)

def remove_single_entry_point(_dir, entry_point="main.cpp"):
    try:
        # pass
        os.remove(os.path.join(_dir, entry_point))
    except FileNotFoundError:
        pass

def create_compiler_command(settings, extra_args=None):
    command_list = []
    if settings.language == "cpp":
        command_list.append("g++")
    elif settings.language == "c":
        command_list.append("gcc")
    else:
        raise ValueError(f"Unsupported language: {settings.language}")
    if settings.version:
        if extra_args is None:
            extra_args = []
        extra_args.append(f"-std={settings.version}")
    if extra_args:
        command_list.extend(extra_args)
    return command_list

def transpose_dict(data: dict) -> dict:
    """
    Transpose a dictionary of dictionaries.
    """
    transposed = {}
    for roll, metrics in data.items():
        for metric, value in metrics.items():
            transposed.setdefault(metric, {})[roll] = value
    return {
        metric: dict(sorted(rolls.items()))
        for metric, rolls in sorted(transposed.items())
    }

def get_latest_in_zip(zip_path):
    with ZipFile(zip_path, 'r') as zf:
        return max(info.date_time for info in zf.infolist())
