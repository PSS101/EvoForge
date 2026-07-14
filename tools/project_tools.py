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
