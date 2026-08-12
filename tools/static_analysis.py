import ast
import json
import os
import re
from collections import defaultdict
from typing import Any, Dict, List, Tuple

# C/C++ analysis is provided by build_tools (lazy import to avoid circular deps)
_C_EXTENSIONS = {'.c', '.cpp', '.cxx', '.cc', '.h', '.hpp', '.hxx'}

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
                curr = getattr(node, "parent", None)
                while curr is not None:
                    if isinstance(curr, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        caller = curr.name
                        break
                    elif isinstance(curr, ast.ClassDef):
                        caller = curr.name
                        break
                    curr = getattr(curr, "parent", None)
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
            file_path = os.path.join(root, filename)
            _, ext = os.path.splitext(filename)

            # --- Python analysis ---
            if ext == ".py":
                file_analysis = analyze_python_file(file_path, project_dir)
                if not file_analysis:
                    continue
                rel_path = file_analysis["path"]
                project_graph["modules"][rel_path] = {
                    "imports": file_analysis["imports"],
                    "api_dependencies": file_analysis["api_dependencies"],
                    "definitions": file_analysis["definitions"],
                    "call_edges": file_analysis["call_edges"],
                    "language": "python",
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

            # --- C / C++ analysis ---
            elif ext in _C_EXTENSIONS:
                try:
                    from tools.build_tools import analyze_c_file
                except ImportError:
                    continue
                file_analysis = analyze_c_file(file_path, project_dir)
                if not file_analysis:
                    continue
                rel_path = file_analysis["path"]
                project_graph["modules"][rel_path] = {
                    "imports": file_analysis.get("includes", []),
                    "api_dependencies": [],
                    "definitions": {
                        "functions": file_analysis.get("functions", []),
                        "classes": [],
                        "structs": file_analysis.get("structs", []),
                    },
                    "call_edges": [],
                    "language": file_analysis.get("language", "c"),
                }
                project_graph["module_imports"][rel_path] = file_analysis.get("includes", [])
                for fn in file_analysis.get("functions", []):
                    project_graph["function_call_graph"].append(
                        {"caller": rel_path, "callee": fn["name"]}
                    )

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


def extract_and_store_c_cpp_functions(
    project_dir: str,
    db_manager: Any = None,
    project_id: Any = None,
    reports_dir: str = None
) -> Tuple[List[Dict[str, Any]], str]:
    """
    Extract all C/C++ functions from source/header files in project_dir,
    persist them to SQLite database (c_cpp_functions table) if db_manager is provided,
    save JSON report to reports_dir (or project_dir), and return (functions_list, formatted_reference).
    """
    from tools.build_tools import analyze_c_file

    all_functions = []
    functions_by_file = defaultdict(list)

    for root, dirs, files in os.walk(project_dir):
        if any(part in root for part in [".venv", "__pycache__", ".git", ".pytest_cache"]):
            continue
        for filename in files:
            _, ext = os.path.splitext(filename)
            if ext in _C_EXTENSIONS:
                file_path = os.path.join(root, filename)
                rel_path = os.path.relpath(file_path, project_dir)
                file_analysis = analyze_c_file(file_path, project_dir)
                fns = file_analysis.get("functions", [])
                if not fns:
                    continue

                for fn in fns:
                    fn_record = {
                        "file_path": rel_path,
                        "name": fn["name"],
                        "return_type": fn.get("return_type", "void"),
                        "params": fn.get("params", []),
                        "signature": fn.get("signature", f"{fn.get('return_type', 'void')} {fn['name']}()"),
                        "is_core": fn.get("is_core", 1)
                    }
                    all_functions.append(fn_record)
                    functions_by_file[rel_path].append(fn_record)

                if db_manager and project_id and hasattr(db_manager, "store_c_cpp_functions"):
                    try:
                        db_manager.store_c_cpp_functions(project_id, rel_path, fns)
                    except Exception:
                        pass

    target_dir = reports_dir if reports_dir and os.path.exists(reports_dir) else project_dir
    json_path = os.path.join(target_dir, "c_cpp_functions.json")
    try:
        with open(json_path, "w", encoding="utf-8") as fh:
            json.dump(all_functions, fh, indent=2)
    except Exception:
        pass

    formatted_ref = format_c_cpp_functions_reference(all_functions)
    return all_functions, formatted_ref


def format_c_cpp_functions_reference(functions_list: List[Dict[str, Any]]) -> str:
    """Format extracted C/C++ functions into a markdown context block for LLM prompt reference."""
    if not functions_list:
        return "No existing C/C++ core functions found."

    by_file = defaultdict(list)
    for fn in functions_list:
        by_file[fn["file_path"]].append(fn)

    lines = ["### Core C/C++ Functions Reference:"]
    for rel_path, fns in sorted(by_file.items()):
        lines.append(f"\n#### File: `{rel_path}`")
        for fn in fns:
            tag = " [CORE]" if fn.get("is_core", 1) == 1 else " [AUX/TEST]"
            lines.append(f"  - `{fn['signature']}`{tag}")

    return "\n".join(lines)


def get_c_cpp_stdlib_reference(language: str = "both", db_manager: Any = None) -> str:
    """Retrieve C/C++ Standard Library core functions, algorithms, and data types reference block."""
    if db_manager is None:
        try:
            from database.db_manager import DBManager
            db_manager = DBManager()
        except Exception:
            db_manager = None

    if db_manager and hasattr(db_manager, "get_c_cpp_stdlib"):
        entries = db_manager.get_c_cpp_stdlib(language=language)
    else:
        entries = []

    if not entries:
        return "No standard library entries found."

    by_cat = defaultdict(list)
    for e in entries:
        by_cat[e["category"]].append(e)

    lines = ["### C/C++ Standard Library Core Functions & Data Types Reference:"]
    for cat, items in sorted(by_cat.items()):
        lines.append(f"\n#### Category: {cat.upper()}")
        for item in items:
            lines.append(f"  - `{item['symbol_name']}` [{item['header']}]: {item['description']} (Signature: `{item['signature']}`)")

    return "\n".join(lines)


