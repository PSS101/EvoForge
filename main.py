import argparse
import sys
import os
import json
import re
import subprocess
from dotenv import load_dotenv

# Load environment variables first to disable telemetry and configure offline providers
load_dotenv()

import tools.cli_ui as ui
from agents.sdlc_crew import SDLCCrewManager

# Defensive imports to allow running without crewai installed (fallback mode)
try:
    from agents.base_agent import BaseAgent
except Exception:
    BaseAgent = None

try:
    from crewai import Agent, Task, Crew, Process
    HAS_CREW = True
except Exception:
    Agent = None
    Task = None
    Crew = None
    Process = None
    HAS_CREW = False

from database.db_manager import DBManager
from tools.language_tools import detect_language, load_project_language, has_explicit_language
from tools.build_tools import compile_project, run_c_tests, generate_makefile, debug_c_project


def check_env_file():
    """Ensures .env exists or creates default .env.example template."""
    if not os.path.exists(".env"):
        with open(".env.example", "w", encoding="utf-8") as f:
            f.write(
                "# LLM Provider Selection (ollama)\n"
                "LLM_PROVIDER=ollama\n\n"
                "# Ollama Local Configuration (Offline)\n"
                "OLLAMA_MODEL=qwen2.5-coder:14b\n"
                "OLLAMA_BASE_URL=http://localhost:11434\n\n"
                "# Disable CrewAI telemetry for offline execution\n"
                "CREWAI_DISABLE_TELEMETRY=true\n"
                "OTEL_SDK_DISABLED=true\n"
                "CREWAI_TRACING_ENABLED=false\n"
            )
        ui.print_stage_warning("Env Setup", ".env file was missing. A template .env.example has been created.")
        ui.print_stage_warning("Env Setup", "Please rename .env.example to .env and configure your LLM settings before running.")
        sys.exit(1)


def autonomous_triage(prompt: str) -> tuple[str, str]:
    """
    Determines project_name and mode autonomously using LLM classifier or fallback heuristics.
    """
    try:
        db = DBManager()
        with db.get_connection() as conn:
            projects = conn.execute("SELECT name FROM projects").fetchall()
        existing_projects = [p[0] for p in projects]
    except Exception as e:
        ui.print_stage_warning("Triage DB", f"Could not fetch existing projects from DB: {e}")
        existing_projects = []

    project_name = "software_project"
    mode = "new"

    def run_llm_triage():
        nonlocal project_name, mode
        if HAS_CREW and Agent is not None and Task is not None and Crew is not None and Process is not None:
            try:
                agent_wrapper = BaseAgent("requirement_agent")
                llm = agent_wrapper.llm
                
                classifier_agent = Agent(
                    role="Project Requirements Triage Agent",
                    goal="Classify user requirement prompt into project_name and mode.",
                    backstory=(
                        "You are a detail-oriented triage coordinator. You parse user software requirements "
                        "to determine the target project name (as a clean, lowercase snake_case slug) "
                        "and whether this is a greenfield project ('new') or an update to an existing project ('evolve')."
                    ),
                    llm=llm,
                    verbose=False,
                    allow_delegation=False
                )
                
                classifier_task = Task(
                    description=(
                        f"Analyze the user requirement prompt: \"{prompt}\"\n\n"
                        f"Here is the list of existing projects: {existing_projects}\n\n"
                        "Determine:\n"
                        "1. 'project_name': A clean lowercase snake_case identifier for the project. "
                        "If the prompt references or seems to update/add features to one of the existing projects "
                        "in the list, you must use that exact existing project name. Otherwise, create a new one.\n"
                        "2. 'mode': Must be either 'evolve' (if the project matches or refers to one of the existing projects) "
                        "or 'new' (if the project is not in the list of existing projects).\n\n"
                        "You must output ONLY a valid JSON object. Do not include markdown code block formatting or any other text. "
                        "Example output:\n"
                        "{\"project_name\": \"calculator\", \"mode\": \"evolve\"}"
                    ),
                    expected_output="A JSON object containing keys 'project_name' and 'mode'.",
                    agent=classifier_agent
                )
                
                crew = Crew(
                    agents=[classifier_agent],
                    tasks=[classifier_task],
                    process=Process.sequential,
                    verbose=False
                )
                
                classification_raw = str(crew.kickoff()).strip()
                clean_result = classification_raw
                if "```" in clean_result:
                    match = re.search(r"```(?:json)?\s*(.*?)\s*```", clean_result, re.DOTALL)
                    if match:
                        clean_result = match.group(1).strip()
                json_match = re.search(r"\{.*\}", clean_result, re.DOTALL)
                if json_match:
                    clean_result = json_match.group(0)
                
                data = json.loads(clean_result)
                project_name = re.sub(r'[^a-zA-Z0-9_]', '_', data.get("project_name", "")).strip('_').lower()
                mode = str(data.get("mode", "new")).strip().lower()
                if mode not in {"new", "evolve"}:
                    mode = "new"
                return
            except Exception:
                pass

        # Heuristic fallback
        GENERIC_WORDS = {"build", "create", "make", "run", "test", "app", "project", "software_project", "new"}
        for p in existing_projects:
            if p.lower() not in GENERIC_WORDS and re.search(r'\b' + re.escape(p.lower()) + r'\b', prompt.lower()):
                project_name = p
                mode = "evolve"
                return

        if mode == "new":
            nouns = [w for w in re.findall(r'\b[a-zA-Z0-9_]+\b', prompt.lower()) if w not in GENERIC_WORDS and len(w) > 2 and w not in {"simple", "in", "for", "with", "c", "cpp", "python"}]
            if nouns:
                project_name = "_".join(nouns[:2])

    if ui.is_rich_available():
        with ui.console.status("[bold cyan]Analyzing requirements & triaging project scope...", spinner="dots"):
            run_llm_triage()
    else:
        print("Analyzing requirements and identifying project scope...")
        run_llm_triage()

    if not project_name:
        project_name = "software_project"
    project_name = project_name.lower().replace(" ", "_")

    # Override heuristic: if user explicitly mentions an existing project name in prompt
    GENERIC_WORDS = {"build", "create", "make", "run", "test", "app", "project", "software_project", "new"}
    for p in existing_projects:
        if p.lower() not in GENERIC_WORDS and re.search(r'\b' + re.escape(p.lower()) + r'\b', prompt.lower()):
            project_name = p
            mode = "evolve"
            break

    if mode == "evolve" and project_name not in existing_projects:
        mode = "new"

    return project_name, mode


