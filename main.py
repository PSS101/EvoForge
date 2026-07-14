import argparse
import sys
import os
from dotenv import load_dotenv

# Load environment variables first to disable telemetry and configure offline providers
load_dotenv()

from agents.sdlc_crew import SDLCCrewManager
# Lazy/defensive imports to allow running without crewai installed (fallback mode)
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
import json
import re
import subprocess

def main():
    parser = argparse.ArgumentParser(
        description="Agentic SDLC Framework: Autonomous Software Development Lifecycle Manager"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # run-new parser
    parser_new = subparsers.add_parser("run-new", help="Initialize and run a new software project")
    parser_new.add_argument("--name", required=True, help="Name of the project")
    parser_new.add_argument("--prompt", required=True, help="Functional requirements prompt for the new project")
    
    # evolve parser
    parser_evolve = subparsers.add_parser("evolve", help="Evolve an existing software project incrementally")
    parser_evolve.add_argument("--name", required=True, help="Name of the project")
    parser_evolve.add_argument("--prompt", required=True, help="Incremental feature updates and modifications prompt")
    
    if len(sys.argv) == 1:
        print("=== Autonomous Agentic SDLC Framework ===")
        prompt = input("Please describe your software requirements: ").strip()
        if not prompt:
            print("Requirements prompt cannot be empty. Exiting.")
            sys.exit(1)
        
        # Determine project_name and mode autonomously
        print("\nAnalyzing requirements and identifying project scope...")
        try:
            db = DBManager()
            with db.get_connection() as conn:
                projects = conn.execute("SELECT name FROM projects").fetchall()
            existing_projects = [p[0] for p in projects]
        except Exception as e:
            print(f"Warning: Could not connect to database to fetch existing projects: {e}")
            existing_projects = []
            
        try:
            # Instantiate BaseAgent to get the configured LLM
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
            
            # Clean markdown formatting if present
            clean_result = classification_raw
            if "```" in clean_result:
                match = re.search(r"```(?:json)?\s*(.*?)\s*```", clean_result, re.DOTALL)
                if match:
                    clean_result = match.group(1).strip()
            
            data = json.loads(clean_result)
            project_name = data.get("project_name", "").strip().lower().replace(" ", "_")
            mode = data.get("mode", "new").strip().lower()
        except Exception as e:
            print(f"Warning: Autonomous classification failed or timed out: {e}")
            # Fallback heuristics
            project_name = "software_project"
            mode = "new"
            for p in existing_projects:
                if p.lower() in prompt.lower():
                    project_name = p
                    mode = "evolve"
                    break
        
        # Enforce name formatting and mode constraints
        if not project_name:
            project_name = "software_project"
        project_name = project_name.lower().replace(" ", "_")
        
        # Override heuristic: if user explicitly mentions an existing project name in the prompt,
        # override the LLM's decision to ensure we evolve that project.
        for p in existing_projects:
            if re.search(r'\b' + re.escape(p.lower()) + r'\b', prompt.lower()):
                project_name = p
                mode = "evolve"
                break
        
        if mode == "evolve" and project_name not in existing_projects:
            mode = "new"
            
        print(f"Identified project: '{project_name}' | Mode: '{mode}'")
        
        class InteractiveArgs:
            def __init__(self, command, name, prompt):
                self.command = command
                self.name = name
                self.prompt = prompt
        
        command = "run-new" if mode == "new" else "evolve"
        args = InteractiveArgs(command, project_name, prompt)
    else:
        args = parser.parse_args()
    
    # Check for .env file and write example if missing
    if not os.path.exists(".env"):
        with open(".env.example", "w", encoding="utf-8") as f:
            f.write(
                "# LLM Provider Selection (gemini, openai, ollama)\n"
                "LLM_PROVIDER=ollama\n\n"
                "# Gemini API Key Configuration\n"
                "# GEMINI_API_KEY=your_gemini_api_key_here\n"
                "# GEMINI_MODEL=gemini-1.5-flash\n\n"
                "# OpenAI API Key Configuration\n"
                "# OPENAI_API_KEY=your_openai_api_key_here\n"
                "# OPENAI_MODEL=gpt-4o-mini\n\n"
                "# Ollama Local Configuration (Offline)\n"
                "OLLAMA_MODEL=qwen2.5:1.5b\n"
                "OLLAMA_BASE_URL=http://localhost:11434\n\n"
                "# Disable CrewAI telemetry for offline execution\n"
                "CREWAI_DISABLE_TELEMETRY=true\n"
                "OTEL_SDK_DISABLED=true\n"
                "CREWAI_TRACING_ENABLED=false\n"
            )
        print("Warning: .env file was missing. A template .env.example has been created.")
        print("Please rename it to .env and configure your LLM settings before running the pipeline.")
        sys.exit(1)
        
    if not args.command:
        parser.print_help()
        sys.exit(1)
        
    project_name = args.name.lower().replace(" ", "_")
    
    try:
        manager = SDLCCrewManager(project_name=project_name)
        if args.command == "run-new":
            print(f"Initializing new project '{project_name}'...")
            manager.run_pipeline(prompt=args.prompt, mode="new")
        elif args.command == "evolve":
            print(f"Evolving project '{project_name}' with new requirements...")
            manager.run_pipeline(prompt=args.prompt, mode="evolve")
            
        # Post-pipeline validation
        print("\n=== Stage: Automated Verification (Tests) ===")
        project_dir = os.path.join("projects", project_name)
        test_dir = os.path.join(project_dir, "tests")
        tests_passed = True
        
        if os.path.exists(test_dir):
            print(f"Running pytest suite in '{project_dir}'...")
            env = os.environ.copy()
            env["PYTHONPATH"] = project_dir
            
            result = subprocess.run(
                [sys.executable, "-m", "pytest", project_dir],
                env=env,
                capture_output=True,
                text=True
            )
            print(result.stdout)
            if result.stderr:
                print(result.stderr)
                
            if result.returncode == 0:
                print("Verification successful: All tests passed!")
                tests_passed = True
            else:
                print("Verification failed: Some tests did not pass.")
                tests_passed = False
        else:
            print("No test suite found. Skipping verification.")
            
        # Post-pipeline deployment
        if tests_passed:
            print("\n=== Stage: Automated Deployment (Git Push) ===")
            try:
                # Stage files
                add_paths = [
                    os.path.join("projects", project_name),
                    os.path.join("reports", project_name)
                ]
                existing_add_paths = [p for p in add_paths if os.path.exists(p)]
                if existing_add_paths:
                    print(f"Staging changes for: {existing_add_paths}")
                    subprocess.run(["git", "add"] + existing_add_paths, check=True)
                    
                    status_result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
                    if status_result.stdout.strip():
                        commit_msg = f"auto(sdlc): update {project_name} autonomously"
                        print(f"Committing changes: '{commit_msg}'")
                        subprocess.run(["git", "commit", "-m", commit_msg], check=True)
                        
                        print("Pushing changes to remote Git repository...")
                        subprocess.run(["git", "push"], check=True)
                        print("Deployment successful: Code pushed to remote Git repository.")
                    else:
                        print("No changes to commit. Skipping Git push.")
                else:
                    print("No project files found to deploy. Skipping Git push.")
            except Exception as ge:
                print(f"Warning: Automated Git deployment failed: {ge}")
        else:
            print("\nDeployment skipped due to test failures.")
            
    except Exception as e:
        print(f"\nError running SDLC pipeline: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
