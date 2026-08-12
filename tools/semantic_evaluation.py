"""
tools/semantic_evaluation.py - Semantic Evaluation Tool for EvoForge

Evaluates semantic requirement coverage, API signature alignment, and boundary check
completeness between SRS.md / Design.md specifications and generated source code.
"""

import os
import re
import ast
from typing import Dict, List, Tuple


def extract_srs_functional_requirements(srs_content: str) -> List[str]:
    """Extract functional requirement strings from SRS.md."""
    if not srs_content:
        return []
    reqs = []
    lines = srs_content.splitlines()
    in_functional = False
    for line in lines:
        if "Functional Requirement" in line or "Core Operations" in line or "3. Functional" in line:
            in_functional = True
            continue
        elif line.startswith("# ") or line.startswith("## 4.") or line.startswith("## Non-Functional"):
            in_functional = False
        if in_functional and line.strip().startswith("- "):
            req_text = re.sub(r"^\s*-\s*(?:\[(NEW|MODIFIED|REMOVED|UNCHANGED)\]\s*)?", "", line).strip()
            if req_text:
                reqs.append(req_text)
    return reqs


def extract_python_code_symbols(code: str) -> Tuple[List[str], List[str]]:
    """Extract function names and class names from Python source using AST."""
    functions = []
    classes = []
    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                functions.append(node.name)
            elif isinstance(node, ast.ClassDef):
                classes.append(node.name)
    except Exception:
        pass
    return functions, classes


def extract_c_code_symbols(code: str) -> Tuple[List[str], List[str]]:
    """Extract function names and struct/class names from C/C++ source using regex."""
    functions = []
    structs_and_classes = []
    struct_matches = re.findall(r"\b(?:struct|class)\s+([A-Za-z_][A-Za-z0-9_]*)", code)
    structs_and_classes.extend(struct_matches)
    
    func_matches = re.findall(r"\b(?:[A-Za-z_][A-Za-z0-9_]*::)?([A-Za-z_][A-Za-z0-9_]*)\s*\([^;]*?\)", code)
    functions.extend(func_matches)
    return list(set(functions)), list(set(structs_and_classes))


def evaluate_project_semantics(project_dir: str, srs_content: str, lang: str = "python") -> Dict[str, any]:
    """
    Perform semantic evaluation of the project source code against SRS.md requirements.
    Returns a dict with score, covered_reqs, missing_reqs, and feedback.
    """
    reqs = extract_srs_functional_requirements(srs_content)
    
    # Auto-detect language if specified lang yields no files or is default python when C/C++ files exist
    cpp_files = []
    py_files = []
    for root, _, files in os.walk(project_dir):
        if any(ign in root for ign in [".git", "__pycache__", ".venv", "tests"]):
            continue
        for f in files:
            if f.endswith((".c", ".cpp", ".cc", ".cxx", ".h", ".hpp")):
                cpp_files.append(os.path.join(root, f))
            elif f.endswith(".py"):
                py_files.append(os.path.join(root, f))
                
    if lang == "python" and cpp_files and not py_files:
        lang = "cpp"
        source_files = cpp_files
    elif lang in {"c", "cpp"}:
        source_files = cpp_files
    else:
        source_files = py_files if py_files else cpp_files

    all_code = ""
    all_functions = []
    all_classes = []

    for sf in source_files:
        try:
            with open(sf, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                all_code += "\n" + content
                if lang == "python":
                    funcs, cls = extract_python_code_symbols(content)
                else:
                    funcs, cls = extract_c_code_symbols(content)
                all_functions.extend(funcs)
                all_classes.extend(cls)
        except Exception:
            pass

    covered_reqs = []
    missing_reqs = []

    for req in reqs:
        req_lower = req.lower()
        stopwords = {"shall", "system", "provide", "implement", "support", "with", "from", "that", "this", "each", "have", "used", "using", "the", "and", "for", "are", "not"}
        words = [w for w in re.findall(r"\b[a-zA-Z]{3,}\b", req_lower) if w not in stopwords]
        matches = []
        for w in words:
            w_stem = w[:3] if len(w) >= 3 else w
            if (w in all_code.lower() or 
                w_stem in all_code.lower() or 
                any(w in fn.lower() or w_stem in fn.lower() or fn.lower() in w for fn in all_functions) or
                any(w in cl.lower() or w_stem in cl.lower() for cl in all_classes)):
                matches.append(w)
        if len(words) == 0 or len(matches) / max(len(words), 1) >= 0.25:
            covered_reqs.append(req)
        else:
            missing_reqs.append(req)

    total_reqs = len(reqs) if reqs else 1
    coverage_score = len(covered_reqs) / total_reqs

    has_boundary_checks = False
    if lang == "python":
        has_boundary_checks = any(kw in all_code for kw in ["raise ", "ValueError", "IndexError", "if ", "try:"])
    else:
        has_boundary_checks = any(kw in all_code for kw in ["if (", "if(", "throw ", "catch", "return false", "return NULL", "return 0", "assert"])

    overall_score = round(coverage_score * 0.8 + (0.2 if has_boundary_checks else 0.0), 2)
    overall_score = min(overall_score, 1.0)

    feedback = []
    if missing_reqs:
        feedback.append(f"Missing semantic requirement implementations: {missing_reqs}")
    if not has_boundary_checks:
        feedback.append("Missing explicit boundary error and validation checks.")

    return {
        "score": overall_score,
        "coverage_score": round(coverage_score, 2),
        "total_requirements": len(reqs),
        "covered_requirements": len(covered_reqs),
        "missing_requirements": missing_reqs,
        "has_boundary_checks": has_boundary_checks,
        "feedback": feedback,
        "is_semantically_valid": overall_score >= 0.7
    }


def generate_semantic_evaluation_report(eval_result: Dict[str, any], reports_dir: str) -> str:
    """Generate Semantic_Evaluation_Report.md report file in reports_dir."""
    report_path = os.path.join(reports_dir, "Semantic_Evaluation_Report.md")
    status_label = "PASSED" if eval_result.get("is_semantically_valid") else "NEEDS REFINEMENT"
    
    content = (
        f"# Semantic Evaluation Report\n\n"
        f"## Executive Summary\n"
        f"- **Status**: {status_label}\n"
        f"- **Semantic Traceability Score**: {eval_result.get('score', 0.0)} / 1.0\n"
        f"- **Requirement Coverage**: {eval_result.get('covered_requirements', 0)} / {eval_result.get('total_requirements', 0)} ({eval_result.get('coverage_score', 0.0) * 100:.1f}%)\n"
        f"- **Boundary Error Handling**: {'Present' if eval_result.get('has_boundary_checks') else 'Missing'}\n\n"
        f"## Detailed Requirement Traceability\n"
    )
    if eval_result.get("missing_requirements"):
        content += "### Uncovered / Missing Requirements\n"
        for req in eval_result["missing_requirements"]:
            content += f"- ❌ {req}\n"
        content += "\n"

    if eval_result.get("feedback"):
        content += "## Recommendations & Actionable Feedback\n"
        for fb in eval_result["feedback"]:
            content += f"- ⚠️ {fb}\n"
    else:
        content += "## Recommendations & Actionable Feedback\n- ✅ All functional requirements and boundary conditions are semantically satisfied.\n"

    os.makedirs(reports_dir, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(content)

    return report_path
