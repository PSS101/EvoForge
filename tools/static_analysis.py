import ast
import json
import os
import re
from collections import defaultdict
from typing import Any, Dict, List

API_MODULES = {
    "requests", "httpx", "urllib", "flask", "fastapi", "django", "bottle", "aiohttp", "graphene", "socketio"
}
DB_MODULES = {
    "sqlite3", "sqlalchemy", "psycopg2", "pymongo", "mysql.connector", "pymysql", "redis", "tinydb"
}
SQL_KEYWORDS = {"select", "insert", "update", "delete", "create", "drop", "alter", "from", "where", "join"}


def _safe_parse_python(code: str) -> Any:
    try:
        return ast.parse(code)
    except SyntaxError:
        return None


def _get_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{_get_name(node.value)}.{node.attr}"
    return ""


def _collect_imports(tree: ast.AST) -> List[str]:
    imports: List[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module:
                imports.append(module)
    return sorted(set(imports))


def _collect_api_dependencies(imports: List[str], code: str) -> List[str]:
    found = set()
    for name in imports:
        root = name.split(".")[0]
        if root in API_MODULES or root in DB_MODULES:
            found.add(root)
    for keyword in SQL_KEYWORDS:
        if re.search(rf"\b{keyword}\b", code, re.IGNORECASE):
            found.add("sql")
            break
    return sorted(found)


def _collect_functions_and_classes(tree: ast.AST) -> Dict[str, List[Dict[str, Any]]]:
    result = {"functions": [], "classes": []}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            result["functions"].append({
                "name": node.name,
                "args": [arg.arg for arg in node.args.args],
                "docstring": ast.get_docstring(node) or ""
            })
        elif isinstance(node, ast.ClassDef):
            methods = []
            for sub in node.body:
                if isinstance(sub, ast.FunctionDef):
                    methods.append({
                        "name": sub.name,
                        "args": [arg.arg for arg in sub.args.args],
                        "docstring": ast.get_docstring(sub) or ""
                    })
            result["classes"].append({
                "name": node.name,
                "bases": [_get_name(base) for base in node.bases if _get_name(base)],
                "methods": methods,
                "docstring": ast.get_docstring(node) or ""
            })
    return result


def _collect_call_edges(tree: ast.AST) -> List[Dict[str, str]]:
    edges: List[Dict[str, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func_name = _get_name(node.func)
            if func_name:
                caller = "<unknown>"
                parent = getattr(node, "parent", None)
                if isinstance(parent, ast.FunctionDef):
                    caller = parent.name
                elif isinstance(parent, ast.ClassDef):
                    caller = parent.name
                edges.append({"caller": caller, "callee": func_name})
    return edges


def _annotate_parents(tree: ast.AST) -> None:
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            child.parent = node


def analyze_python_file(file_path: str, root_dir: str) -> Dict[str, Any]:
    code = ""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            code = f.read()
    except FileNotFoundError:
        return {}

    tree = _safe_parse_python(code)
    if tree is None:
        return {
            "path": os.path.relpath(file_path, root_dir),
            "error": "syntax_error"
        }

    _annotate_parents(tree)
    imports = _collect_imports(tree)
    api_dependencies = _collect_api_dependencies(imports, code)
    definitions = _collect_functions_and_classes(tree)
    call_edges = _collect_call_edges(tree)

    return {
        "path": os.path.relpath(file_path, root_dir),
        "imports": imports,
        "api_dependencies": api_dependencies,
        "definitions": definitions,
        "call_edges": call_edges,
        "source": code[:1000]
    }


def build_dependency_graph(project_dir: str) -> Dict[str, Any]:
    project_graph: Dict[str, Any] = {
        "modules": {},
        "module_imports": {},
        "api_dependencies": set(),
        "db_dependencies": set(),
        "class_dependency_graph": {},
        "function_call_graph": [],
    }
    for root, dirs, files in os.walk(project_dir):
        if any(part in root for part in [".venv", "__pycache__", ".git", ".pytest_cache"]):
            continue
        for filename in files:
            if not filename.endswith(".py"):
                continue
            file_path = os.path.join(root, filename)
            file_analysis = analyze_python_file(file_path, project_dir)
            if not file_analysis:
                continue
            rel_path = file_analysis["path"]
            project_graph["modules"][rel_path] = {
                "imports": file_analysis["imports"],
                "api_dependencies": file_analysis["api_dependencies"],
                "definitions": file_analysis["definitions"],
                "call_edges": file_analysis["call_edges"],
            }
            project_graph["module_imports"][rel_path] = file_analysis["imports"]
            for dep in file_analysis["api_dependencies"]:
                if dep == "sql":
                    project_graph["db_dependencies"].add(dep)
                else:
                    project_graph["api_dependencies"].add(dep)

            for cls in file_analysis["definitions"]["classes"]:
                project_graph["class_dependency_graph"][cls["name"]] = cls["bases"]
            project_graph["function_call_graph"].extend(file_analysis["call_edges"])

    project_graph["api_dependencies"] = sorted(project_graph["api_dependencies"])
    project_graph["db_dependencies"] = sorted(project_graph["db_dependencies"])
    return project_graph


def dependency_graph_to_json(graph: Dict[str, Any]) -> str:
    serializable = {
        "modules": graph["modules"],
        "module_imports": graph["module_imports"],
        "api_dependencies": graph["api_dependencies"],
        "db_dependencies": graph["db_dependencies"],
        "class_dependency_graph": graph["class_dependency_graph"],
        "function_call_graph": graph["function_call_graph"],
    }
    return json.dumps(serializable, indent=2)
