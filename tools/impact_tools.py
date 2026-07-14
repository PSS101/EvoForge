import os
import re
from typing import Dict, List, Set
from tools.file_tools import read_file

TEST_FILE_PATTERN = re.compile(r"test_.*\.py$", re.IGNORECASE)
IMPORT_PATTERN = re.compile(r"^\s*from\s+([\w\.]+)\s+import|^\s*import\s+([\w\.]+)", re.MULTILINE)


def list_test_files(project_dir: str) -> List[str]:
    tests = []
    for root, _, files in os.walk(project_dir):
        if "tests" not in root and not root.endswith("tests"):
            continue
        for filename in files:
            if TEST_FILE_PATTERN.match(filename):
                tests.append(os.path.relpath(os.path.join(root, filename), project_dir))
    return sorted(tests)


def map_source_to_tests(project_dir: str, changed_modules: List[str]) -> Dict[str, List[str]]:
    test_map = {module: [] for module in changed_modules}
    all_tests = list_test_files(project_dir)
    for test_path in all_tests:
        abs_path = os.path.join(project_dir, test_path)
        content = read_file(abs_path)
        for module in changed_modules:
            module_name = os.path.splitext(os.path.basename(module))[0]
            if re.search(rf"\b{re.escape(module_name)}\b", content):
                test_map[module].append(test_path)
    return test_map


def generate_test_impact_report(changed_modules: List[str], project_dir: str) -> str:
    test_map = map_source_to_tests(project_dir, changed_modules)
    lines = [
        "# Test Impact Report",
        "",
        "## Changed Source Modules",
        ""
    ]
    if not changed_modules:
        lines.append("No source modules were identified as changed.")
    else:
        for module in changed_modules:
            lines.append(f"- {module}")
    lines.extend(["", "## Impacted Test Files", ""])
    impacted_tests = set()
    for module, tests in test_map.items():
        if tests:
            impacted_tests.update(tests)
            lines.append(f"- {module} -> {', '.join(tests)}")
        else:
            lines.append(f"- {module} -> no direct tests found")
    if not impacted_tests:
        lines.append("No impacted tests could be automatically mapped from the changed modules.")
    lines.append("")
    return "\n".join(lines)
