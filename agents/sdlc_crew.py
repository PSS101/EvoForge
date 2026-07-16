import os
from crewai import Crew, Process, Task
from agents.base_agent import BaseAgent
from database.db_manager import DBManager
from tools.file_tools import calculate_hash, read_file, write_file
from tools.project_tools import (
    read_project_file,
    write_project_file,
    list_project_files,
    analyze_python_ast
)

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
        Runs the multi-agent SDLC pipeline.
        mode can be 'new' or 'evolve'.
        """
        # Load agents
        req_agent_wrapper = BaseAgent("requirement_agent")
        design_agent_wrapper = BaseAgent("design_agent")
        code_agent_wrapper = BaseAgent("code_agent")
        testing_agent_wrapper = BaseAgent("testing_agent")
        doc_agent_wrapper = BaseAgent("documentation_agent")

        # Create agents with appropriate tools
        # Requirement and Design agents need read/write tools
        req_agent = req_agent_wrapper.get_agent(tools=[read_project_file, write_project_file])
        design_agent = design_agent_wrapper.get_agent(tools=[read_project_file, write_project_file])
        
        # Code agent needs AST analysis and write tools
        code_agent = code_agent_wrapper.get_agent(tools=[
            read_project_file,
            write_project_file,
            list_project_files,
            analyze_python_ast
        ])

        # Testing agent needs write tools to create/run tests
        testing_agent = testing_agent_wrapper.get_agent(tools=[read_project_file, write_project_file, list_project_files])
        
        # Documentation agent needs read/write tools
        doc_agent = doc_agent_wrapper.get_agent(tools=[read_project_file, write_project_file])

        # Setup Agents list
        agents_list = [req_agent]
        tasks_list = []

        # 1. Requirement Task
        srs_path = os.path.join(self.reports_dir, "SRS.md")
        existing_srs = read_file(srs_path) if os.path.exists(srs_path) else "No existing SRS."
        req_desc = req_agent_wrapper.get_task_description("requirement_task").format(
            prompt=prompt,
            reports_dir=self.reports_dir,
            existing_srs=existing_srs
        )
        req_expected = req_agent_wrapper.get_task_expected_output("requirement_task")
        req_task = Task(
            description=req_desc,
            expected_output=req_expected,
            agent=req_agent,
            output_file=srs_path
        )
        tasks_list.append(req_task)

        # 2. Impact Analysis Task (only for evolution)
        impact_report_path = os.path.join(self.reports_dir, "Impact_Report.md")
        if mode == "evolve":
            impact_agent_wrapper = BaseAgent("impact_agent")
            impact_agent = impact_agent_wrapper.get_agent(tools=[
                read_project_file,
                write_project_file,
                list_project_files,
                analyze_python_ast
            ])
            agents_list.append(impact_agent)

            # Get summary of existing files from DB registry
            registry = self.db.get_file_registry(self.project_id)
            existing_files_summary = "\n".join([
                f"- File: {f[0]}, Type: {f[1]}, Hash: {f[2]}" for f in registry
            ]) if registry else "No files registered yet."

            impact_desc = impact_agent_wrapper.get_task_description("impact_task").format(
                reports_dir=self.reports_dir,
                existing_files_summary=existing_files_summary
            )
            impact_expected = impact_agent_wrapper.get_task_expected_output("impact_task")
            impact_task = Task(
                description=impact_desc,
                expected_output=impact_expected,
                agent=impact_agent,
                output_file=os.path.join(self.reports_dir, "Impact_Report.md")
            )
            tasks_list.append(impact_task)

        # 3. Design Task
        agents_list.append(design_agent)
        design_desc = design_agent_wrapper.get_task_description("design_task").format(
            reports_dir=self.reports_dir
        )
        design_expected = design_agent_wrapper.get_task_expected_output("design_task")
        design_task = Task(
            description=design_desc,
            expected_output=design_expected,
            agent=design_agent,
            output_file=os.path.join(self.reports_dir, "Design.md")
        )
        tasks_list.append(design_task)

        # 4. Code Task
        agents_list.append(code_agent)
        
        # Load existing source code context if any
        existing_source_code = ""
        for root, dirs, files in os.walk(self.project_dir):
            if any(ignored in root for ignored in [".venv", "__pycache__", ".git", ".pytest_cache", "tests"]):
                continue
            for file in files:
                filepath = os.path.join(root, file)
                rel_path = os.path.relpath(filepath, self.project_dir)
                content = read_file(filepath)
                existing_source_code += f"\n--- FILE: {rel_path} ---\n{content}\n"
        if not existing_source_code:
            existing_source_code = "No existing source code."

        code_desc = code_agent_wrapper.get_task_description("code_task").format(
            reports_dir=self.reports_dir,
            project_dir=self.project_dir,
            existing_source_code=existing_source_code
        )
        code_expected = code_agent_wrapper.get_task_expected_output("code_task")
        code_task = Task(
            description=code_desc,
            expected_output=code_expected,
            agent=code_agent
        )
        tasks_list.append(code_task)

        # 5. Testing Task
        agents_list.append(testing_agent)
        testing_desc = testing_agent_wrapper.get_task_description("testing_task").format(
            project_dir=self.project_dir,
            reports_dir=self.reports_dir
        )
        testing_expected = testing_agent_wrapper.get_task_expected_output("testing_task")
        testing_task = Task(
            description=testing_desc,
            expected_output=testing_expected,
            agent=testing_agent
        )
        tasks_list.append(testing_task)

        # 6. Documentation Task
        agents_list.append(doc_agent)
        doc_desc = doc_agent_wrapper.get_task_description("documentation_task").format(
            project_dir=self.project_dir,
            reports_dir=self.reports_dir
        )
        doc_expected = doc_agent_wrapper.get_task_expected_output("documentation_task")
        doc_task = Task(
            description=doc_desc,
            expected_output=doc_expected,
            agent=doc_agent
        )
        tasks_list.append(doc_task)

        # Initialize Crew
        crew = Crew(
            agents=agents_list,
            tasks=tasks_list,
            process=Process.sequential,
            verbose=True
        )

        # Run Crew
        print(f"Starting SDLC Crew in '{mode}' mode for project '{self.project_name}'...")
        result = crew.kickoff()
        print("SDLC Crew run complete.")

        # Post-process: Classify and tag requirements incrementally
        self._classify_and_tag_requirements(srs_path, existing_srs)

        # Update registry and log runs
        self._update_db_registry_and_run(mode)
        return result

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

    def _classify_and_tag_requirements(self, srs_path: str, existing_srs_content: str):
        """Clean the draft SRS and run an LLM call to compare old and new requirements, classifying them."""
        if not os.path.exists(srs_path):
            return
        
        new_srs_content = read_file(srs_path)
        
        # Build prompt for requirements comparison & tagging
        prompt = f"""
