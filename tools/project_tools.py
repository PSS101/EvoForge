try:
    from crewai.tools import tool
except Exception:
    # Fallback no-op decorator when crewai is not installed — allows local execution without agent tooling
    def tool(name=None):
        def _decorator(fn):
            return fn
        return _decorator
import os
from tools.file_tools import read_file, write_file, parse_python_ast
from tools.build_tools import compile_project as _compile_project, generate_makefile as _generate_makefile, run_c_tests as _run_c_tests, analyze_c_bugs as _analyze_c_bugs, debug_c_project as _debug_c_project
from tools.language_tools import detect_language, save_project_language as _save_project_language, load_project_language as _load_project_language

project_base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

@tool("read_project_file")
def read_project_file(file_path: str) -> str:
    """Reads the contents of any file in the workspace or project directory."""
    # Ensure file_path is absolute or relative to workspace root
    if not os.path.isabs(file_path):
        file_path = os.path.join(project_base_dir, file_path)
    return read_file(file_path)

@tool("write_project_file")
def write_project_file(file_path: str, content: str) -> str:
    """Writes content to a file in the workspace or project directory. Automatically creates parent directories."""
    if not os.path.isabs(file_path):
        file_path = os.path.join(project_base_dir, file_path)
    write_file(file_path, content)
    return f"Successfully wrote content to {file_path}"

@tool("list_project_files")
def list_project_files(dir_path: str) -> str:
    """Lists files and directories recursively in a given directory path."""
    if not os.path.isabs(dir_path):
        dir_path = os.path.join(project_base_dir, dir_path)
    if not os.path.exists(dir_path):
        return f"Directory {dir_path} does not exist."
    
    files_list = []
    for root, dirs, files in os.walk(dir_path):
        # Skip virtual environments or cache folders
        if any(ignored in root for ignored in [".venv", "__pycache__", ".git", ".pytest_cache"]):
            continue
        for file in files:
            rel_path = os.path.relpath(os.path.join(root, file), project_base_dir)
            files_list.append(rel_path)
    return "\n".join(files_list) if files_list else "No files found."

@tool("analyze_python_ast")
def analyze_python_ast(file_path: str) -> str:
    """Parses a Python file and returns classes, methods, and functions with their signatures."""
    if not os.path.isabs(file_path):
        file_path = os.path.join(project_base_dir, file_path)
    res = parse_python_ast(file_path)
    return str(res)

@tool("detect_project_language")
def detect_project_language(prompt: str) -> str:
    """Detect the intended project language from a user prompt."""
    return detect_language(prompt)

@tool("save_project_language")
def save_project_language(project_dir: str, language: str) -> str:
    """Persist the project language to a hidden metadata file."""
    if not os.path.isabs(project_dir):
        project_dir = os.path.join(project_base_dir, project_dir)
    _save_project_language(project_dir, language)
    return f"Saved project language '{language}' to {project_dir}"

@tool("load_project_language")
def load_project_language(project_dir: str) -> str:
    """Load the persisted project language or infer it from source files."""
    if not os.path.isabs(project_dir):
        project_dir = os.path.join(project_base_dir, project_dir)
    return _load_project_language(project_dir)

@tool("generate_makefile")
def generate_makefile(project_dir: str, project_name: str, language: str) -> str:
    """Generate an auto-generated Makefile for a C/C++ project."""
    if not os.path.isabs(project_dir):
        project_dir = os.path.join(project_base_dir, project_dir)
    return _generate_makefile(project_dir, project_name, language)

@tool("compile_project")
def compile_project(project_dir: str) -> str:
    """Compile a C/C++ project using its Makefile."""
    if not os.path.isabs(project_dir):
        project_dir = os.path.join(project_base_dir, project_dir)
    success, output = _compile_project(project_dir)
    return output if success else f"ERROR: {output}"

@tool("run_c_tests")
def run_c_tests(project_dir: str) -> str:
    """Compile and run C/C++ tests using make test."""
    if not os.path.isabs(project_dir):
        project_dir = os.path.join(project_base_dir, project_dir)
    success, output = _run_c_tests(project_dir)
    return output if success else f"ERROR: {output}"

@tool("analyze_c_bugs")
def analyze_c_bugs(project_dir: str) -> str:
    """Perform static bug checks on C/C++ source and header files."""
    if not os.path.isabs(project_dir):
        project_dir = os.path.join(project_base_dir, project_dir)
    issues = _analyze_c_bugs(project_dir)
    return str(issues) if issues else "No C/C++ static bug issues detected."

@tool("debug_c_project")
def debug_c_project(project_dir: str) -> str:
    """Run automated debugging and compilation fix pass on a C/C++ project."""
    if not os.path.isabs(project_dir):
        project_dir = os.path.join(project_base_dir, project_dir)
    success, output = _debug_c_project(project_dir)
    return output if success else f"DEBUG ERROR: {output}"

@tool("get_c_cpp_functions")
def get_c_cpp_functions(project_dir: str) -> str:
    """Extract and return core C/C++ function signatures and metadata from a C/C++ project directory."""
    if not os.path.isabs(project_dir):
        project_dir = os.path.join(project_base_dir, project_dir)
    from tools.static_analysis import extract_and_store_c_cpp_functions
    _, formatted_ref = extract_and_store_c_cpp_functions(project_dir)
    return formatted_ref