def execute_pipeline(project_name: str, mode: str, prompt: str):
    """
    Executes the multi-agent SDLC pipeline, automated verification, and Git deployment.
    """
    project_name = project_name.lower().replace(" ", "_")
    target_lang = detect_language(prompt)

    ui.print_triage_result(project_name=project_name, mode=mode, language=target_lang)

    manager = SDLCCrewManager(project_name=project_name)
    if mode == "new":
        ui.print_header("INITIALIZING GREENFIELD SDLC PIPELINE", f"Project: {project_name}")
        manager.run_pipeline(prompt=prompt, mode="new")
    else:
        ui.print_header("EVOLVING EXISTING SDLC PROJECT", f"Project: {project_name}")
        manager.run_pipeline(prompt=prompt, mode="evolve")

    # Automated Verification Stage — use language resolved by the pipeline manager
    # so an explicit "python" prompt is never overridden by leftover C/C++ files on disk.
    ui.print_header("STAGE: AUTOMATED VERIFICATION (TESTS)", f"Project: {project_name}")
    project_dir = os.path.join("projects", project_name)
    tests_passed = True
    compile_success = True
    compile_output = ""
    test_success = True
    test_output = ""
    debug_applied = False
    debug_success = False

    language = manager.project_language
    has_sources = manager._project_has_source_files()
    if not has_sources:
        compile_success = False
        test_success = False
        tests_passed = False
        compile_output = "No source files were generated for this project."
        test_output = "Automated verification failed: Project directory contains no source code."
    elif language in {"c", "cpp"}:
        makefile_path = os.path.join(project_dir, "Makefile")
        if not os.path.exists(makefile_path):
            ui.print_stage_warning("Makefile Generator", "No Makefile found. Generating default C/C++ Makefile...")
            try:
                generate_makefile(project_dir, project_name, language)
            except Exception as e:
                ui.print_stage_warning("Makefile Error", f"Failed to generate Makefile: {e}")

        compile_success, compile_output = compile_project(project_dir)
        if compile_success:
            test_dir = os.path.join(project_dir, "tests")
            if os.path.isdir(test_dir):
                test_success, test_output = run_c_tests(project_dir)

        if not compile_success or not test_success:
            debug_applied = True
            ui.print_stage_warning("C/C++ Debugger", "Initial verification failed. Running automated C/C++ debugging pass...")
            debug_success, dbg_out = debug_c_project(project_dir)
            test_output = (test_output or compile_output) + "\n\n" + dbg_out
            tests_passed = debug_success
            if debug_success:
                compile_success = True
                test_success = True
        else:
            tests_passed = True
    else:
        test_dir = os.path.join(project_dir, "tests")
        if os.path.exists(test_dir):
            env = os.environ.copy()
            # Set PYTHONPATH to include project_dir and its parent so both package-style
            # and module-style imports (e.g. from inventory import ... or from project_name.inventory import ...) work.
            parent_dir = os.path.dirname(os.path.abspath(project_dir))
            proj_abs = os.path.abspath(project_dir)
            env["PYTHONPATH"] = f"{proj_abs}:{parent_dir}:{env.get('PYTHONPATH', '')}"

            result = subprocess.run(
                [
                    sys.executable, "-m", "pytest",
                    "tests",                          # target tests/ dir relative to project_dir
                    "--import-mode=importlib",        # avoid __pycache__ module collisions
                    "-p", "no:cacheprovider",         # skip .pytest_cache creation in project
                    "-q",
                ],
                cwd=os.path.abspath(project_dir),
                env=env,
                capture_output=True,
                text=True
            )
            test_output = result.stdout + ("\n" + result.stderr if result.stderr else "")
            test_success = (result.returncode == 0)
            tests_passed = test_success
        else:
            test_output = "No pytest suite found in tests directory. Skipping verification."
            test_success = True
            tests_passed = True

    ui.print_verification_summary(
        project_name=project_name,
        language=language,
        compile_success=compile_success,
        compile_output=compile_output,
        test_success=test_success,
        test_output=test_output,
        debug_applied=debug_applied,
        debug_success=debug_success
    )

    # Automated Deployment Stage
    if tests_passed:
        ui.print_header("STAGE: AUTOMATED DEPLOYMENT (GIT PUSH)", f"Project: {project_name}")
        try:
            add_paths = [
                os.path.join("projects", project_name),
                os.path.join("reports", project_name)
            ]
            existing_add_paths = [p for p in add_paths if os.path.exists(p)]
            if existing_add_paths:
                subprocess.run(["git", "add"] + existing_add_paths, check=True)
                status_result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
                if status_result.stdout.strip():
                    commit_msg = f"auto(sdlc): update {project_name} autonomously"
                    subprocess.run(["git", "commit", "-m", commit_msg], check=True)
                    subprocess.run(["git", "push"], check=True)
                    ui.print_deployment_summary(project_name, existing_add_paths, commit_msg, pushed=True)
                else:
                    ui.print_deployment_summary(project_name, [], "", pushed=False, skipped_reason="No uncommitted changes detected.")
            else:
                ui.print_deployment_summary(project_name, [], "", pushed=False, skipped_reason="No project artifacts found to stage.")
        except Exception as ge:
            ui.print_stage_warning("Git Deployment", f"Automated Git deployment warning: {ge}")
    else:
        ui.print_deployment_summary(project_name, [], "", pushed=False, skipped_reason="Deployment skipped due to verification test failures.")