You are an expert systems analyst. Your job is to compare the historical Software Requirements Specification (SRS) with the new updated draft SRS, merge them, and output a clean, final Software Requirements Specification (SRS) in markdown format.

Here is the previous/historical SRS:
\"\"\"
{existing_srs_content}
\"\"\"

Here is the new updated draft SRS:
\"\"\"
{new_srs_content}
\"\"\"

For EVERY single functional and non-functional requirement listed in the final merged list, you MUST classify it into one of these categories and prefix it with the exact tag:
- [NEW]: If the requirement was newly added in the updated draft.
- [MODIFIED]: If the requirement existed in the historical SRS but was updated or modified.
- [REMOVED]: If the requirement existed in the historical SRS but is no longer present in the updated draft. You must include it in the final list but prefix it with [REMOVED].
- [UNCHANGED]: If the requirement existed in the historical SRS and remains exactly the same.

Format the output as a valid markdown document starting with:
# Software Requirements Specification (SRS)

Under the 'Functional Requirements' section, ensure that every requirement item is prefixed with its classification tag. Example:
- [UNCHANGED] The system shall support addition.
- [NEW] The system shall support modulo calculation.
- [REMOVED] The system shall support legacy division.

Do NOT include any conversational intro, explanation, or outro. Do NOT wrap the markdown output in triple backticks (e.g. do not wrap in markdown tags). Just output the raw markdown text starting with '# Software Requirements Specification (SRS)'.
"""
        try:
            # Get LLM instance
            from agents.base_agent import BaseAgent
            req_agent_wrapper = BaseAgent("requirement_agent")
            llm = req_agent_wrapper.llm
            
            # Invoke LLM
            response_text = llm.call([{"role": "user", "content": prompt}])
            
            # Clean up output if wrapped in backticks
            response_text = response_text.strip()
            if response_text.startswith("```"):
                lines = response_text.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                response_text = "\n".join(lines).strip()
            
            # Write back
            write_file(srs_path, response_text)
            print(f"Successfully classified and updated requirements in {srs_path}")
        except Exception as e:
            print(f"Warning: Failed to classify requirements via LLM call: {e}")
