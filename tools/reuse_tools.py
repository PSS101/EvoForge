import re
from typing import Dict, List
from collections import defaultdict
from tools.static_analysis import build_dependency_graph
from tools.requirement_tools import parse_markdown_sections, normalize_text


def _extract_keywords(text: str) -> List[str]:
    words = re.findall(r"[a-zA-Z0-9_]+", text.lower())
    return [word for word in words if len(word) > 2]


def scan_reusable_components(project_dir: str) -> Dict[str, List[Dict[str, str]]]:
    graph = build_dependency_graph(project_dir)
    components = {
        "modules": [],
        "classes": [],
        "functions": []
    }
    for module_path, module_data in graph["modules"].items():
        components["modules"].append({
            "path": module_path,
            "imports": module_data.get("imports", [])
        })
        for class_def in module_data.get("definitions", {}).get("classes", []):
            components["classes"].append({
                "module": module_path,
                "name": class_def["name"],
                "bases": class_def.get("bases", []),
                "methods": [method["name"] for method in class_def.get("methods", [])]
            })
        for func_def in module_data.get("definitions", {}).get("functions", []):
            components["functions"].append({
                "module": module_path,
                "name": func_def["name"],
                "args": func_def.get("args", [])
            })
    return components


def _score_reuse(requirement_text: str, candidate_text: str) -> float:
    req_keywords = set(_extract_keywords(requirement_text))
    candidate_keywords = set(_extract_keywords(candidate_text))
    if not req_keywords or not candidate_keywords:
        return 0.0
    intersection = req_keywords & candidate_keywords
    return len(intersection) / max(len(req_keywords), len(candidate_keywords))


def generate_reuse_decision_report(project_dir: str, srs_text: str) -> str:
    components = scan_reusable_components(project_dir)
    srs_sections = parse_markdown_sections(srs_text or "")
    requirements = []
    for section, items in srs_sections.items():
        for item in items:
            requirements.append({"section": section, "text": item})

    decisions = []
    for requirement in requirements:
        best_match = None
        best_score = 0.0
        candidate_summary = ""
        for cls in components["classes"]:
            score = _score_reuse(requirement["text"], cls["name"])
            if score > best_score:
                best_score = score
                best_match = f"class {cls['name']} in {cls['module']}"
        for func in components["functions"]:
            score = _score_reuse(requirement["text"], func["name"])
            if score > best_score:
                best_score = score
                best_match = f"function {func['name']} in {func['module']}"
        if best_score >= 0.25 and best_match:
            decisions.append({
                "requirement": requirement["text"],
                "decision": "reuse",
                "candidate": best_match,
                "score": best_score
            })
        else:
            decisions.append({
                "requirement": requirement["text"],
                "decision": "new",
                "candidate": "No strong reusable component found",
                "score": best_score
            })

    lines = [
        "# Reuse Decision Report",
        "",
        "## Reusable Components Detected",
        ""
    ]
    if not components["classes"] and not components["functions"]:
        lines.append("No reusable classes or functions were detected in the existing project.")
    else:
        for cls in components["classes"]:
            lines.append(f"- Class `{cls['name']}` in `{cls['module']}` with methods: {', '.join(cls['methods'])}")
        for func in components["functions"]:
            lines.append(f"- Function `{func['name']}` in `{func['module']}` with args: {', '.join(func['args'])}")

    lines.extend(["", "## Reuse Decisions", ""])
    for decision in decisions:
        if decision["decision"] == "reuse":
            lines.append(f"- [REUSE] `{decision['requirement']}` can be satisfied by `{decision['candidate']}` (score: {decision['score']:.2f})")
        else:
            lines.append(f"- [NEW] `{decision['requirement']}` requires new implementation. {decision['candidate']}.")

    lines.append("")
    return "\n".join(lines)
