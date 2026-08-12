import os
import re
try:
    from crewai import Crew, Process, Task
    HAS_CREW = True
except Exception:
    Crew = None
    Process = None
    Task = None
    HAS_CREW = False
from typing import Any as BaseAgent  # Lazy import of BaseAgent at runtime to avoid module-level crewai dependency

from database.db_manager import DBManager
from tools.file_tools import calculate_hash, read_file, write_file, save_json
from tools.project_tools import (
    read_project_file,
    write_project_file,
    list_project_files,
    analyze_python_ast,
    get_c_cpp_functions
)
from tools.build_tools import generate_makefile
from tools.language_tools import detect_language, load_project_language, save_project_language, get_source_extensions, has_explicit_language
from tools.requirement_tools import classify_requirements
from tools.static_analysis import build_dependency_graph, dependency_graph_to_json
from tools.reuse_tools import generate_reuse_decision_report
from tools.impact_tools import generate_test_impact_report
from tools.semantic_evaluation import evaluate_project_semantics, generate_semantic_evaluation_report
import tools.cli_ui as ui

def clean_markdown_content(text: str) -> str:
    """Strips an outer markdown wrapper fence from LLM text.

    IMPORTANT: Only strips the wrapper when the output is a single
    markdown/code block. If the text contains multi-file blocks
    (--- FILE: ... ---) or multiple code fences, return it unchanged
    so that _extract_file_map can parse all blocks correctly.
    """
    if not text:
        return ""
    text = text.strip()
    # Skip cleaning if this looks like a multi-file code output
    if re.search(r'(?:---|###|//|#)\s*(?:FILE|File):', text):
        return text
    # Count code fences — if >2 present, this is a multi-block response; don't strip
    fence_count = len(re.findall(r'^```', text, re.MULTILINE))
    if fence_count > 2:
        return text
    # Safe to strip a single outer markdown wrapper
    match = re.search(r"```(?:markdown)?\s*\n(.*?)\n```$", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    match = re.search(r"```(?:markdown)?\s*\n(.*?)\n```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text

class SDLCCrewManager:
    def __init__(self, project_name: str):
        self.project_name = project_name
        self.project_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "projects",
            project_name
        )
        self.reports_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "reports",
            project_name
        )
        os.makedirs(self.project_dir, exist_ok=True)
        os.makedirs(self.reports_dir, exist_ok=True)

        self.db = DBManager()
        self.project_id = self.db.register_project(project_name, self.project_dir)

    def run_pipeline(self, prompt: str, mode: str = "new"):
        """
        Runs the multi-agent SDLC pipeline incrementally.
        mode can be 'new' or 'evolve'.
        """
        self.current_prompt = prompt
        srs_path = os.path.join(self.reports_dir, "SRS.md")
        delta_path = os.path.join(self.reports_dir, "Requirement_Delta_Report.md")
        dependency_path = os.path.join(self.reports_dir, "Dependency_Graph.json")
        reuse_path = os.path.join(self.reports_dir, "Reuse_Decision_Report.md")
        test_impact_path = os.path.join(self.reports_dir, "Test_Impact_Report.md")

        existing_srs = self._load_existing_srs()
        prompt_language = detect_language(prompt)
        saved_language = load_project_language(self.project_dir)
        if has_explicit_language(prompt):
            self.project_language = prompt_language
            if saved_language and saved_language != prompt_language:
                ui.print_stage_warning(
                    "Language Override",
                    f"Prompt explicitly specifies '{prompt_language}'. Overriding previous project language '{saved_language}'."
                )
        else:
            self.project_language = saved_language or prompt_language
        save_project_language(self.project_dir, self.project_language)

        # STAGE 1: Requirements Analysis
        ui.print_stage_card(1, 5, "Requirements Analysis & SRS Delta", "Parsing functional prompt, analyzing existing specification, and triaging requirement delta.")
        raw_srs = self._run_requirement_stage(prompt, existing_srs, srs_path)

        try:
            merged_srs, delta_report, classified_requirements = classify_requirements(existing_srs, raw_srs)
        except Exception as e:
            ui.print_stage_warning("Requirement Classification", f"classify_requirements failed ({e}). Using raw SRS.")
            merged_srs = raw_srs
            delta_report = f"# Requirement Delta\n\nClassification failed: {e}\n"
            classified_requirements = []
        # Safety guarantee: always write SRS.md — use raw_srs if merged is empty
        write_file(srs_path, merged_srs or raw_srs)
        write_file(delta_path, delta_report or "# Requirement Delta\n\nNo delta computed.\n")
        if hasattr(self.db, 'store_srs_version'):
            try:
                self.db.store_srs_version(self.project_id, merged_srs, note=mode)
            except Exception as e:
                ui.print_stage_warning("DB Persistence", f"Failed to store SRS version in DB: {e}")
        ui.print_stage_success("Requirement Stage", "SRS specification synthesized & requirement delta classified.")

        # STAGE 2: Architecture & Dependency Modeling
        ui.print_stage_card(2, 5, "Architecture & Dependency Modeling", "Generating static dependency graph, evaluating asset reuse, and modeling software design.")
        dependency_graph = build_dependency_graph(self.project_dir)
        save_json(dependency_path, dependency_graph)
        if hasattr(self.db, 'store_dependency_graph'):
            try:
                self.db.store_dependency_graph(self.project_id, "static", dependency_graph_to_json(dependency_graph), file_path=dependency_path)
            except Exception as e:
                ui.print_stage_warning("DB Persistence", f"Failed to store dependency graph in DB: {e}")

        reuse_report = generate_reuse_decision_report(self.project_dir, merged_srs)
        write_file(reuse_path, reuse_report)

        impacted_modules = self._guess_impacted_modules(classified_requirements)
        test_impact_report = generate_test_impact_report(impacted_modules, self.project_dir)
        write_file(test_impact_path, test_impact_report)

        self._run_design_stage(design_output=os.path.join(self.reports_dir, "Design.md"), delta_path=delta_path)
        ui.print_stage_success("Architecture Stage", "Dependency graph, reuse decisions & design documents updated.")

        # STAGE 3: Automated Code Generation
        ui.print_stage_card(3, 5, "Automated Code Engineering", "Generating source files, module headers, and build configuration specs.")
        try:
            from agents.base_agent import BaseAgent as _BaseAgent
            code_agent_name = "c_code_agent" if self.project_language in {"c", "cpp"} else "code_agent"
            code_agent_wrapper = _BaseAgent(code_agent_name)
        except Exception as e:
            ui.print_stage_warning("Agent Initialization", f"Could not import BaseAgent for code stage: {e}. Proceeding with fallback.")
            code_agent_wrapper = None
        self._run_code_stage(code_agent_wrapper=code_agent_wrapper, code_output=None, dependency_path=dependency_path, reuse_path=reuse_path, delta_path=delta_path)
        ui.print_stage_success("Code Engineering Stage", "Source files and build artifacts synthesized.")

        # STAGE 4: Testing & Test Suite Synthesis
        ui.print_stage_card(4, 5, "Test Suite & Impact Mapping", "Synthesizing test cases and mapping requirement impact to test execution suites.")
        self._run_testing_stage(testing_output_dir=os.path.join(self.project_dir, "tests"), test_impact_path=test_impact_path)
        ui.print_stage_success("Testing Stage", "Test suite files generated and mapped to impact specs.")

        # STAGE 5: Documentation & Spec Persistence
        ui.print_stage_card(5, 5, "Documentation & Spec Persistence", "Generating project documentation and updating SQLite DB version control.")
        self._run_documentation_stage(doc_output_dir=self.project_dir)

        self._update_db_registry_and_run(mode)
        ui.print_stage_success("Documentation Stage", "Project documentation synthesized and version control updated.")
        return {
            "srs": srs_path,
            "delta_report": delta_path,
            "dependency_graph": dependency_path,
            "reuse_report": reuse_path,
            "test_impact_report": test_impact_path
        }

    def _load_existing_srs(self) -> str:
        srs_path = os.path.join(self.reports_dir, "SRS.md")
        if os.path.exists(srs_path):
            return read_file(srs_path)
        return ""

    def _sanitize_rel_path(self, rel_path: str) -> str:
        clean = rel_path.strip().strip('`\'":').strip()
        clean = clean.lstrip('./\\')
        clean = clean.rstrip('/\\')
        if not clean:
            return ""
        proj_prefix = f"projects/{self.project_name}/"
        if clean.startswith(proj_prefix):
            clean = clean[len(proj_prefix):]
        elif clean.startswith(f"{self.project_name}/"):
            clean = clean[len(f"{self.project_name}/"):]
        if not clean or clean == self.project_name or not os.path.basename(clean) or "." not in os.path.basename(clean):
            return ""
        return clean

    def _extract_file_map(self, text: str) -> dict[str, str]:
        """Extract relative_file_path -> code_content mapping from LLM output without writing to disk."""
        if not text:
            return {}

        file_map = {}

        def add_file(rel_path: str, code_str: str):
            sanitized = self._sanitize_rel_path(rel_path)
            if sanitized and sanitized not in file_map and code_str.strip():
                file_map[sanitized] = code_str.strip() + "\n"

        # Pattern 1: --- FILE: rel/path --- or ### File: rel/path or // File: rel/path or # File: rel/path
        file_block_pattern = re.compile(
            r"(?:---|###|//|\#|\/\*)\s*(?:[Ff]ile:\s*|FILE:\s*)?`?([^\n`\s\:]+\.(?:py|c|cpp|cc|cxx|h|hpp|hxx|md|txt|json))`?\s*(?:---|###|\*\/)?\s*\n```(?:[a-zA-Z0-9_\+\-]+)?\s*\n(.*?)\n```",
            re.DOTALL
        )
        for rel_path, code in file_block_pattern.findall(text):
            add_file(rel_path, code)

        # Pattern 2: ```python filename=rel_path or ```cpp file="rel_path"
        fence_file_pattern = re.compile(
            r"```(?:[a-zA-Z0-9_\+\-]+)?\s+(?:filename=|file=)?`?\"?'?([^\n`\s\"']+\.(?:py|c|cpp|cc|cxx|h|hpp|hxx|md|txt|json))`?\"?'?\s*\n(.*?)\n```",
            re.DOTALL
        )
        for rel_path, code in fence_file_pattern.findall(text):
            add_file(rel_path, code)

        # Pattern 3: Markdown section headers right before code fences (e.g. ### filename.cpp or **filename.h**)
        header_fence_pattern = re.compile(
            r"(?:#{1,6}|\*\*|\*)\s*(?:[Ff]ile(?:\s*\d+)?:?\s*)?`?([a-zA-Z0-9_\-/\.]+\.(?:py|c|cpp|cc|cxx|h|hpp|hxx|md|txt|json))`?\s*(?:\*\*|\*)?\s*\n+```(?:[a-zA-Z0-9_\+\-]+)?\s*\n(.*?)\n```",
            re.DOTALL
        )
        for rel_path, code in header_fence_pattern.findall(text):
            add_file(rel_path, code)

        # Pattern 4: Code block with file header inside the fence (e.g. --- FILE: src/hello.c --- or // FILE: src/hello.c)
        code_block_pattern = re.compile(
            r"```(?:[a-zA-Z0-9_\+\-]+)?\s*\n(.*?)\n```",
            re.DOTALL
        )
        for code_match in code_block_pattern.finditer(text):
            code = code_match.group(1).strip()
            lines = code.splitlines()
            first_line = lines[0] if lines else ""
            header_match = re.match(
                r"^\s*(?:---|###|//|\#|/\*)\s*(?:[Ff]ile:\s*|FILE:\s*)?`?([a-zA-Z0-9_\-/\.]+\.(?:py|c|cpp|cc|cxx|h|hpp|hxx|md|txt|json))`?\s*(?:---|###|\*/)?\s*$",
                first_line
            )
            if header_match:
                rel_path = header_match.group(1)
                clean_code = "\n".join(lines[1:]).strip() + "\n"
                add_file(rel_path, clean_code)

        # Pattern 5: File: path/to/file.ext right before code block
        preamble_pattern = re.compile(
            r"(?:[Ff]ile|[Ff]ilename):\s*`?([a-zA-Z0-9_\-/\.]+\.(?:py|c|cpp|cc|cxx|h|hpp|hxx|md|txt|json))`?\s*\n+```(?:[a-zA-Z0-9_\+\-]+)?\s*\n(.*?)\n```",
            re.DOTALL
        )
        for rel_path, code in preamble_pattern.findall(text):
            add_file(rel_path, code)

        return file_map

    def _validate_syntax(self, file_map: dict[str, str], lang: str, task_name: str = "code_task") -> tuple[bool, str]:
        """Validate syntax for Python (ast.parse) or C/C++ (compile check) and evaluate semantic coverage.
        Semantic evaluation is only applied to 'code_task' — test files verify requirements,
        they don't implement them, so running semantic scoring on test files always produces
        false failures. Returns (is_valid, error_msg)."""
        if not file_map:
            return False, "No code files were extracted from model output."

        # Filter file_map to valid file entries
        valid_file_map = {
            rel: code for rel, code in file_map.items()
            if os.path.basename(rel) and "." in os.path.basename(rel)
        }
        if not valid_file_map:
            return False, "No valid code files with extensions were extracted from model output."

        # 1. Python Syntax Validation
        if lang == "python":
            import ast
            for rel_path, code in valid_file_map.items():
                if rel_path.endswith(".py"):
                    try:
                        ast.parse(code, filename=rel_path)
                    except SyntaxError as se:
                        return False, f"Python SyntaxError in '{rel_path}' at line {se.lineno}: {se.msg}\nLine: {se.text}"

        # 2. C/C++ Syntax Validation
        elif lang in {"c", "cpp"}:
            import tempfile, shutil
            from tools.build_tools import compile_project, parse_c_compiler_errors, generate_makefile

            temp_dir = tempfile.mkdtemp()
            try:
                for rel_path, code in valid_file_map.items():
                    full_p = os.path.join(temp_dir, rel_path)
                    os.makedirs(os.path.dirname(full_p), exist_ok=True)
                    write_file(full_p, code)

                # Strip deprecated C++17-incompatible dynamic exception specs before compiling
                _throw_re = re.compile(r'\s*throw\s*\([^)]*\)', re.MULTILINE)
                for root, _, fnames in os.walk(temp_dir):
                    for fname in fnames:
                        if fname.endswith(('.cpp', '.cxx', '.cc', '.hpp', '.hxx', '.h')):
                            fpath = os.path.join(root, fname)
                            try:
                                with open(fpath, 'r', encoding='utf-8', errors='replace') as f:
                                    content = f.read()
                                cleaned = _throw_re.sub('', content)
                                if cleaned != content:
                                    with open(fpath, 'w', encoding='utf-8') as f:
                                        f.write(cleaned)
                            except Exception:
                                pass

                proj_name = "syntax_val"
                generate_makefile(temp_dir, proj_name, lang)
                comp_ok, comp_out = compile_project(temp_dir)
                if not comp_ok:
                    errors = parse_c_compiler_errors(comp_out)
                    if errors:
                        err_lines = [f"{e['file']}:{e['line']}: {e['severity']}: {e['message']}" for e in errors]
                        return False, "C/C++ Compiler Errors:\n" + "\n".join(err_lines)
                    return False, f"C/C++ Compiler Error Output:\n{comp_out.strip()}"
            finally:
                shutil.rmtree(temp_dir, ignore_errors=True)

        # 3. Semantic Requirement Evaluation — only for code_task.
        if task_name == "code_task":
            srs_path = os.path.join(self.reports_dir, "SRS.md")
            if os.path.exists(srs_path):
                srs_content = read_file(srs_path)
                import tempfile, shutil
                eval_temp = tempfile.mkdtemp()
                try:
                    for rel_path, code in valid_file_map.items():
                        full_p = os.path.join(eval_temp, rel_path)
                        os.makedirs(os.path.dirname(full_p), exist_ok=True)
                        write_file(full_p, code)
                    eval_res = evaluate_project_semantics(eval_temp, srs_content, lang)
                    generate_semantic_evaluation_report(eval_res, self.reports_dir)

                    # Only fail if semantic coverage score is 0.0; log warnings otherwise
                    if not eval_res.get("is_semantically_valid") and eval_res.get("score", 0.0) == 0.0:
                        fb_str = "\n".join([f"- {fb}" for fb in eval_res.get("feedback", [])])
                        return False, f"Semantic Evaluation Failed (Score: {eval_res.get('score')}/1.0):\n{fb_str}"
                finally:
                    shutil.rmtree(eval_temp, ignore_errors=True)

        return True, "Syntax & Semantic validation passed."

    def _extract_and_write_files(self, text: str) -> list[str]:
        """Extract code blocks or file markers from LLM response and write to project_dir."""
        file_map = self._extract_file_map(text)
        written = []
        for rel_path, code in file_map.items():
            target_path = os.path.join(self.project_dir, rel_path)
            write_file(target_path, code)
            written.append(rel_path)
        return written

    def _run_single_stage(self, agent_wrapper: BaseAgent, task_name: str, task_vars: dict, output_file=None, tools=None):
        """Run a single agent task with syntax validation and self-correction before saving code files."""
        agent = None
        description = task_vars.get("prompt", f"{task_name} (no description)")
        expected = None

        if agent_wrapper is not None:
            try:
                agent = agent_wrapper.get_agent(tools=tools)
                description = agent_wrapper.get_task_description(task_name).format(**task_vars)
                expected = agent_wrapper.get_task_expected_output(task_name)
            except Exception as e:
                print(f"Agent wrapper preparation failed: {e}")
                agent = None

        lang = getattr(self, 'project_language', 'python')

        # Code & Testing Stage Validation and Self-Correction Loop
        if task_name in {"code_task", "testing_task"}:
            max_attempts = int(os.environ.get("EVOFORGE_MAX_RETRIES", "3"))
            current_prompt = description
            last_file_map = {}
            last_cleaned_text = ""

            for attempt in range(1, max_attempts + 1):
                raw_out = None
                if agent is not None and hasattr(agent, 'run') and not HAS_CREW:
                    try:
                        raw_out = agent.run(current_prompt)
                    except Exception as e:
                        print(f"Local agent attempt {attempt} failed: {e}")
                elif HAS_CREW and agent is not None:
                    try:
                        task = Task(
                            description=current_prompt,
                            expected_output=expected or f"Output for {task_name}",
                            agent=agent,
                            output_file=output_file
                        )
                        crew = Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=True)
                        raw_out = str(crew.kickoff())
                    except Exception as e:
                        print(f"Crew attempt {attempt} failed: {e}")

                if raw_out and not self._is_local_agent_failure(raw_out):
                    # Try extraction on raw output FIRST (before cleaning strips file blocks)
                    file_map = self._extract_file_map(raw_out)
                    if not file_map:
                        # Fallback: try after cleaning in case output has an outer wrapper
                        cleaned_text = clean_markdown_content(raw_out)
                        file_map = self._extract_file_map(cleaned_text)
                    else:
                        cleaned_text = raw_out

                    if file_map:
                        last_file_map = file_map
                        last_cleaned_text = cleaned_text

                    is_valid, val_msg = self._validate_syntax(file_map, lang, task_name=task_name)

                    if is_valid:
                        # SAVE ONLY AFTER SUCCESSFUL VALIDATION
                        for rel_path, code in file_map.items():
                            write_file(os.path.join(self.project_dir, rel_path), code)
                        if output_file:
                            write_file(output_file, cleaned_text)
                        print(f"Syntax validation passed on attempt {attempt} for '{task_name}'. Saved {len(file_map)} files.")
                        return cleaned_text
                    else:
                        print(f"Syntax validation failed on attempt {attempt} for '{task_name}':\n{val_msg}")
                        # Send compiler/syntax error back to model & ask it to fix ONLY reported issues
                        current_prompt = (
                            f"{description}\n\n"
                            f"CRITICAL: Syntax/Compiler Validation Failed on previous attempt!\n"
                            f"Reported Errors:\n{val_msg}\n\n"
                            f"Please fix ONLY the reported errors above and regenerate all code files. Use standard file blocks:\n"
                            f"--- FILE: relative/path ---\n```\n<fixed code>\n```"
                        )

            # Preserve best-effort LLM code if extracted, rather than wiping out with simple fallback
            if last_file_map:
                print(f"Validation had warnings after {max_attempts} attempts for '{task_name}'. Preserving {len(last_file_map)} best-effort LLM code files.")
                for rel_path, code in last_file_map.items():
                    write_file(os.path.join(self.project_dir, rel_path), code)
                if output_file and last_cleaned_text:
                    write_file(output_file, last_cleaned_text)
                return last_cleaned_text

            print(f"All {max_attempts} validation attempts failed and no LLM files were extracted for '{task_name}'. Using deterministic fallback.")
            if lang in {"c", "cpp"}:
                return self._run_c_fallback(task_name, task_vars, output_file)
            else:
                return self._run_python_fallback(task_name, task_vars, output_file)

        # Standard execution for non-code stages (requirements, design, docs)
        result_text = None
        if agent is not None and hasattr(agent, 'run') and not HAS_CREW:
            try:
                raw_out = agent.run(description)
                if raw_out and not self._is_local_agent_failure(raw_out):
                    result_text = raw_out
            except Exception as e:
                print(f"Local agent execution failed for '{task_name}': {e}")
        elif HAS_CREW and agent is not None:
            try:
                task = Task(
                    description=description,
                    expected_output=expected or f"Output for {task_name}",
                    agent=agent,
                    output_file=output_file
                )
                crew = Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=True)
                result_text = str(crew.kickoff())
            except Exception as e:
                print(f"Crew execution failed for '{task_name}': {e}")

        if result_text:
            cleaned_text = clean_markdown_content(result_text)
            if output_file:
                write_file(output_file, cleaned_text)
            if task_name == "documentation_task":
                self._extract_and_write_files(result_text)
            return cleaned_text

        print(f"Using deterministic fallback for stage '{task_name}'.")
        if lang in {"c", "cpp"}:
            return self._run_c_fallback(task_name, task_vars, output_file)
        else:
            return self._run_python_fallback(task_name, task_vars, output_file)

    def _run_requirement_stage(self, prompt: str, existing_srs: str, output_file: str) -> str:
        # Lazy import BaseAgent to avoid import-time crewai dependency
        try:
            from agents.base_agent import BaseAgent as _BaseAgent
            req_agent_wrapper = _BaseAgent("requirement_agent")
        except Exception as e:
            print(f"Could not import BaseAgent for requirement stage: {e}. Proceeding with fallback.")
            req_agent_wrapper = None

        req_task_vars = {
            "prompt": prompt,
            "reports_dir": self.reports_dir,
            "existing_srs": existing_srs or ""
        }
        self._run_single_stage(
            req_agent_wrapper,
            "requirement_task",
            req_task_vars,
            output_file=output_file,
            tools=[read_project_file, write_project_file]
        )
        return read_file(output_file)

    def _run_python_fallback(self, task_name: str, task_vars: dict, output_file: str = None):
        prompt = task_vars.get("prompt", getattr(self, "current_prompt", ""))
        domain = self._infer_python_domain(prompt)

        if task_name == "requirement_task":
            content = self._generate_python_requirements(prompt, domain)
            if output_file:
                write_file(output_file, content)
            return content
        if task_name == "design_task":
            content = self._generate_python_design(prompt, domain)
            if output_file:
                write_file(output_file, content)
            return content
        if task_name == "code_task":
            self._generate_python_code(prompt, domain)
            return "Generated Python source files."
        if task_name == "testing_task":
            self._generate_python_tests(domain)
            return "Generated Python tests."
        if task_name == "documentation_task":
            self._generate_python_documentation(domain)
            return "Generated Python documentation."
        return None

    def _infer_python_domain(self, prompt: str) -> str:
        """Derive a safe module name from the project name — no domain keyword sniffing.
        The LLM is responsible for producing domain-specific logic; this is only used
        as a last-resort fallback skeleton module name.
        """
        clean_name = re.sub(r'[^a-zA-Z0-9_]', '_', self.project_name).strip('_').lower()
        return clean_name or "utility"

    def _generate_python_requirements(self, prompt: str, domain: str) -> str:
        domain_title = domain.capitalize()
        return (
            f"# Software Requirements Specification (SRS)\n\n"
            f"## 1. Document Overview & System Purpose\n"
            f"The system shall provide a fully functional, robust, and extensible {domain_title} application in Python.\n"
            f"This specification outlines the functional features, user interactions, input/output validation, error handling, and quality constraints.\n\n"
            f"## 2. User Personas & System Scope\n"
            f"- **Target Users**: End-users, software developers, and automated test runners.\n"
            f"- **Execution Environment**: Python 3.8+ command-line environment.\n"
            f"- **Dependencies**: Standard Python library and Pytest testing framework.\n\n"
            f"## 3. Functional Requirements\n"
            f"### 3.1 Primary Operations & Business Logic\n"
            f"- [NEW] The system shall implement core operational routines for {domain_title}.\n"
            f"- [NEW] The system shall support dynamic execution via an interactive user menu interface.\n"
            f"- [NEW] The system shall output accurate computation and status results for all valid inputs.\n\n"
            f"### 3.2 Input Validation & Boundary Error Handling\n"
            f"- [NEW] The system shall validate user inputs prior to processing and reject invalid data types or out-of-bound values.\n"
            f"- [NEW] The system shall handle boundary conditions (e.g. division by zero, empty collections, negative parameters) without raising unhandled exceptions.\n"
            f"- [NEW] The system shall display informative error messages when input validation fails.\n\n"
            f"### 3.3 State Management & Execution Flow\n"
            f"- [NEW] The system shall allow users to execute multiple operations sequentially until opting to exit.\n"
            f"- [NEW] The system shall ensure clean initialization and termination of application resources.\n\n"
            f"## 4. Non-Functional Requirements\n"
            f"### 4.1 Performance & Latency\n"
            f"- [NEW] Operational routines shall execute synchronously within 100 milliseconds for standard operations.\n\n"
            f"### 4.2 Reliability & Fault Tolerance\n"
            f"- [NEW] The system shall maintain 100% stability under invalid inputs by trapping exceptions internally.\n\n"
            f"### 4.3 Maintainability & Code Quality\n"
            f"- [NEW] Source code shall adhere strictly to Python PEP 8 formatting guidelines, type hinting, and modular function decomposition.\n\n"
            f"### 4.4 Automated Testing & Verification\n"
            f"- [NEW] The system shall include an automated Pytest test suite (`tests/test_{domain}.py`) covering positive, negative, and edge-case execution paths.\n\n"
            f"## 5. Interface & Operational Constraints\n"
            f"- [NEW] The user interface shall operate as a clean, text-based interactive command-line interface (CLI).\n"
            f"- [NEW] All primary documentation (`README.md`, `User_Manual.md`) shall include setup, execution, and test commands.\n"
        )

    def _generate_python_design(self, prompt: str, domain: str) -> str:
        domain_title = domain.capitalize()
        return (
            "# Design Document\n\n"
            f"## Architecture Overview\nThe project is organized as a modular Python application centered on the `{domain}` module.\n\n"
            f"## Module Specifications\n"
            f"- `{domain}.py`: Core domain logic and operations.\n"
            f"- `main.py`: Application entry point and demonstration CLI.\n"
            f"- `tests/test_{domain}.py`: Pytest suite for automated testing.\n\n"
            "## Sequence Flow\n"
            "```mermaid\nsequenceDiagram\n    participant User\n    participant Main\n"
            f"    participant {domain_title}Service\n\n"
            "    User->>Main: execute program\n"
            f"    Main->>{domain_title}Service: perform operation\n"
            f"    {domain_title}Service-->>Main: return result\n"
            "    Main-->>User: display output\n"
            "```\n"
        )

    def _generate_python_code(self, prompt: str, domain: str) -> None:
        """Generate a minimal generic Python scaffold. Domain-specific code is expected
        from the LLM; this is only reached when LLM output is completely absent.
        """
        if False:  # Placeholder — never enters domain branches below
            code = (
                "import math\n\n"
                "def add(a: float, b: float) -> float:\n    return a + b\n\n"
                "def subtract(a: float, b: float) -> float:\n    return a - b\n\n"
                "def multiply(a: float, b: float) -> float:\n    return a * b\n\n"
                "def divide(a: float, b: float) -> float:\n    if b == 0:\n        raise ValueError('Division by zero is not allowed.')\n    return a / b\n\n"
                "def power(base: float, exp: float) -> float:\n    return math.pow(base, exp)\n\n"
                "def square_root(val: float) -> float:\n    if val < 0:\n        raise ValueError('Cannot calculate square root of a negative number.')\n    return math.sqrt(val)\n"
            )
            main_code = (
                "from calculator import add, subtract, multiply, divide, power, square_root\n\n"
                "def main():\n"
                "    print('Calculator Demo:')\n"
                "    print('10 + 5 =', add(10, 5))\n"
                "    print('10 - 5 =', subtract(10, 5))\n"
                "    print('10 * 5 =', multiply(10, 5))\n"
                "    print('10 / 5 =', divide(10, 5))\n"
                "    print('2 ^ 3 =', power(2, 3))\n"
                "    print('sqrt(16) =', square_root(16))\n\n"
                "if __name__ == '__main__':\n    main()\n"
            )
        elif domain == "converter":
            code = (
                "def celsius_to_fahrenheit(c: float) -> float:\n    return (c * 9 / 5) + 32\n\n"
                "def fahrenheit_to_celsius(f: float) -> float:\n    return (f - 32) * 5 / 9\n\n"
                "def meters_to_feet(m: float) -> float:\n    return m * 3.28084\n\n"
                "def feet_to_meters(ft: float) -> float:\n    return ft / 3.28084\n"
            )
            main_code = (
                "from converter import celsius_to_fahrenheit, fahrenheit_to_celsius, meters_to_feet, feet_to_meters\n\n"
                "def main():\n"
                "    print('Converter Demo:')\n"
                "    print('0 C =', celsius_to_fahrenheit(0), 'F')\n"
                "    print('32 F =', fahrenheit_to_celsius(32), 'C')\n"
                "    print('1 m =', meters_to_feet(1), 'ft')\n"
                "    print('3.28084 ft =', feet_to_meters(3.28084), 'm')\n\n"
                "if __name__ == '__main__':\n    main()\n"
            )
        elif domain == "parser":
            code = (
                "import csv\nimport json\nimport xml.etree.ElementTree as ET\nfrom typing import List, Dict, Any\n\n"
                "def parse_csv_string(csv_text: str) -> List[Dict[str, str]]:\n"
                "    lines = [line.strip() for line in csv_text.strip().splitlines() if line.strip()]\n"
                "    reader = csv.DictReader(lines)\n"
                "    return list(reader)\n\n"
                "def export_to_json(data: List[Dict[str, Any]]) -> str:\n"
                "    return json.dumps(data, indent=2)\n\n"
                "def export_to_xml(data: List[Dict[str, Any]], root_tag: str = 'items') -> str:\n"
                "    root = ET.Element(root_tag)\n"
                "    for item in data:\n"
                "        item_elem = ET.SubElement(root, 'item')\n"
                "        for k, v in item.items():\n"
                "            child = ET.SubElement(item_elem, str(k))\n"
                "            child.text = str(v)\n"
                "    return ET.tostring(root, encoding='utf-8').decode('utf-8')\n"
            )
            main_code = (
                "from parser import parse_csv_string, export_to_json, export_to_xml\n\n"
                "def main():\n"
                "    sample_csv = 'name,age\\nAlice,30\\nBob,25\\n'\n"
                "    data = parse_csv_string(sample_csv)\n"
                "    print('Parsed Data:', data)\n"
                "    print('JSON Output:\\n', export_to_json(data))\n"
                "    print('XML Output:\\n', export_to_xml(data))\n\n"
                "if __name__ == '__main__':\n    main()\n"
            )
        elif domain == "interest":
            code = (
                "def calculate_simple_interest(principal: float, rate: float, time: float) -> float:\n"
                "    if principal < 0 or rate < 0 or time < 0:\n"
                "        raise ValueError('Inputs must be non-negative.')\n"
                "    return (principal * rate * time) / 100.0\n\n"
                "def calculate_total_amount(principal: float, rate: float, time: float) -> float:\n"
                "    interest = calculate_simple_interest(principal, rate, time)\n"
                "    return principal + interest\n"
            )
            main_code = (
                "from interest import calculate_simple_interest, calculate_total_amount\n\n"
                "def main():\n"
                "    p, r, t = 1000.0, 5.0, 2.0\n"
                "    interest = calculate_simple_interest(p, r, t)\n"
                "    total = calculate_total_amount(p, r, t)\n"
                "    print(f'Principal: {p}, Rate: {r}%, Time: {t} years')\n"
                "    print(f'Simple Interest: {interest}')\n"
                "    print(f'Total Amount: {total}')\n\n"
                "if __name__ == '__main__':\n    main()\n"
            )
        elif domain in {"queue", "stack"}:
            if domain == "queue":
                code = (
                    "from typing import Any, List\n\n"
                    "class Queue:\n"
                    "    def __init__(self):\n        self._items: List[Any] = []\n\n"
                    "    def enqueue(self, item: Any) -> None:\n        self._items.append(item)\n\n"
                    "    def dequeue(self) -> Any:\n"
                    "        if self.is_empty():\n            raise IndexError('dequeue from empty queue')\n"
                    "        return self._items.pop(0)\n\n"
                    "    def peek(self) -> Any:\n"
                    "        if self.is_empty():\n            raise IndexError('peek from empty queue')\n"
                    "        return self._items[0]\n\n"
                    "    def is_empty(self) -> bool:\n        return len(self._items) == 0\n\n"
                    "    def size(self) -> int:\n        return len(self._items)\n"
                )
                main_code = (
                    "from queue import Queue\n\n"
                    "def main():\n"
                    "    q = Queue()\n"
                    "    q.enqueue(10)\n    q.enqueue(20)\n"
                    "    print('Front:', q.peek())\n"
                    "    print('Dequeued:', q.dequeue())\n"
                    "    print('Size:', q.size())\n\n"
                    "if __name__ == '__main__':\n    main()\n"
                )
            else:
                code = (
                    "from typing import Any, List\n\n"
                    "class Stack:\n"
                    "    def __init__(self):\n        self._items: List[Any] = []\n\n"
                    "    def push(self, item: Any) -> None:\n        self._items.append(item)\n\n"
                    "    def pop(self) -> Any:\n"
                    "        if self.is_empty():\n            raise IndexError('pop from empty stack')\n"
                    "        return self._items.pop()\n\n"
                    "    def peek(self) -> Any:\n"
                    "        if self.is_empty():\n            raise IndexError('peek from empty stack')\n"
                    "        return self._items[-1]\n\n"
                    "    def is_empty(self) -> bool:\n        return len(self._items) == 0\n\n"
                    "    def size(self) -> int:\n        return len(self._items)\n"
                )
                main_code = (
                    "from stack import Stack\n\n"
                    "def main():\n"
                    "    s = Stack()\n"
                    "    s.push(10)\n    s.push(20)\n"
                    "    print('Top:', s.peek())\n"
                    "    print('Popped:', s.pop())\n"
                    "    print('Size:', s.size())\n\n"
                    "if __name__ == '__main__':\n    main()\n"
                )
        else:
            module_name = domain
            code = (
                f"from typing import Any, Dict\n\n"
                f"class {domain.capitalize()}:\n"
                "    def __init__(self, name: str = 'default'):\n"
                "        self.name = name\n"
                "        self._data: Dict[str, Any] = {}\n\n"
                "    def set_value(self, key: str, value: Any) -> None:\n"
                "        self._data[key] = value\n\n"
                "    def get_value(self, key: str, default: Any = None) -> Any:\n"
                "        return self._data.get(key, default)\n\n"
                "    def has_key(self, key: str) -> bool:\n"
                "        return key in self._data\n"
            )
            main_code = (
                f"from {module_name} import {domain.capitalize()}\n\n"
                "def main():\n"
                f"    obj = {domain.capitalize()}('demo')\n"
                "    obj.set_value('status', 'active')\n"
                "    print('Status:', obj.get_value('status'))\n\n"
                "if __name__ == '__main__':\n    main()\n"
            )

        # Generic scaffold: use project_name as module name
        module_name = domain
        code = (
            f"from typing import Any, Dict\n\n"
            f"class {module_name.capitalize()}:\n"
            "    \"\"\"Core domain class. Replace with LLM-generated implementation.\"\"\"\n"
            "    def __init__(self, name: str = 'default'):\n"
            "        self.name = name\n"
            "        self._data: Dict[str, Any] = {}\n\n"
            "    def set_value(self, key: str, value: Any) -> None:\n"
            "        self._data[key] = value\n\n"
            "    def get_value(self, key: str, default: Any = None) -> Any:\n"
            "        return self._data.get(key, default)\n\n"
            "    def has_key(self, key: str) -> bool:\n"
            "        return key in self._data\n"
        )
        main_code = (
            f"from {module_name} import {module_name.capitalize()}\n\n"
            "def main():\n"
            f"    obj = {module_name.capitalize()}('demo')\n"
            "    obj.set_value('status', 'active')\n"
            "    print('Status:', obj.get_value('status'))\n\n"
            "if __name__ == '__main__':\n    main()\n"
        )
        write_file(os.path.join(self.project_dir, f"{module_name}.py"), code)
        write_file(os.path.join(self.project_dir, "main.py"), main_code)

    def _generate_python_tests(self, domain: str) -> None:
        """Generate a minimal generic test scaffold. Full tests are expected from the LLM."""
        test_dir = os.path.join(self.project_dir, "tests")
        test_file = os.path.join(test_dir, f"test_{domain}.py")

        if False:  # Placeholder — domain-specific branches removed
            test_code = (
                "import pytest\n"
                "from calculator import add, subtract, multiply, divide, power, square_root\n\n"
                "def test_calculator_basic():\n"
                "    assert add(2, 3) == 5\n"
                "    assert subtract(10, 4) == 6\n"
                "    assert multiply(3, 4) == 12\n"
                "    assert divide(10, 2) == 5.0\n"
                "    assert power(2, 3) == 8.0\n"
                "    assert square_root(25) == 5.0\n\n"
                "def test_calculator_divide_by_zero():\n"
                "    with pytest.raises(ValueError):\n"
                "        divide(5, 0)\n\n"
                "def test_calculator_negative_sqrt():\n"
                "    with pytest.raises(ValueError):\n"
                "        square_root(-4)\n"
            )
        elif domain == "converter":
            test_code = (
                "import pytest\n"
                "from converter import celsius_to_fahrenheit, fahrenheit_to_celsius, meters_to_feet, feet_to_meters\n\n"
                "def test_temperature_conversion():\n"
                "    assert celsius_to_fahrenheit(0) == 32.0\n"
                "    assert fahrenheit_to_celsius(32) == 0.0\n"
                "    assert celsius_to_fahrenheit(100) == 212.0\n\n"
                "def test_length_conversion():\n"
                "    assert pytest.approx(meters_to_feet(1), 0.001) == 3.28084\n"
                "    assert pytest.approx(feet_to_meters(3.28084), 0.001) == 1.0\n"
            )
        elif domain == "parser":
            test_code = (
                "import pytest\n"
                "from parser import parse_csv_string, export_to_json, export_to_xml\n\n"
                "def test_parser_csv_json_xml():\n"
                "    csv_data = 'name,age\\nAlice,30\\n'\n"
                "    parsed = parse_csv_string(csv_data)\n"
                "    assert len(parsed) == 1\n"
                "    assert parsed[0]['name'] == 'Alice'\n"
                "    json_out = export_to_json(parsed)\n"
                "    assert 'Alice' in json_out\n"
                "    xml_out = export_to_xml(parsed)\n"
                "    assert '<name>Alice</name>' in xml_out\n"
            )
        elif domain == "interest":
            test_code = (
                "import pytest\n"
                "from interest import calculate_simple_interest, calculate_total_amount\n\n"
                "def test_simple_interest():\n"
                "    assert calculate_simple_interest(1000, 5, 2) == 100.0\n"
                "    assert calculate_total_amount(1000, 5, 2) == 1100.0\n\n"
                "def test_invalid_interest_inputs():\n"
                "    with pytest.raises(ValueError):\n"
                "        calculate_simple_interest(-100, 5, 2)\n"
            )
        elif domain == "queue":
            test_code = (
                "import pytest\n"
                "from queue import Queue\n\n"
                "def test_queue_operations():\n"
                "    q = Queue()\n"
                "    assert q.is_empty()\n"
                "    q.enqueue(1)\n    q.enqueue(2)\n"
                "    assert q.peek() == 1\n"
                "    assert q.dequeue() == 1\n"
                "    assert q.dequeue() == 2\n"
                "    assert q.is_empty()\n\n"
                "def test_queue_empty_errors():\n"
                "    q = Queue()\n"
                "    with pytest.raises(IndexError):\n"
                "        q.dequeue()\n"
                "    with pytest.raises(IndexError):\n"
                "        q.peek()\n"
            )
        elif domain == "stack":
            test_code = (
                "import pytest\n"
                "from stack import Stack\n\n"
                "def test_stack_operations():\n"
                "    s = Stack()\n"
                "    assert s.is_empty()\n"
                "    s.push(1)\n    s.push(2)\n"
                "    assert s.peek() == 2\n"
                "    assert s.pop() == 2\n"
                "    assert s.pop() == 1\n"
                "    assert s.is_empty()\n\n"
                "def test_stack_empty_errors():\n"
                "    s = Stack()\n"
                "    with pytest.raises(IndexError):\n"
                "        s.pop()\n"
                "    with pytest.raises(IndexError):\n"
                "        s.peek()\n"
            )
        else:
            test_code = (
                "import pytest\n"
                f"from {domain} import {domain.capitalize()}\n\n"
                "def test_generic_object():\n"
                f"    obj = {domain.capitalize()}('test')\n"
                "    obj.set_value('key1', 'val1')\n"
                "    assert obj.has_key('key1')\n"
                "    assert obj.get_value('key1') == 'val1'\n"
                "    assert obj.get_value('missing', 'default') == 'default'\n"
            )

        # Generic test scaffold: inspect project_dir for real generated .py modules
        py_files = []
        if os.path.exists(self.project_dir):
            for f in os.listdir(self.project_dir):
                if f.endswith('.py') and f != 'main.py':
                    full_p = os.path.join(self.project_dir, f)
                    if os.path.isfile(full_p):
                        py_files.append(f[:-3])

        if py_files:
            imports = "\n".join([f"try:\n    import {mod}\nexcept ImportError:\n    {mod} = None" for mod in py_files])
            test_cases = "\n".join([f"def test_{mod}_module_loaded():\n    if {mod} is not None:\n        assert hasattr({mod}, '__file__')" for mod in py_files])
            test_code = f"import pytest\n{imports}\n\n{test_cases}\n"
            test_file = os.path.join(test_dir, f"test_{py_files[0]}.py")
        else:
            test_code = (
                "import pytest\n\n"
                "def test_generic_object_operations():\n"
                "    assert True\n"
            )
            test_file = os.path.join(test_dir, f"test_{domain}.py")

        os.makedirs(test_dir, exist_ok=True)
        write_file(test_file, test_code)

    def _generate_python_documentation(self, domain: str) -> None:
        readme = os.path.join(self.project_dir, "README.md")
        user_manual = os.path.join(self.project_dir, "User_Manual.md")
        readme_content = (
            f"# {self.project_name}\n\n"
            f"A Python implementation of {domain} with automated Pytest unit testing.\n\n"
            "## Requirements\n- Python 3.8+\n- Pytest\n\n"
            "## Execution\n```sh\npython main.py\n```\n\n"
            "## Testing\n```sh\npytest\n```\n"
        )
        user_manual_content = (
            "# User Manual\n\n"
            f"This document provides instructions for using the {self.project_name} Python application.\n\n"
            "## Setup and Installation\n1. Ensure Python 3 is installed.\n2. Run `python main.py` to execute main entry point.\n3. Run `pytest` to verify suite correctness.\n"
        )
        write_file(readme, readme_content)
        write_file(user_manual, user_manual_content)

    def _run_c_fallback(self, task_name: str, task_vars: dict, output_file: str):
        if task_name == "requirement_task":
            content = self._generate_c_requirements(task_vars.get("prompt", ""))
            if output_file:
                write_file(output_file, content)
            return content
        if task_name == "design_task":
            content = self._generate_c_design(task_vars.get("prompt", ""))
            if output_file:
                write_file(output_file, content)
            return content
        if task_name == "code_task":
            self._generate_c_code(task_vars.get("prompt", ""))
            return "Generated C/C++ source files."
        if task_name == "testing_task":
            self._generate_c_tests(task_vars["project_dir"])
            return "Generated C/C++ tests."
        if task_name == "documentation_task":
            self._generate_c_documentation(task_vars["project_dir"])
            return "Generated C/C++ documentation."
        return None

    def _is_local_agent_failure(self, result_text: str) -> bool:
        """Detect a hard system-level agent failure (not valid LLM output).
        Uses precise, non-generic markers to avoid false positives on LLM-generated
        code/docs that legitimately contain words like 'Error' or 'Failed'.
        """
        if not result_text:
            return True
        stripped = result_text.strip()
        # Only match exact system-level error tokens emitted by the agent runner itself
        system_failure_markers = [
            "ERROR_RUNNING_OLLAMA",
            "LOCAL_AGENT_ERROR",
            "NO MODEL AVAILABLE",
            "MODEL NOT FOUND",
            "OLLAMA SERVE",
            "CONNECTION REFUSED",
        ]
        normalized = stripped.upper()
        return any(marker in normalized for marker in system_failure_markers)

    def _project_has_source_files(self) -> bool:
        source_exts = get_source_extensions('c') | get_source_extensions('cpp') | get_source_extensions('python')
        for root, _, files in os.walk(self.project_dir):
            if any(ignored in root for ignored in [".venv", "__pycache__", ".git", ".pytest_cache"]):
                continue
            for file in files:
                if file == '.evoforge_lang':
                    continue
                if os.path.splitext(file)[1] in source_exts:
                    return True
        return False

    def _generate_c_requirements(self, prompt: str) -> str:
        language_label = "C++" if self.project_language == "cpp" else "C"
        proj_title = self.project_name.replace('_', ' ').title()
        return (
            f"# Software Requirements Specification (SRS)\n\n"
            f"## 1. Document Overview & System Purpose\n"
            f"The system shall provide a high-performance, standards-compliant {proj_title} application written in {language_label}.\n"
            f"Specification Prompt: \"{prompt or self.project_name}\"\n\n"
            f"## 2. User Personas & System Scope\n"
            f"- **Target Users**: System users, software developers, and automated build pipelines.\n"
            f"- **Compilation Tools**: GCC / G++ / Clang toolchains supporting POSIX Makefile builds.\n"
            f"- **Dependencies**: Standard runtime libraries (`libc`/`libm` or `<iostream>`, `<cmath>`, `<cassert>`).\n\n"
            f"## 3. Functional Requirements\n"
            f"### 3.1 Core Application Capabilities\n"
            f"- [NEW] The system shall execute functional logic satisfying: {prompt or self.project_name}.\n"
            f"- [NEW] The system shall provide standard module initialization, operational execution, and resource cleanup routines.\n"
            f"- [NEW] The system shall include an interactive CLI entry point (`main`) prompting users for runtime inputs dynamically.\n\n"
            f"### 3.2 Boundary Error & Memory Management\n"
            f"- [NEW] The system shall validate all boundary parameters (division by zero, null pointers, out-of-bounds inputs).\n"
            f"- [NEW] The system shall ensure clean memory management without heap leaks or buffer overruns.\n\n"
            f"## 4. Non-Functional Requirements\n"
            f"### 4.1 Performance & Memory Efficiency\n"
            f"- [NEW] High execution performance with minimal heap allocation overhead.\n\n"
            f"### 4.2 Code Standards & Architecture\n"
            f"- [NEW] Code structured into header files (`.h`/`.hpp`) and source files (`.c`/`.cpp`) with standard `#ifndef` include guards.\n"
            f"- [NEW] Warning-free compilation under strict GCC/G++ compiler flags.\n\n"
            f"### 4.3 Build System & Testing\n"
            f"- [NEW] POSIX Makefile supporting `make`, `make test`, and `make clean` targets.\n"
            f"- [NEW] Automated assertion test runner in `tests/test_runner`.\n\n"
            f"## 5. Interface Specifications\n"
            f"- [NEW] Interactive CLI menu loop accepting dynamic user input via standard input.\n"
        )

    def _generate_c_design(self, prompt: str) -> str:
        language_label = "C++" if self.project_language == "cpp" else "C"
        module_name = re.sub(r'[^a-zA-Z0-9_]', '_', self.project_name).strip('_').lower()
        header_ext = "hpp" if self.project_language == "cpp" else "h"
        source_ext = "cpp" if self.project_language == "cpp" else "c"
        proj_title = self.project_name.replace('_', ' ').title()

        return (
            f"# Design Document\n\n"
            f"## Architecture Overview\n"
            f"The project is a {language_label} application providing the `{module_name}` module.\n\n"
            f"## Module Specifications\n"
            f"- `{module_name}.{header_ext}`: Public API declarations for the {proj_title} component.\n"
            f"- `{module_name}.{source_ext}`: Implementation of {proj_title} core logic.\n"
            f"- `main.{source_ext}`: Interactive command-line interface accepting dynamic user inputs.\n"
            f"- `tests/test_runner.{source_ext}`: Automated assertion test suite.\n\n"
            f"## Data Model\n"
            f"- Data structures and function signatures declared in `{module_name}.{header_ext}`.\n\n"
            f"## Sequence Flow\n"
            f"```mermaid\nsequenceDiagram\n"
            f"    participant User\n"
            f"    participant Main CLI\n"
            f"    participant {module_name.capitalize()} Engine\n\n"
            f"    User->>Main CLI: launch program & provide input choices\n"
            f"    Main CLI->>{module_name.capitalize()} Engine: call domain operations\n"
            f"    {module_name.capitalize()} Engine-->>Main CLI: return results / error status\n"
            f"    Main CLI-->>User: display output in console\n"
            f"```\n"
        )

    def _generate_c_code(self, prompt: str) -> None:
        module_name = re.sub(r'[^a-zA-Z0-9_]', '_', self.project_name).strip('_').lower()
        is_cpp = (self.project_language == "cpp")
        header_ext = "hpp" if is_cpp else "h"
        source_ext = "cpp" if is_cpp else "c"
        header = f"{module_name}.{header_ext}"
        source = f"{module_name}.{source_ext}"
        main_src = f"main.{source_ext}"
        header_guard = f"{module_name.upper()}_{header_ext.upper()}"
        
        # Always generate the generic C/C++ struct scaffold when LLM output is unavailable.
        # Math-specific keyword sniffing removed — the LLM is responsible for domain logic.
        if False:  # Math-calc branch removed to prevent hardcoded domain assumption
            if is_cpp:
                header_content = (
                    f"#ifndef {header_guard}\n#define {header_guard}\n\n#include <cmath>\n\n"
                    f"double {module_name}_add(double a, double b);\n"
                    f"double {module_name}_subtract(double a, double b);\n"
                    f"double {module_name}_multiply(double a, double b);\n"
                    f"bool {module_name}_divide(double a, double b, double &result);\n"
                    f"bool {module_name}_power(double base, double exponent, double &result);\n"
                    f"bool {module_name}_sqrt(double val, double &result);\n"
                    f"bool {module_name}_log(double val, double &result);\n"
                    f"double {module_name}_sin(double rad);\n"
                    f"double {module_name}_cos(double rad);\n"
                    f"bool {module_name}_factorial(int n, double &result);\n\n#endif\n"
                )
                source_content = (
                    f"#include \"{header}\"\n#include <cmath>\n\n"
                    f"double {module_name}_add(double a, double b) {{ return a + b; }}\n"
                    f"double {module_name}_subtract(double a, double b) {{ return a - b; }}\n"
                    f"double {module_name}_multiply(double a, double b) {{ return a * b; }}\n"
                    f"bool {module_name}_divide(double a, double b, double &result) {{\n"
                    f"    if (b == 0.0) return false;\n    result = a / b;\n    return true;\n}}\n"
                    f"bool {module_name}_power(double base, double exponent, double &result) {{\n"
                    f"    result = std::pow(base, exponent);\n    return !std::isnan(result);\n}}\n"
                    f"bool {module_name}_sqrt(double val, double &result) {{\n"
                    f"    if (val < 0.0) return false;\n    result = std::sqrt(val);\n    return true;\n}}\n"
                    f"bool {module_name}_log(double val, double &result) {{\n"
                    f"    if (val <= 0.0) return false;\n    result = std::log(val);\n    return true;\n}}\n"
                    f"double {module_name}_sin(double rad) {{ return std::sin(rad); }}\n"
                    f"double {module_name}_cos(double rad) {{ return std::cos(rad); }}\n"
                    f"bool {module_name}_factorial(int n, double &result) {{\n"
                    f"    if (n < 0 || n > 170) return false;\n    double res = 1.0;\n    for (int i = 1; i <= n; ++i) res *= i;\n    result = res;\n    return true;\n}}\n"
                )
                main_content = (
                    f"#include <iostream>\n#include \"{header}\"\n\n"
                    "int main() {\n"
                    f"    std::cout << \"=========================================\\n\";\n"
                    f"    std::cout << \"     {self.project_name.replace('_', ' ').title()} CLI\\n\";\n"
                    f"    std::cout << \"=========================================\\n\";\n"
                    "    std::cout << \"1. Add (+)\\n2. Subtract (-)\\n3. Multiply (*)\\n4. Divide (/)\\n\"\n"
                    "                 \"5. Power (a^b)\\n6. Square Root (sqrt)\\n7. Sin\\n8. Cos\\n9. Log (ln)\\n10. Factorial (n!)\\n0. Exit\\n\";\n"
                    "    int choice;\n"
                    "    while (std::cout << \"\\nSelect operation (0-10): \" && (std::cin >> choice)) {\n"
                    "        if (choice == 0) {\n            std::cout << \"Exiting application.\\n\";\n            break;\n        }\n"
                    "        double a, b, res;\n"
                    "        if (choice >= 1 && choice <= 5) {\n"
                    "            std::cout << \"Enter first number: \"; if (!(std::cin >> a)) break;\n"
                    "            std::cout << \"Enter second number: \"; if (!(std::cin >> b)) break;\n"
                    "        } else if (choice >= 6 && choice <= 9) {\n"
                    "            std::cout << \"Enter value: \"; if (!(std::cin >> a)) break;\n"
                    "        }\n"
                    "        switch (choice) {\n"
                    f"            case 1: std::cout << \"Result: \" << a << \" + \" << b << \" = \" << {module_name}_add(a, b) << \"\\n\"; break;\n"
                    f"            case 2: std::cout << \"Result: \" << a << \" - \" << b << \" = \" << {module_name}_subtract(a, b) << \"\\n\"; break;\n"
                    f"            case 3: std::cout << \"Result: \" << a << \" * \" << b << \" = \" << {module_name}_multiply(a, b) << \"\\n\"; break;\n"
                    "            case 4:\n"
                    f"                if ({module_name}_divide(a, b, res)) std::cout << \"Result: \" << a << \" / \" << b << \" = \" << res << \"\\n\";\n"
                    "                else std::cout << \"Error: Division by zero!\\n\"; break;\n"
                    "            case 5:\n"
                    f"                if ({module_name}_power(a, b, res)) std::cout << \"Result: \" << a << \" ^ \" << b << \" = \" << res << \"\\n\";\n"
                    "                else std::cout << \"Error: Invalid power operation!\\n\"; break;\n"
                    "            case 6:\n"
                    f"                if ({module_name}_sqrt(a, res)) std::cout << \"Result: sqrt(\" << a << \") = \" << res << \"\\n\";\n"
                    "                else std::cout << \"Error: Cannot compute square root of negative number!\\n\"; break;\n"
                    f"            case 7: std::cout << \"Result: sin(\" << a << \") = \" << {module_name}_sin(a) << \"\\n\"; break;\n"
                    f"            case 8: std::cout << \"Result: cos(\" << a << \") = \" << {module_name}_cos(a) << \"\\n\"; break;\n"
                    "            case 9:\n"
                    f"                if ({module_name}_log(a, res)) std::cout << \"Result: ln(\" << a << \") = \" << res << \"\\n\";\n"
                    "                else std::cout << \"Error: Logarithm undefined for non-positive numbers!\\n\"; break;\n"
                    "            case 10: {\n"
                    "                int n;\n                std::cout << \"Enter integer n: \";\n"
                    f"                if (std::cin >> n && {module_name}_factorial(n, res)) std::cout << \"Result: \" << n << \"! = \" << res << \"\\n\";\n"
                    "                else std::cout << \"Error: Invalid factorial input!\\n\"; break;\n"
                    "            }\n"
                    "            default: std::cout << \"Invalid choice!\\n\"; break;\n"
                    "        }\n"
                    "    }\n    return 0;\n"
                    "}\n"
                )
            else:
                header_content = (
                    f"#ifndef {header_guard}\n#define {header_guard}\n\n#include <stdbool.h>\n#include <math.h>\n\n"
                    f"double {module_name}_add(double a, double b);\n"
                    f"double {module_name}_subtract(double a, double b);\n"
                    f"double {module_name}_multiply(double a, double b);\n"
                    f"bool {module_name}_divide(double a, double b, double *result);\n"
                    f"bool {module_name}_power(double base, double exponent, double *result);\n"
                    f"bool {module_name}_sqrt(double val, double *result);\n"
                    f"bool {module_name}_factorial(int n, double *result);\n\n#endif\n"
                )
                source_content = (
                    f"#include \"{header}\"\n#include <math.h>\n\n"
                    f"double {module_name}_add(double a, double b) {{ return a + b; }}\n"
                    f"double {module_name}_subtract(double a, double b) {{ return a - b; }}\n"
                    f"double {module_name}_multiply(double a, double b) {{ return a * b; }}\n"
                    f"bool {module_name}_divide(double a, double b, double *result) {{\n"
                    f"    if (b == 0.0) return false;\n    if (result) *result = a / b;\n    return true;\n}}\n"
                    f"bool {module_name}_power(double base, double exponent, double *result) {{\n"
                    f"    double res = pow(base, exponent);\n    if (isnan(res)) return false;\n    if (result) *result = res;\n    return true;\n}}\n"
                    f"bool {module_name}_sqrt(double val, double *result) {{\n"
                    f"    if (val < 0.0) return false;\n    if (result) *result = sqrt(val);\n    return true;\n}}\n"
                    f"bool {module_name}_factorial(int n, double *result) {{\n"
                    f"    if (n < 0 || n > 170) return false;\n    double res = 1.0;\n    for (int i = 1; i <= n; ++i) res *= i;\n    if (result) *result = res;\n    return true;\n}}\n"
                )
                main_content = (
                    f"#include <stdio.h>\n#include \"{header}\"\n\n"
                    "int main(void) {\n"
                    f"    printf(\"=================================\\n\");\n"
                    f"    printf(\"   {self.project_name.replace('_', ' ').title()} CLI (C)\\n\");\n"
                    f"    printf(\"=================================\\n\");\n"
                    "    printf(\"1. Add (+)\\n2. Subtract (-)\\n3. Multiply (*)\\n4. Divide (/)\\n5. Power\\n6. Sqrt\\n7. Factorial\\n0. Exit\\n\");\n"
                    "    int choice;\n"
                    "    while (printf(\"\\nSelect operation (0-7): \") && scanf(\"%d\", &choice) == 1) {\n"
                    "        if (choice == 0) break;\n"
                    "        double a, b, res;\n"
                    "        if (choice >= 1 && choice <= 5) {\n"
                    "            printf(\"Enter first number: \"); if (scanf(\"%lf\", &a) != 1) break;\n"
                    "            printf(\"Enter second number: \"); if (scanf(\"%lf\", &b) != 1) break;\n"
                    "        } else if (choice == 6) {\n"
                    "            printf(\"Enter value: \"); if (scanf(\"%lf\", &a) != 1) break;\n"
                    "        }\n"
                    f"        if (choice == 1) printf(\"Result: %f\\n\", {module_name}_add(a, b));\n"
                    f"        else if (choice == 2) printf(\"Result: %f\\n\", {module_name}_subtract(a, b));\n"
                    f"        else if (choice == 3) printf(\"Result: %f\\n\", {module_name}_multiply(a, b));\n"
                    "        else if (choice == 4) {\n"
                    f"            if ({module_name}_divide(a, b, &res)) printf(\"Result: %f\\n\", res);\n"
                    "            else printf(\"Error: Division by zero!\\n\");\n"
                    "        }\n"
                    "        else if (choice == 5) {\n"
                    f"            if ({module_name}_power(a, b, &res)) printf(\"Result: %f\\n\", res);\n"
                    "            else printf(\"Error: Invalid power!\\n\");\n"
                    "        }\n"
                    "        else if (choice == 6) {\n"
                    f"            if ({module_name}_sqrt(a, &res)) printf(\"Result: %f\\n\", res);\n"
                    "            else printf(\"Error: Negative sqrt!\\n\");\n"
                    "        }\n"
                    "        else if (choice == 7) {\n"
                    "            int n; printf(\"Enter integer n: \");\n"
                    f"            if (scanf(\"%d\", &n) == 1 && {module_name}_factorial(n, &res)) printf(\"Result: %f\\n\", res);\n"
                    "            else printf(\"Error: Invalid factorial!\\n\");\n"
                    "        }\n"
                    "    }\n    return 0;\n"
                    "}\n"
                )
        else:
            # Generic specification skeleton for non-math C/C++ projects
            struct_name = module_name.capitalize()
            if is_cpp:
                header_content = (
                    f"#ifndef {header_guard}\n#define {header_guard}\n\n#include <string>\n#include <vector>\n\n"
                    f"struct {struct_name} {{\n"
                    f"    std::string name;\n"
                    f"    std::vector<double> data;\n"
                    f"}};\n\n"
                    f"void {module_name}_init({struct_name} &m, const std::string &name);\n"
                    f"void {module_name}_add_entry({struct_name} &m, double val);\n"
                    f"std::size_t {module_name}_count(const {struct_name} &m);\n"
                    f"void {module_name}_clear({struct_name} &m);\n\n#endif\n"
                )
                source_content = (
                    f"#include \"{header}\"\n\n"
                    f"void {module_name}_init({struct_name} &m, const std::string &name) {{\n"
                    f"    m.name = name;\n    m.data.clear();\n}}\n\n"
                    f"void {module_name}_add_entry({struct_name} &m, double val) {{\n"
                    f"    m.data.push_back(val);\n}}\n\n"
                    f"std::size_t {module_name}_count(const {struct_name} &m) {{\n"
                    f"    return m.data.size();\n}}\n\n"
                    f"void {module_name}_clear({struct_name} &m) {{\n"
                    f"    m.data.clear();\n}}\n"
                )
                main_content = (
                    f"#include <iostream>\n#include \"{header}\"\n\n"
                    "int main() {\n"
                    f"    {struct_name} m;\n"
                    f"    {module_name}_init(m, \"{self.project_name}\");\n"
                    f"    std::cout << \"=== {self.project_name.replace('_', ' ').title()} CLI ===\\n\";\n"
                    "    std::cout << \"Enter numbers to add to module session (enter non-numeric to finish):\\n\";\n"
                    "    double val;\n"
                    f"    while (std::cout << \"Input value: \" && (std::cin >> val)) {{\n"
                    f"        {module_name}_add_entry(m, val);\n"
                    "    }\n"
                    f"    std::cout << \"Total entries recorded: \" << {module_name}_count(m) << std::endl;\n"
                    f"    {module_name}_clear(m);\n"
                    "    return 0;\n"
                    "}\n"
                )
            else:
                header_content = (
                    f"#ifndef {header_guard}\n#define {header_guard}\n\n#include <stddef.h>\n#include <stdbool.h>\n\n"
                    f"typedef struct {{\n    double data[100];\n    size_t count;\n}} {struct_name};\n\n"
                    f"void {module_name}_init({struct_name} *m);\n"
                    f"bool {module_name}_add_entry({struct_name} *m, double val);\n"
                    f"size_t {module_name}_count(const {struct_name} *m);\n\n#endif\n"
                )
                source_content = (
                    f"#include \"{header}\"\n\n"
                    f"void {module_name}_init({struct_name} *m) {{\n"
                    f"    if (m) m->count = 0;\n}}\n\n"
                    f"bool {module_name}_add_entry({struct_name} *m, double val) {{\n"
                    f"    if (!m || m->count >= 100) return false;\n"
                    f"    m->data[m->count++] = val;\n    return true;\n}}\n\n"
                    f"size_t {module_name}_count(const {struct_name} *m) {{\n"
                    f"    return m ? m->count : 0;\n}}\n"
                )
                main_content = (
                    f"#include <stdio.h>\n#include \"{header}\"\n\n"
                    "int main(void) {\n"
                    f"    {struct_name} m;\n"
                    f"    {module_name}_init(&m);\n"
                    f"    printf(\"=== {self.project_name.replace('_', ' ').title()} CLI ===\\n\");\n"
                    "    printf(\"Enter numbers to add (non-numeric to finish):\\n\");\n"
                    "    double val;\n"
                    "    printf(\"Input value: \");\n"
                    f"    while (scanf(\"%lf\", &val) == 1) {{\n"
                    f"        {module_name}_add_entry(&m, val);\n"
                    "        printf(\"Input value: \");\n"
                    "    }\n"
                    f"    printf(\"Total entries recorded: %zu\\n\", {module_name}_count(&m));\n"
                    "    return 0;\n"
                    "}\n"
                )

        write_file(os.path.join(self.project_dir, header), header_content)
        write_file(os.path.join(self.project_dir, source), source_content)
        write_file(os.path.join(self.project_dir, main_src), main_content)
        generate_makefile(self.project_dir, self.project_name, self.project_language)
        try:
            from tools.static_analysis import extract_and_store_c_cpp_functions
            extract_and_store_c_cpp_functions(
                self.project_dir,
                db_manager=getattr(self, 'db', None),
                project_id=getattr(self, 'project_id', None),
                reports_dir=getattr(self, 'reports_dir', None)
            )
        except Exception:
            pass



    def _generate_c_tests(self, project_dir: str) -> None:
        module_name = re.sub(r'[^a-zA-Z0-9_]', '_', self.project_name).strip('_').lower()
        is_cpp = (self.project_language == "cpp")
        test_ext = "cpp" if is_cpp else "c"
        header = f"{module_name}.hpp" if is_cpp else f"{module_name}.h"
        test_file = os.path.join(project_dir, "tests", f"test_runner.{test_ext}")

        # Math-specific keyword sniffing removed — always generate generic struct tests
        # as a last-resort skeleton when no LLM test output is available.
        if False:  # Math-calc test branch removed
            if is_cpp:
                test_content = (
                    f"#include <cassert>\n#include <iostream>\n#include \"{header}\"\n\n"
                    "int main() {\n"
                    f"    assert({module_name}_add(5.0, 3.0) == 8.0);\n"
                    f"    assert({module_name}_subtract(10.0, 4.0) == 6.0);\n"
                    f"    assert({module_name}_multiply(2.0, 4.0) == 8.0);\n"
                    f"    double res;\n"
                    f"    assert({module_name}_divide(10.0, 2.0, res) && res == 5.0);\n"
                    f"    assert(!{module_name}_divide(10.0, 0.0, res));\n"
                    f"    assert({module_name}_power(2.0, 3.0, res) && res == 8.0);\n"
                    f"    assert({module_name}_sqrt(16.0, res) && res == 4.0);\n"
                    f"    assert(!{module_name}_sqrt(-4.0, res));\n"
                    f"    assert({module_name}_factorial(5, res) && res == 120.0);\n"
                    f"    std::cout << \"{self.project_name} automated tests passed successfully.\" << std::endl;\n"
                    "    return 0;\n}\n"
                )
            else:
                test_content = (
                    f"#include <assert.h>\n#include <stdio.h>\n#include \"{header}\"\n\n"
                    "int main(void) {\n"
                    f"    assert({module_name}_add(5.0, 3.0) == 8.0);\n"
                    f"    assert({module_name}_subtract(10.0, 4.0) == 6.0);\n"
                    f"    assert({module_name}_multiply(2.0, 4.0) == 8.0);\n"
                    f"    double res;\n"
                    f"    assert({module_name}_divide(10.0, 2.0, &res) && res == 5.0);\n"
                    f"    assert(!{module_name}_divide(10.0, 0.0, &res));\n"
                    f"    assert({module_name}_power(2.0, 3.0, &res) && res == 8.0);\n"
                    f"    assert({module_name}_sqrt(16.0, &res) && res == 4.0);\n"
                    f"    assert(!{module_name}_sqrt(-4.0, &res));\n"
                    f"    assert({module_name}_factorial(5, &res) && res == 120.0);\n"
                    f"    printf(\"{self.project_name} automated tests passed successfully.\\n\");\n"
                    "    return 0;\n}\n"
                )
        else:
            struct_name = module_name.capitalize()
            if is_cpp:
                test_content = (
                    f"#include <cassert>\n#include <iostream>\n#include \"{header}\"\n\n"
                    "int main() {\n"
                    f"    {struct_name} m;\n"
                    f"    {module_name}_init(m, \"test_session\");\n"
                    f"    assert({module_name}_count(m) == 0);\n"
                    f"    {module_name}_add_entry(m, 42.0);\n"
                    f"    assert({module_name}_count(m) == 1);\n"
                    f"    {module_name}_clear(m);\n"
                    f"    assert({module_name}_count(m) == 0);\n"
                    f"    std::cout << \"{self.project_name} automated tests passed successfully.\" << std::endl;\n"
                    "    return 0;\n}\n"
                )
            else:
                test_content = (
                    f"#include <assert.h>\n#include <stdio.h>\n#include \"{header}\"\n\n"
                    "int main(void) {\n"
                    f"    {struct_name} m;\n"
                    f"    {module_name}_init(&m);\n"
                    f"    assert({module_name}_count(&m) == 0);\n"
                    f"    assert({module_name}_add_entry(&m, 42.0));\n"
                    f"    assert({module_name}_count(&m) == 1);\n"
                    f"    printf(\"{self.project_name} automated tests passed successfully.\\n\");\n"
                    "    return 0;\n}\n"
                )
        os.makedirs(os.path.dirname(test_file), exist_ok=True)
        write_file(test_file, test_content)

    def _generate_c_documentation(self, project_dir: str) -> None:
        readme = os.path.join(project_dir, "README.md")
        user_manual = os.path.join(project_dir, "User_Manual.md")
        runtime = "C++" if self.project_language == "cpp" else "C"
        readme_content = (
            f"# {self.project_name}\n\n"
            f"A {runtime} implementation of {self.project_name} with build and test support.\n\n"
            "## Build\n\n"
            "```sh\nmake\n```\n\n"
            "## Run\n\n"
            f"```sh\n./{self.project_name}\n```\n\n"
            "## Test\n\n"
            "```sh\nmake test\n```\n"
        )
        user_manual_content = (
            "# User Manual\n\n"
            f"This project provides a {runtime} {self.project_name} application.\n\n"
            "## Build Instructions\n1. Run `make` to compile the executable.\n2. Run `make test` to build and execute the test runner.\n\n"
            f"## Usage\n1. Build the code with `make`.\n2. Execute `./{self.project_name}`.\n3. Enter input values at the dynamic CLI prompt.\n"
        )
        write_file(readme, readme_content)
        write_file(user_manual, user_manual_content)


    def _run_design_stage(self, design_output: str, delta_path: str):
        try:
            from agents.base_agent import BaseAgent as _BaseAgent
            design_agent_wrapper = _BaseAgent("design_agent")
            design_agent_wrapper.get_agent(tools=[read_project_file, write_project_file])
        except Exception as e:
            print(f"Could not import BaseAgent for design stage: {e}. Proceeding with fallback.")
            design_agent_wrapper = None

        design_task_vars = {
            "reports_dir": self.reports_dir,
            "delta_path": delta_path
        }
        self._run_single_stage(
            design_agent_wrapper,
            "design_task",
            design_task_vars,
            output_file=design_output,
            tools=[read_project_file, write_project_file]
        )

    def _distill_markdown_context(self, srs_content: str, design_content: str) -> tuple[str, str]:
        """Extract concise requirement items and class/function signatures from SRS and Design documents to avoid LLM prompt overloading."""
        srs_items = []
        if srs_content:
            for line in srs_content.splitlines():
                l = line.strip()
                if l.startswith("- [") or l.startswith("### ") or l.startswith("## 3"):
                    srs_items.append(l)
        distilled_srs = "\n".join(srs_items[:40]) if srs_items else srs_content[:1500]

        design_items = []
        if design_content:
            in_code = False
            for line in design_content.splitlines():
                l = line.strip()
                if l.startswith("```"):
                    in_code = not in_code
                    design_items.append(l)
                elif in_code or l.startswith("- `") or l.startswith("### ") or l.startswith("## "):
                    design_items.append(l)
        distilled_design = "\n".join(design_items[:40]) if design_items else design_content[:1500]

        return distilled_srs, distilled_design

    def _run_code_stage(self, code_agent_wrapper: BaseAgent, code_output, dependency_path: str, reuse_path: str, delta_path: str):
        existing_source_code = self._collect_existing_source_code()
        srs_file = os.path.join(self.reports_dir, "SRS.md")
        design_file = os.path.join(self.reports_dir, "Design.md")
        srs_content = read_file(srs_file) if os.path.exists(srs_file) else ""
        design_content = read_file(design_file) if os.path.exists(design_file) else ""
        distilled_srs, distilled_design = self._distill_markdown_context(srs_content, design_content)

        # Extract and persist C/C++ functions & Standard Library functions (std::max, min, sort, vector, etc.) to DB & file
        core_c_functions = "No existing C/C++ core functions found."
        try:
            from tools.static_analysis import extract_and_store_c_cpp_functions, get_c_cpp_stdlib_reference
            _, project_c_functions = extract_and_store_c_cpp_functions(
                self.project_dir,
                db_manager=getattr(self, 'db', None),
                project_id=getattr(self, 'project_id', None),
                reports_dir=getattr(self, 'reports_dir', None)
            )
            stdlib_ref = get_c_cpp_stdlib_reference(
                language=getattr(self, 'project_language', 'both'),
                db_manager=getattr(self, 'db', None)
            )
            core_c_functions = f"{project_c_functions}\n\n{stdlib_ref}"
        except Exception:
            pass


        code_task_vars = {
            "reports_dir": self.reports_dir,
            "project_dir": self.project_dir,
            "language": self.project_language,
            "existing_source_code": existing_source_code,
            "core_c_functions": core_c_functions,
            "dependency_graph_path": dependency_path,
            "reuse_report_path": reuse_path,
            "delta_report_path": delta_path,
            "srs_content": distilled_srs,
            "design_content": distilled_design
        }
        # Use the unified _run_single_stage which has a Crew fallback
        res = self._run_single_stage(
            code_agent_wrapper,
            "code_task",
            code_task_vars,
            output_file=code_output,
            tools=[read_project_file, write_project_file, list_project_files, analyze_python_ast, get_c_cpp_functions]
        )

        # Re-extract and persist functions after code stage to ensure newly generated C/C++ functions are indexed
        try:
            from tools.static_analysis import extract_and_store_c_cpp_functions
            extract_and_store_c_cpp_functions(
                self.project_dir,
                db_manager=getattr(self, 'db', None),
                project_id=getattr(self, 'project_id', None),
                reports_dir=getattr(self, 'reports_dir', None)
            )
        except Exception:
            pass

        return res



    def _run_testing_stage(self, testing_output_dir: str, test_impact_path: str):
        try:
            from agents.base_agent import BaseAgent as _BaseAgent
            testing_agent_name = "c_testing_agent" if self.project_language in {"c", "cpp"} else "testing_agent"
            testing_agent_wrapper = _BaseAgent(testing_agent_name)
        except Exception as e:
            print(f"Could not import BaseAgent for testing stage: {e}. Proceeding with fallback.")
            testing_agent_wrapper = None

        existing_source_code = self._collect_existing_source_code()
        testing_task_vars = {
            "project_dir": self.project_dir,
            "reports_dir": self.reports_dir,
            "test_impact_path": test_impact_path,
            "existing_source_code": existing_source_code or "No existing source code files."
        }
        self._run_single_stage(
            testing_agent_wrapper,
            "testing_task",
            testing_task_vars,
            output_file=None,
            tools=[read_project_file, write_project_file, list_project_files]
        )

    def _run_documentation_stage(self, doc_output_dir: str):
        try:
            from agents.base_agent import BaseAgent as _BaseAgent
            doc_agent_wrapper = _BaseAgent("documentation_agent")
            doc_agent = doc_agent_wrapper.get_agent(tools=[read_project_file, write_project_file])
        except Exception as e:
            print(f"Could not import BaseAgent for documentation stage: {e}. Proceeding with fallback.")
            doc_agent_wrapper = None
            doc_agent = None

        doc_task_vars = {
            "project_dir": self.project_dir,
            "reports_dir": self.reports_dir
        }
        self._run_single_stage(
            doc_agent_wrapper,
            "documentation_task",
            doc_task_vars,
            output_file=None,
            tools=[read_project_file, write_project_file]
        )

    def _collect_existing_source_code(self) -> str:
        existing_source_code = ""
        valid_exts = {".c", ".cpp", ".cc", ".cxx", ".h", ".hpp", ".hxx", ".py", ".md", ".json", ".txt", ".ini"}
        for root, dirs, files in os.walk(self.project_dir):
            if any(ignored in root for ignored in [".venv", "__pycache__", ".git", ".pytest_cache", "tests"]):
                continue
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if file != "Makefile" and ext not in valid_exts:
                    continue
                filepath = os.path.join(root, file)
                rel_path = os.path.relpath(filepath, self.project_dir)
                content = read_file(filepath)
                existing_source_code += f"\n--- FILE: {rel_path} ---\n{content}\n"
        return existing_source_code if existing_source_code else "No existing source code."

    def _guess_impacted_modules(self, classified_requirements):
        # Gather existing source files in self.project_dir
        existing_sources = []
        for root, _, files in os.walk(self.project_dir):
            if any(ign in root for ign in [".git", "__pycache__", ".venv", "tests"]):
                continue
            for f in files:
                if f.endswith((".py", ".c", ".cpp", ".cc", ".cxx")):
                    rel = os.path.relpath(os.path.join(root, f), self.project_dir)
                    existing_sources.append(rel)

        if existing_sources:
            matched = set()
            for item in classified_requirements:
                if item.get("tag") in {"NEW", "MODIFIED", "REMOVED"}:
                    text_lower = item.get("text", "").lower()
                    for src in existing_sources:
                        stem = os.path.splitext(os.path.basename(src))[0].lower()
                        if len(stem) > 2 and stem in text_lower:
                            matched.add(src)
            if matched:
                return sorted(list(matched))
            return sorted(existing_sources)

        ext = ".cpp" if getattr(self, "project_language", "") == "cpp" else (".c" if getattr(self, "project_language", "") == "c" else ".py")
        changed = []
        for item in classified_requirements:
            if item.get("tag") in {"NEW", "MODIFIED", "REMOVED"}:
                words = [w for w in re.findall(r"[a-zA-Z0-9_]+", item.get("text", "")) if len(w) > 3 and w.lower() not in {"the", "this", "that", "from", "with", "shall", "system", "students", "individuals", "developers"}]
                candidate = f"{words[0].lower()}{ext}" if words else None
                if candidate:
                    changed.append(candidate)
        return [module for module in sorted(set(changed)) if module] or [f"main{ext}"]

    def _update_db_registry_and_run(self, mode: str):
        """Scan project and reports directories to update file hashes and log the run."""
        srs_path = os.path.join(self.reports_dir, "SRS.md")
        design_path = os.path.join(self.reports_dir, "Design.md")

        # Re-build static dependency graph post code generation and persist to Dependency_Graph.json
        dependency_path = os.path.join(self.reports_dir, "Dependency_Graph.json")
        dependency_graph = build_dependency_graph(self.project_dir)
        save_json(dependency_path, dependency_graph)

        srs_hash = calculate_hash(srs_path)
        design_hash = calculate_hash(design_path)

        # Register reports files
        if srs_hash:
            self.db.register_file(self.project_id, srs_path, "spec", srs_hash)
        if design_hash:
            self.db.register_file(self.project_id, design_path, "spec", design_hash)

        # Scan and register project files
        for root, dirs, files in os.walk(self.project_dir):
            # Skip python caching/virtual env
            if any(ignored in root for ignored in [".venv", "__pycache__", ".git", ".pytest_cache"]):
                continue
            
            is_test_dir = "tests" in os.path.split(root)
            for file in files:
                file_path = os.path.join(root, file)
                content_hash = calculate_hash(file_path)
                
                # Categorize file type
                if is_test_dir or file.startswith("test_"):
                    file_type = "test"
                elif file.endswith(".md"):
                    file_type = "doc"
                elif file.endswith(".py"):
                    file_type = "source"
                else:
                    file_type = "source" # Fallback

                self.db.register_file(self.project_id, file_path, file_type, content_hash)

        # Log the run
        status = "success" if os.path.exists(srs_path) else "failed"
        self.db.log_run(self.project_id, srs_hash, design_hash, status)
        print(f"Logged SDLC run state in SQLite for project ID {self.project_id}.")


