import argparse
import sys
import os
from dotenv import load_dotenv

# Load environment variables first to disable telemetry and configure offline providers
load_dotenv()

from agents.sdlc_crew import SDLCCrewManager

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
        print("=== Agentic SDLC Framework ===")
        print("1. Initialize and run a new software project")
        print("2. Evolve an existing software project incrementally")
        choice = input("Select option (1 or 2): ").strip()
        if choice not in ["1", "2"]:
            print("Invalid choice. Exiting.")
            sys.exit(1)
        command = "run-new" if choice == "1" else "evolve"
        name = input("Enter project name: ").strip()
        if not name:
            print("Project name cannot be empty. Exiting.")
            sys.exit(1)
        prompt = input("Enter functional requirements prompt: ").strip()
        if not prompt:
            print("Prompt cannot be empty. Exiting.")
            sys.exit(1)
            
        class InteractiveArgs:
            def __init__(self, command, name, prompt):
                self.command = command
                self.name = name
                self.prompt = prompt
        args = InteractiveArgs(command, name, prompt)
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
    except Exception as e:
        print(f"\nError running SDLC pipeline: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
