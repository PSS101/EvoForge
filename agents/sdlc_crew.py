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
    analyze_python_ast
)
from tools.requirement_tools import classify_requirements
from tools.static_analysis import build_dependency_graph, dependency_graph_to_json
from tools.reuse_tools import generate_reuse_decision_report
from tools.impact_tools import generate_test_impact_report

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
        srs_path = os.path.join(self.reports_dir, "SRS.md")
        delta_path = os.path.join(self.reports_dir, "Requirement_Delta_Report.md")
        dependency_path = os.path.join(self.reports_dir, "Dependency_Graph.json")
        reuse_path = os.path.join(self.reports_dir, "Reuse_Decision_Report.md")
        test_impact_path = os.path.join(self.reports_dir, "Test_Impact_Report.md")

        existing_srs = self._load_existing_srs()
        raw_srs = self._run_requirement_stage(prompt, existing_srs, srs_path)

        merged_srs, delta_report, classified_requirements = classify_requirements(existing_srs, raw_srs)
        write_file(srs_path, merged_srs)
        write_file(delta_path, delta_report)
        if hasattr(self.db, 'store_srs_version'):
            try:
                self.db.store_srs_version(self.project_id, merged_srs, note=mode)
            except Exception as e:
                print(f"Warning: Failed to store SRS version in DB: {e}")
        else:
            print("DBManager.store_srs_version not available; skipping DB persistence for SRS.")

        dependency_graph = build_dependency_graph(self.project_dir)
        save_json(dependency_path, dependency_graph)
        if hasattr(self.db, 'store_dependency_graph'):
            try:
                self.db.store_dependency_graph(self.project_id, "static", dependency_graph_to_json(dependency_graph), file_path=dependency_path)
            except Exception as e:
                print(f"Warning: Failed to store dependency graph in DB: {e}")
        else:
            print("DBManager.store_dependency_graph not available; skipping DB persistence for dependency graph.")

        reuse_report = generate_reuse_decision_report(self.project_dir, merged_srs)
        write_file(reuse_path, reuse_report)

        impacted_modules = self._guess_impacted_modules(classified_requirements)
        test_impact_report = generate_test_impact_report(impacted_modules, self.project_dir)
        write_file(test_impact_path, test_impact_report)

        self._run_design_stage(design_output=os.path.join(self.reports_dir, "Design.md"), delta_path=delta_path)
        # Lazy import BaseAgent to avoid import-time dependency on crewai
        try:
            from agents.base_agent import BaseAgent as _BaseAgent
            code_agent_wrapper = _BaseAgent("code_agent")
        except Exception as e:
            print(f"Could not import BaseAgent for code stage: {e}. Proceeding with fallback.")
            code_agent_wrapper = None
        self._run_code_stage(code_agent_wrapper=code_agent_wrapper, code_output=None, dependency_path=dependency_path, reuse_path=reuse_path, delta_path=delta_path)
        self._run_testing_stage(testing_output_dir=os.path.join(self.project_dir, "tests"), test_impact_path=test_impact_path)
        self._run_documentation_stage(doc_output_dir=self.project_dir)

        self._update_db_registry_and_run(mode)
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

    def _run_single_stage(self, agent_wrapper: BaseAgent, task_name: str, task_vars: dict, output_file=None, tools=None):
        """Run a single agent task. If Crew is unavailable, write a safe placeholder output and continue.
        """
        # Prepare agent and task description
        try:
            agent = agent_wrapper.get_agent(tools=tools)
            description = agent_wrapper.get_task_description(task_name).format(**task_vars)
            expected = agent_wrapper.get_task_expected_output(task_name)
        except Exception as e:
            print(f"Agent wrapper preparation failed: {e}")
            agent = None
            description = task_vars.get("prompt", f"{task_name} (no description)")
            expected = None

        if not HAS_CREW:
            print(f"Crew not available; attempting local agent execution for task '{task_name}'.")
            # If we have a local agent implementation, run it and write its output
            if agent is not None and hasattr(agent, 'run'):
                try:
                    result_text = agent.run(description)
                    if output_file:
                        try:
                            write_file(output_file, result_text)
                        except Exception as e:
                            print(f"Failed writing agent output to {output_file}: {e}")
                    return result_text
                except Exception as e:
                    print(f"Local agent execution failed: {e}")

            # Fallback placeholder when no local agent is available
            print(f"Local agent not available or failed — writing placeholder for '{task_name}'")
            if output_file:
                placeholder = f"# Placeholder output for {task_name}\n\nDescription:\n{description}\n\nNote: Crew/agent execution was skipped because the crew library is unavailable or incompatible, and local agent execution failed."
                try:
                    write_file(output_file, placeholder)
                except Exception as e:
                    print(f"Failed writing placeholder output to {output_file}: {e}")
            return None

        # Normal flow: run with Crew
        try:
            task = Task(
                description=description,
                expected_output=expected,
                agent=agent,
                output_file=output_file
            )
            crew = Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=True)
            print(f"Running {task_name}...")
            return crew.kickoff()
        except TypeError as te:
            # Backward/forward compatibility issues — fallback to placeholder behavior
            print(f"Crew execution failed with TypeError: {te}. Falling back to placeholder output for '{task_name}'.")
            if output_file:
                placeholder = f"# Fallback output for {task_name}\n\nDescription:\n{description}\n\nNote: Crew execution failed with TypeError: {te}."
                try:
                    write_file(output_file, placeholder)
                except Exception as e:
                    print(f"Failed writing fallback output to {output_file}: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error while running Crew for '{task_name}': {e}")
            raise

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

    def _run_code_stage(self, code_agent_wrapper: BaseAgent, code_output, dependency_path: str, reuse_path: str, delta_path: str):
        existing_source_code = self._collect_existing_source_code()
        code_task_vars = {
            "reports_dir": self.reports_dir,
            "project_dir": self.project_dir,
            "existing_source_code": existing_source_code,
            "dependency_graph_path": dependency_path,
            "reuse_report_path": reuse_path,
            "delta_report_path": delta_path
        }
        # Use the unified _run_single_stage which has a Crew fallback
        return self._run_single_stage(
            code_agent_wrapper,
            "code_task",
            code_task_vars,
            output_file=code_output,
            tools=[read_project_file, write_project_file, list_project_files, analyze_python_ast]
        )

    def _run_testing_stage(self, testing_output_dir: str, test_impact_path: str):
        try:
            from agents.base_agent import BaseAgent as _BaseAgent
            testing_agent_wrapper = _BaseAgent("testing_agent")
            testing_agent = testing_agent_wrapper.get_agent(tools=[read_project_file, write_project_file, list_project_files])
        except Exception as e:
            print(f"Could not import BaseAgent for testing stage: {e}. Proceeding with fallback.")
            testing_agent_wrapper = None
            testing_agent = None

        testing_task_vars = {
            "project_dir": self.project_dir,
            "reports_dir": self.reports_dir,
            "test_impact_path": test_impact_path
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
        for root, dirs, files in os.walk(self.project_dir):
            if any(ignored in root for ignored in [".venv", "__pycache__", ".git", ".pytest_cache", "tests"]):
                continue
            for file in files:
                filepath = os.path.join(root, file)
                rel_path = os.path.relpath(filepath, self.project_dir)
                content = read_file(filepath)
                existing_source_code += f"\n--- FILE: {rel_path} ---\n{content}\n"
        return existing_source_code if existing_source_code else "No existing source code."

    def _guess_impacted_modules(self, classified_requirements):
        changed = []
        for item in classified_requirements:
            if item["tag"] in {"NEW", "MODIFIED", "REMOVED"}:
                keyword = re.sub(r"[^a-zA-Z0-9_]+", "_", item["text"]).strip("_")
                candidate = None
                if keyword:
                    candidate = f"{keyword.split('_')[0]}.py"
                changed.append(candidate or item["section"])
        return [module for module in sorted(set(changed)) if module]

    def _update_db_registry_and_run(self, mode: str):
        """Scan project and reports directories to update file hashes and log the run."""
        srs_path = os.path.join(self.reports_dir, "SRS.md")
        design_path = os.path.join(self.reports_dir, "Design.md")

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