def prompt_and_run_direct():
    """
    Direct prompt entry when main.py is executed without arguments.
    """
    ui.print_banner()
    if ui.is_rich_available():
        from rich.prompt import Prompt
        prompt = Prompt.ask("[bold bright_white]Please describe your software requirements[/bold bright_white]").strip()
    else:
        prompt = input("Please describe your software requirements: ").strip()

    if not prompt:
        if ui.is_rich_available():
            ui.print_stage_warning("Input Error", "Requirements prompt cannot be empty. Exiting.")
        else:
            print("Requirements prompt cannot be empty. Exiting.")
        sys.exit(1)

    # After giving input, allow the user to switch between models:
    ui.prompt_model_selection()

    project_name, mode = autonomous_triage(prompt)
    execute_pipeline(project_name, mode, prompt)


def main():
    check_env_file()

    parser = argparse.ArgumentParser(
        description="EvoForge SDLC Framework: Autonomous Multi-Agent Software Development Lifecycle Manager"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # run-new parser
    parser_new = subparsers.add_parser("run-new", help="Initialize and run a new software project")
    parser_new.add_argument("--name", help="Name of the project (optional, determined autonomously if omitted)")
    parser_new.add_argument("--prompt", required=True, help="Functional requirements prompt for the new project")
    parser_new.add_argument("--model", "-m", help="Select LLM model (1: qwen 2.5 coder 14B, 2: gpt OSS 20B)")

    # evolve parser
    parser_evolve = subparsers.add_parser("evolve", help="Evolve an existing software project incrementally")
    parser_evolve.add_argument("--name", help="Name of the project to evolve")
    parser_evolve.add_argument("--prompt", required=True, help="Incremental feature updates prompt")
    parser_evolve.add_argument("--model", "-m", help="Select LLM model (1: qwen 2.5 coder 14B, 2: gpt OSS 20B)")

    # list parser
    subparsers.add_parser("list", help="List all existing projects in portfolio")

    # inspect parser
    parser_inspect = subparsers.add_parser("inspect", help="Inspect project file tree and SRS specifications")
    parser_inspect.add_argument("--name", required=True, help="Name of the project to inspect")

    # config parser
    subparsers.add_parser("config", help="View system diagnostics and LLM configuration")

    if len(sys.argv) == 1:
        prompt_and_run_direct()
        sys.exit(0)

    args = parser.parse_args()

    if args.command in {"list", "projects"}:
        ui.print_banner()
        portfolio = ui.fetch_project_portfolio()
        ui.print_projects_portfolio(portfolio)

    elif args.command == "inspect":
        ui.print_banner()
        p_dir, r_dir, files, srs = ui.get_project_inspect_info(args.name)
        ui.print_project_details(args.name, p_dir, r_dir, files, srs)

    elif args.command in {"config", "diagnostics"}:
        ui.print_banner()
        env_vars = {k: os.getenv(k, "") for k in ["LLM_PROVIDER", "OLLAMA_MODEL", "OLLAMA_BASE_URL", "CREWAI_DISABLE_TELEMETRY"]}
        db_status = "Connected & Initialized (SQLite)"
        try:
            db = DBManager()
            with db.get_connection() as conn:
                conn.execute("SELECT 1")
        except Exception as e:
            db_status = f"Error: {e}"
        ui.print_system_diagnostics(env_vars, db_status, HAS_CREW)

    elif args.command == "run-new":
        ui.print_banner()
        if args.model:
            model_display, model_tag = ui.resolve_model_choice(args.model)
            os.environ["OLLAMA_MODEL"] = model_tag
            os.environ["LLM_PROVIDER"] = "ollama"
            if ui.is_rich_available():
                ui.console.print(f"[bold green]✔ Model set to:[/bold green] [bold magenta]{model_display}[/bold magenta] [dim]({model_tag})[/dim]\n")
        elif sys.stdin.isatty():
            ui.prompt_model_selection()

        project_name = args.name
        if not project_name:
            project_name, mode = autonomous_triage(args.prompt)
        else:
            mode = "new"
        execute_pipeline(project_name, mode, args.prompt)

    elif args.command == "evolve":
        ui.print_banner()
        if args.model:
            model_display, model_tag = ui.resolve_model_choice(args.model)
            os.environ["OLLAMA_MODEL"] = model_tag
            os.environ["LLM_PROVIDER"] = "ollama"
            if ui.is_rich_available():
                ui.console.print(f"[bold green]✔ Model set to:[/bold green] [bold magenta]{model_display}[/bold magenta] [dim]({model_tag})[/dim]\n")
        elif sys.stdin.isatty():
            ui.prompt_model_selection()

        project_name = args.name
        if not project_name:
            project_name, mode = autonomous_triage(args.prompt)
        else:
            mode = "evolve"
        execute_pipeline(project_name, mode, args.prompt)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()

