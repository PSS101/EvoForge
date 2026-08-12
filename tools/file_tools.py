import hashlib
import json
import os
import ast

def calculate_hash(file_path):
    """Calculate the SHA-256 hash of a file's content."""
    if not os.path.exists(file_path):
        return ""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        buf = f.read()
        hasher.update(buf)
    return hasher.hexdigest()


def calculate_content_hash(content: str) -> str:
    """Calculate the SHA-256 hash of a string content."""
    hasher = hashlib.sha256()
    hasher.update(content.encode("utf-8"))
    return hasher.hexdigest()


def save_json(file_path: str, data: object) -> None:
    """Write JSON serializable data to a file."""
    parent_dir = os.path.dirname(file_path)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
def read_file(file_path):
    """Read contents of a file safely."""
    if not os.path.exists(file_path):
        return ""
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()

def write_file(file_path, content):
    """Write contents to a file, ensuring directories exist."""
    parent_dir = os.path.dirname(file_path)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

def parse_python_ast(file_path):
    """
    Parse a Python file using AST and return high-level details
    about classes, methods, and functions.
    """
    if not os.path.exists(file_path):
        return {}
    
    code = read_file(file_path)
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return {"error": f"Syntax error: {e}"}

    summary = {
        "classes": [],
        "functions": []
    }

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            class_info = {
                "name": node.name,
                "methods": [],
                "docstring": ast.get_docstring(node) or ""
            }
            for subnode in node.body:
                if isinstance(subnode, ast.FunctionDef):
                    args = [arg.arg for arg in subnode.args.args]
                    class_info["methods"].append({
                        "name": subnode.name,
                        "args": args,
                        "docstring": ast.get_docstring(subnode) or ""
                    })
            summary["classes"].append(class_info)
        elif isinstance(node, ast.FunctionDef):
            args = [arg.arg for arg in node.args.args]
            summary["functions"].append({
                "name": node.name,
                "args": args,
                "docstring": ast.get_docstring(node) or ""
            })

    return summary
