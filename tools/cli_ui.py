"""
EvoForge CLI UI/UX Module
Powered by Rich for visual terminal formatting, panels, tables, trees, and progress indicators.
"""

import os
import sys
import time
from typing import List, Dict, Any, Optional, Tuple

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.tree import Tree
    from rich.text import Text
    from rich.prompt import Prompt, Confirm, IntPrompt
    from rich.markdown import Markdown
    from rich.syntax import Syntax
    from rich.style import Style
    from rich.align import Align
    from rich.columns import Columns
    from rich import box
    from rich.status import Status
    from rich.rule import Rule
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

console = Console() if HAS_RICH else None

BANNER_ART = r"""
███████╗██╗   ██╗ ██████╗ ███████╗ ██████╗ ██████╗   ██████╗ ███████╗
██╔════╝██║   ██║██╔═══██╗██╔════╝██╔═══██╗██╔══██╗ ██╔════╝ ██╔════╝
█████╗  ██║   ██║██║   ██║█████╗  ██║   ██║██████╔╝ ██║  ███╗█████╗  
██╔══╝  ╚██╗ ██╔╝██║   ██║██╔══╝  ██║   ██║██╔══██╗ ██║   ██║██╔══╝  
███████╗ ╚████╔╝ ╚██████╔╝██║     ╚██████╔╝██║  ██║ ╚██████╔╝███████╗
╚══════╝  ╚═══╝   ╚═════╝ ╚═╝      ╚═════╝ ╚═╝  ╚═╝  ╚═════╝ ╚══════╝
"""


def is_rich_available() -> bool:
    return HAS_RICH


def print_banner():
    """Prints the EvoForge branding header with styled panel and metadata badges."""
    if not HAS_RICH:
        print("=== Autonomous Agentic SDLC Framework (EvoForge) ===")
        return

    banner_text = Text(BANNER_ART, style="bold cyan")
    tagline = Text("\nAutonomous Agentic Software Development Lifecycle Framework", style="bold white")
    subtitle = Text("AI-Driven Greenfield Engineering & Incremental Code Evolution\n", style="italic dim bright_cyan")
    
    badge_text = Text()
    badge_text.append(" [ Multi-Agent Pipeline ] ", style="bold black on cyan")
    badge_text.append(" ")
    badge_text.append(" [ CrewAI Integrated ] ", style="bold black on green")
    badge_text.append(" ")
    badge_text.append(" [ Hybrid C/C++ & Python ] ", style="bold black on yellow")

    content = Align.center(Text.assemble(banner_text, tagline, "\n", subtitle, badge_text))
    
    panel = Panel(
        content,
        box=box.ROUNDED,
        border_style="bold blue",
        padding=(1, 2),
        title="[bold bright_white]⚡ EVOFORGE SDLC ENGINE ⚡[/bold bright_white]",
        title_align="center"
    )
    console.print(panel)


def print_header(title: str, subtitle: Optional[str] = None):
    """Prints a styled section header rule."""
    if not HAS_RICH:
        print(f"\n--- {title} ---")
        if subtitle:
            print(f"    {subtitle}")
        return

    console.print()
    console.print(Rule(title=f"[bold cyan]{title}[/bold cyan]", style="blue"))
    if subtitle:
        console.print(Align.center(f"[dim italic bright_white]{subtitle}[/dim italic bright_white]"))
    console.print()



AVAILABLE_MODELS = [
    {
        "id": "1",
        "name": "qwen 2.5 coder 14B",
        "tag": "qwen2.5-coder:14b",
        "desc": "High-performance coding model optimized for code generation & refactoring"
    },
    {
        "id": "2",
        "name": "gpt OSS 20B",
        "tag": "gpt-oss:20b",
        "desc": "Open-source general intelligence & reasoning model"
    }
]


def resolve_model_choice(choice: Optional[str]) -> Tuple[str, str]:
    """
    Resolves user input string (number, option name, or model tag) to (display_name, model_tag).
    Defaults to qwen 2.5 coder 14B if empty or unrecognized.
    """
    choice_clean = (choice or "").strip().lower()
    if not choice_clean:
        return AVAILABLE_MODELS[0]["name"], AVAILABLE_MODELS[0]["tag"]

    if choice_clean in {"1", "qwen", "qwen 2.5 coder 14b", "qwen2.5-coder:14b", "qwen2.5-coder"}:
        return AVAILABLE_MODELS[0]["name"], AVAILABLE_MODELS[0]["tag"]

    if choice_clean in {"2", "gpt", "gpt oss 20b", "gpt-oss:20b", "gpt-oss-20b", "gpt-oss"}:
        return AVAILABLE_MODELS[1]["name"], AVAILABLE_MODELS[1]["tag"]

    return choice.strip(), choice.strip()


def get_active_model_info() -> Tuple[str, str]:
    """Returns (display_name, model_tag) for current OLLAMA_MODEL env var."""
    current_tag = os.getenv("OLLAMA_MODEL", AVAILABLE_MODELS[0]["tag"])
    return resolve_model_choice(current_tag)


def prompt_model_selection(default_model: Optional[str] = None) -> Tuple[str, str]:
    """
    Prompts the user to switch or choose between available models after giving input.
    Returns tuple: (display_name, model_tag).
    Sets environment variables OLLAMA_MODEL and LLM_PROVIDER.
    """
    current_name, current_tag = get_active_model_info()
    if default_model:
        current_name, current_tag = resolve_model_choice(default_model)

    if not HAS_RICH:
        print("\n=== Model Selection ===")
        print(f"Current Active Model: {current_name} ({current_tag})")
        for m in AVAILABLE_MODELS:
            print(f"  [{m['id']}] {m['name']} ({m['tag']}) - {m['desc']}")
        choice = input(f"Select LLM Model [1-2 or name] (default: 1): ").strip()
        display_name, tag = resolve_model_choice(choice)
        os.environ["OLLAMA_MODEL"] = tag
        os.environ["LLM_PROVIDER"] = "ollama"
        print(f"✔ Model switched to: {display_name} ({tag})\n")
        return display_name, tag

    console.print()
    grid = Table.grid(expand=True, padding=(0, 2))
    grid.add_column(style="bold white", width=6)
    grid.add_column(style="bold cyan", width=24)
    grid.add_column(style="dim bright_white", width=22)
    grid.add_column(style="dim white")

    for m in AVAILABLE_MODELS:
        is_current = (m["tag"] == current_tag)
        badge = " [Active]" if is_current else ""
        grid.add_row(f"[{m['id']}]", f"{m['name']}{badge}", f"({m['tag']})", m["desc"])

    panel = Panel(
        grid,
        title="[bold bright_white]🤖 MODEL SELECTION[/bold bright_white]",
        subtitle="[dim italic]Switch between available LLM models for pipeline execution[/dim italic]",
        border_style="magenta",
        box=box.ROUNDED,
        padding=(1, 2)
    )
    console.print(panel)

    prompt_msg = f"[bold bright_white]Select LLM Model [1/2 or name][/bold bright_white] [dim](default: 1 - {AVAILABLE_MODELS[0]['name']})[/dim]"
    user_choice = Prompt.ask(prompt_msg, default="1").strip()

    display_name, tag = resolve_model_choice(user_choice)
    os.environ["OLLAMA_MODEL"] = tag
    os.environ["LLM_PROVIDER"] = "ollama"

    console.print(f"[bold green]✔ Active Model Switched To:[/bold green] [bold magenta]{display_name}[/bold magenta] [dim]({tag})[/dim]\n")
    return display_name, tag


def prompt_requirements(mode: str = "new", default_project: str = "") -> Tuple[str, str]:
    """
    Prompts the user for requirements and optional project name.
    Returns (project_name, prompt_text).
    """
    if not HAS_RICH:
        pname = input(f"Project Name [{default_project}]: ").strip() or default_project
        req = input("Describe software requirements: ").strip()
        prompt_model_selection()
        return pname, req

    console.print()
    if mode == "new":
        console.print(Panel(
            "[bold green]Greenfield Project Creation[/bold green]\n"
            "[dim]Describe what application you want EvoForge to design, code, test, and document.[/dim]",
            border_style="green",
            box=box.ROUNDED
        ))
    else:
        console.print(Panel(
            "[bold yellow]Incremental Project Evolution[/bold yellow]\n"
            "[dim]Describe new features, modifications, or bug fixes to add to an existing project.[/dim]",
            border_style="yellow",
            box=box.ROUNDED
        ))

    pname = ""
    if mode == "evolve" or default_project:
        pname = Prompt.ask(
            "[bold cyan]Target Project Name[/bold cyan]",
            default=default_project
        ).strip().lower().replace(" ", "_")

    req_prompt = Prompt.ask("[bold bright_white]Enter software requirements prompt[/bold bright_white]").strip()
    prompt_model_selection()
    return pname, req_prompt


def print_triage_result(project_name: str, mode: str, language: str, reason: Optional[str] = None, model: Optional[str] = None):
    """Displays project triage and classification summary card."""
    lang_key = language.lower()
    lang_display = "⚡ C++" if lang_key == "cpp" else ("⚙️ C" if lang_key == "c" else "🐍 Python")
    model_name, model_tag = get_active_model_info() if not model else resolve_model_choice(model)

    if not HAS_RICH:
        print(f"\n[Triage] Target Project: '{project_name}' | Mode: '{mode}' | Language: '{lang_display}' | Model: '{model_name}'")
        return

    mode_badge = "[bold black on green] GREENFIELD (NEW) [/bold black on green]" if mode == "new" else "[bold black on yellow] INCREMENTAL (EVOLVE) [/bold black on yellow]"
    lang_badge = f"[bold white on blue] {lang_display} [/bold white on blue]"
    model_badge = f"[bold white on magenta] 🤖 {model_name} ({model_tag}) [/bold white on magenta]"
    
    grid = Table.grid(expand=True, padding=(0, 2))
    grid.add_column(style="bold white", width=18)
    grid.add_column()

    grid.add_row("Project Name:", f"[bold cyan]{project_name}[/bold cyan]")
    grid.add_row("Pipeline Mode:", mode_badge)
    grid.add_row("Target Language:", lang_badge)
    grid.add_row("Selected LLM Model:", model_badge)
    if reason:
        grid.add_row("Triage Context:", f"[dim]{reason}[/dim]")

    panel = Panel(
        grid,
        title="[bold bright_white]🎯 PROJECT CLASSIFICATION & SCOPE[/bold bright_white]",
        border_style="cyan",
        box=box.ROUNDED,
        padding=(1, 2)
    )
    console.print(panel)


def print_stage_card(stage_num: int, total_stages: int, title: str, description: str):
    """Prints a visual stage indicator card."""
    if not HAS_RICH:
        print(f"\n=== Stage {stage_num}/{total_stages}: {title} ===")
        print(f"    {description}")
        return

    stage_badge = f"[bold black on cyan] STAGE {stage_num}/{total_stages} [/bold black on cyan]"
    
    text = Text()
    text.append(f"{title}\n", style="bold bright_white")
    text.append(description, style="dim white")

    panel = Panel(
        text,
        title=stage_badge,
        title_align="left",
        border_style="bright_blue",
        box=box.ROUNDED,
        padding=(0, 2)
    )
    console.print()
    console.print(panel)


def print_stage_success(stage_name: str, summary: str):
    """Prints a green check mark success indicator for a completed stage."""
    if not HAS_RICH:
        print(f"✓ {stage_name}: {summary}")
        return
    console.print(f"[bold green]✔ [{stage_name}][/bold green] [white]{summary}[/white]")


def print_stage_warning(stage_name: str, message: str):
    """Prints a yellow warning badge."""
    if not HAS_RICH:
        print(f"⚠ {stage_name}: {message}")
        return
    console.print(f"[bold yellow]⚠ [{stage_name}][/bold yellow] [dim yellow]{message}[/dim yellow]")


def print_verification_summary(
    project_name: str,
    language: str,
    compile_success: bool,
    compile_output: str,
    test_success: bool,
    test_output: str,
    debug_applied: bool = False,
    debug_success: bool = False
):
    """
    Renders verification & automated testing results in a structured table & panel.
    """
    if not HAS_RICH:
        print("\n=== Automated Verification Summary ===")
        print(f"Compile: {'PASSED' if compile_success else 'FAILED'}")
        print(f"Tests: {'PASSED' if test_success else 'FAILED'}")
        if debug_applied:
            print(f"Auto-Debug: {'FIXED' if debug_success else 'UNRESOLVED'}")
        return

    table = Table(box=box.ROUNDED, expand=True, header_style="bold bright_cyan")
    table.add_column("Verification Step", style="bold white", width=22)
    table.add_column("Status", width=16, justify="center")
    table.add_column("Details Summary", style="dim white")

    # Compilation Row
    lang_key = language.lower()
    if lang_key in {"c", "cpp"}:
        c_label = "C++" if lang_key == "cpp" else "C"
        c_status = "[bold black on green] PASSED [/bold black on green]" if compile_success else "[bold black on red] FAILED [/bold black on red]"
        c_detail = "Binary / Library compiled cleanly with Makefile" if compile_success else "Compilation errors detected"
        table.add_row(f"{c_label} Build (gcc/make)", c_status, c_detail)

    # Test Execution Row
    t_label = "C++" if lang_key == "cpp" else ("C" if lang_key == "c" else "PYTHON")
    t_status = "[bold black on green] PASSED [/bold black on green]" if test_success else "[bold black on red] FAILED [/bold black on red]"
    t_detail = "All test assertions passed successfully" if test_success else "Test failures or assertion errors detected"
    table.add_row(f"{t_label} Test Suite", t_status, t_detail)

    # Debugger Pass Row
    if debug_applied:
        d_status = "[bold black on green] FIXED [/bold black on green]" if debug_success else "[bold black on red] UNRESOLVED [/bold black on red]"
        d_detail = "Automated C/C++ debugging agent resolved compiler/test errors" if debug_success else "Automated debugging could not fix all failures"
        table.add_row("Auto Debugging Pass", d_status, d_detail)

    final_ok = test_success or debug_success
    panel_color = "green" if final_ok else "red"
    title_status = "✔ ALL VERIFICATION TESTS PASSED" if final_ok else "✖ VERIFICATION ISSUES DETECTED"

    panel = Panel(
        table,
        title=f"[bold bright_white]{title_status}[/bold bright_white]",
        border_style=panel_color,
        box=box.ROUNDED
    )
    console.print()
    console.print(panel)

    # Log snippet preview if tests/build failed
    output_to_show = test_output or compile_output
    if not final_ok and output_to_show:
        log_panel = Panel(
            Syntax(output_to_show[-1000:], "text", line_numbers=False, word_wrap=True),
            title="[bold red]Log Trace Output (Tail)[/bold red]",
            border_style="red",
            box=box.ROUNDED
        )
        console.print(log_panel)


def print_deployment_summary(project_name: str, staged_paths: List[str], commit_msg: str, pushed: bool, skipped_reason: Optional[str] = None):
    """Displays deployment and Git push status summary."""
    if not HAS_RICH:
        print("\n=== Automated Deployment Summary ===")
        if skipped_reason:
            print(f"Skipped: {skipped_reason}")
        else:
            print(f"Committed: {commit_msg}")
            print(f"Pushed: {pushed}")
        return

    if skipped_reason:
        panel = Panel(
            f"[yellow]Automated Deployment Skipped:[/yellow] [dim]{skipped_reason}[/dim]",
            title="[bold yellow]🚀 DEPLOYMENT STAGE[/bold yellow]",
            border_style="yellow",
            box=box.ROUNDED
        )
        console.print(panel)
        return

    table = Table.grid(expand=True, padding=(0, 2))
    table.add_column(style="bold white", width=18)
    table.add_column()

    table.add_row("Staged Paths:", f"[cyan]{', '.join(staged_paths)}[/cyan]")
    table.add_row("Commit Message:", f"[italic bright_white]\"{commit_msg}\"[/italic bright_white]")
    push_badge = "[bold black on green] PUSHED TO REMOTE [/bold black on green]" if pushed else "[bold black on yellow] COMMITTED LOCALLY [/bold black on yellow]"
    table.add_row("Git Status:", push_badge)

    panel = Panel(
        table,
        title="[bold bright_white]🚀 AUTOMATED GIT DEPLOYMENT SUCCESSFUL[/bold bright_white]",
        border_style="green",
        box=box.ROUNDED
    )
    console.print()
    console.print(panel)


def print_projects_portfolio(projects: List[Dict[str, Any]]):
    """Renders a rich table of all existing projects in EvoForge."""
    if not HAS_RICH:
        print("\n=== EvoForge Project Portfolio ===")
        for p in projects:
            print(f"- {p['name']} ({p['language']}) - Files: {p['file_count']} - Directory: {p['path']}")
        return

    if not projects:
        console.print(Panel(
            "[dim italic]No existing projects found in database or filesystem.[/dim italic]",
            title="[bold cyan]📁 Project Portfolio[/bold cyan]",
            border_style="cyan"
        ))
        return

    table = Table(box=box.ROUNDED, expand=True, header_style="bold bright_cyan")
    table.add_column("#", style="bold yellow", width=4, justify="center")
    table.add_column("Project Name", style="bold cyan", width=22)
    table.add_column("Language", width=12, justify="center")
    table.add_column("Files", style="bold white", width=8, justify="center")
    table.add_column("SRS Spec", width=12, justify="center")
    table.add_column("Project Directory Path", style="dim white")

    for i, p in enumerate(projects, 1):
        lang = p.get("language", "unknown").upper()
        lang_style = "bold blue" if lang == "PYTHON" else "bold yellow"
        srs_status = "[green]✔ Present[/green]" if p.get("has_srs") else "[dim]✖ None[/dim]"
        
        table.add_row(
            str(i),
            p['name'],
            f"[{lang_style}]{lang}[/{lang_style}]",
            str(p.get('file_count', 0)),
            srs_status,
            p.get('path', '')
        )

    panel = Panel(
        table,
        title=f"[bold bright_white]📁 EVOFORGE PROJECT PORTFOLIO ({len(projects)} Projects)[/bold bright_white]",
        border_style="blue",
        box=box.ROUNDED
    )
    console.print()
    console.print(panel)


def print_project_details(project_name: str, project_dir: str, reports_dir: str, files_list: List[str], srs_content: str = "", dep_graph: Optional[Dict] = None):
    """
    Renders detailed tree and inspect view for a single project.
    """
    if not HAS_RICH:
        print(f"\n=== Project Details: {project_name} ===")
        print(f"Path: {project_dir}")
        print("Files:")
        for f in files_list:
            print(f"  - {f}")
        return

    # File Tree
    tree = Tree(f"[bold bright_cyan]📁 {project_name}[/bold bright_cyan] ({project_dir})")
    
    # Organize files into directory tree
    dir_nodes = {}
    for rel_path in sorted(files_list):
        parts = rel_path.split(os.sep)
        current = tree
        path_acc = ""
        for idx, part in enumerate(parts):
            path_acc = os.path.join(path_acc, part)
            if idx == len(parts) - 1:
                # File node
                icon = "🐍" if part.endswith(".py") else ("⚡" if part.endswith((".c", ".h")) else ("⚙️" if part == "Makefile" else "📄"))
                current.add(f"[green]{icon} {part}[/green]")
            else:
                # Directory node
                if path_acc not in dir_nodes:
                    dir_nodes[path_acc] = current.add(f"[bold yellow]📂 {part}/[/bold yellow]")
                current = dir_nodes[path_acc]

    tree_panel = Panel(
        tree,
        title="[bold bright_white]🌳 PROJECT FILE TREE[/bold bright_white]",
        border_style="cyan",
        box=box.ROUNDED
    )

    console.print()
    console.print(tree_panel)

    # Render SRS snippet if available
    if srs_content:
        srs_panel = Panel(
            Markdown(srs_content[:1500] + ("\n\n*(Truncated for view...)*" if len(srs_content) > 1500 else "")),
            title="[bold bright_white]📋 SOFTWARE REQUIREMENTS SPECIFICATION (SRS)[/bold bright_white]",
            border_style="blue",
            box=box.ROUNDED
        )
        console.print(srs_panel)


def print_system_diagnostics(env_vars: Dict[str, str], db_status: str, has_crew: bool):
    """Renders system configuration & LLM diagnostic panel."""
    if not HAS_RICH:
        print("\n=== System Diagnostics ===")
        print(f"LLM Provider: {env_vars.get('LLM_PROVIDER', 'not set')}")
        print(f"Database: {db_status}")
        print(f"CrewAI Available: {has_crew}")
        return

    table = Table(box=box.ROUNDED, expand=True, header_style="bold bright_cyan")
    table.add_column("Configuration Parameter", style="bold white", width=26)
    table.add_column("Status / Setting", width=20, justify="center")
    table.add_column("Description / Details", style="dim white")

    llm_prov = env_vars.get("LLM_PROVIDER", "ollama").lower()
    prov_badge = f"[bold black on cyan] {llm_prov.upper()} [/bold black on cyan]"
    table.add_row("LLM Provider", prov_badge, f"Configured model provider in .env")

    model = env_vars.get("OLLAMA_MODEL", "qwen2.5-coder:14b")
    url = env_vars.get("OLLAMA_BASE_URL", "http://localhost:11434")
    table.add_row("Ollama Model", f"[cyan]{model}[/cyan]", f"Base URL: {url}")

    db_badge = "[bold black on green] CONNECTED [/bold black on green]" if "connected" in db_status.lower() or "ok" in db_status.lower() else "[bold black on red] ERROR [/bold black on red]"
    table.add_row("SQLite Database", db_badge, db_status)

    crew_badge = "[bold black on green] INSTALLED [/bold black on green]" if has_crew else "[bold black on yellow] FALLBACK MODE [/bold black on yellow]"
    table.add_row("CrewAI Framework", crew_badge, "Multi-agent task orchestration engine")

    telemetry = env_vars.get("CREWAI_DISABLE_TELEMETRY", "false").lower()
    t_badge = "[green]Disabled (Offline)[/green]" if telemetry in {"true", "1"} else "[yellow]Enabled[/yellow]"
    table.add_row("Telemetry & Privacy", t_badge, "CrewAI tracing and telemetry state")

    panel = Panel(
        table,
        title="[bold bright_white]⚙️ SYSTEM & ENVIRONMENT DIAGNOSTICS[/bold bright_white]",
        border_style="magenta",
        box=box.ROUNDED
    )
    console.print()
    console.print(panel)


def print_help_guide():
    """Renders CLI usage and command reference guide."""
    guide_markdown = """
# 🛠️ EvoForge CLI Usage Guide

EvoForge is an **Autonomous Agentic SDLC Framework** designed for multi-agent software engineering.

## 📌 Command Line Interface Commands

### 1. Interactive Mode
Run EvoForge without flags to launch the rich interactive command center:
```bash
python main.py
```

### 2. Run Greenfield Project (`run-new`)
Initialize a new software project from a prompt:
```bash
python main.py run-new --name my_app --prompt "Build a CLI calculator with add/sub/mul/div"
```

### 3. Evolve Existing Project (`evolve`)
Add features or fix bugs in an existing project:
```bash
python main.py evolve --name my_app --prompt "Add square root and exponentiation functions"
```

### 4. Portfolio Listing (`list` / `projects`)
List all registered projects, language badges, and file counts:
```bash
python main.py list
```

### 5. Inspect Project (`inspect`)
Explore file tree structure and SRS specification for a project:
```bash
python main.py inspect --name my_app
```

### 6. System Configuration (`config` / `diagnostics`)
Inspect environment variables, LLM providers, and DB health:
```bash
python main.py config
```

---
*Powered by CrewAI, Rich, and Python.*
"""
    if not HAS_RICH:
        print(guide_markdown)
        return

    panel = Panel(
        Markdown(guide_markdown),
        title="[bold bright_white]❓ EVOFORGE HELP & REFERENCE[/bold bright_white]",
        border_style="cyan",
        box=box.ROUNDED,
        padding=(1, 2)
    )
    console.print()
    console.print(panel)


def fetch_project_portfolio() -> List[Dict[str, Any]]:
    """Fetches list of registered and on-disk projects for portfolio display."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    projects_dir = os.path.join(base_dir, "projects")
    reports_dir = os.path.join(base_dir, "reports")
    
    project_names = set()
    if os.path.exists(projects_dir):
        for entry in os.listdir(projects_dir):
            if os.path.isdir(os.path.join(projects_dir, entry)) and not entry.startswith("."):
                project_names.add(entry)

    try:
        from database.db_manager import DBManager
        db = DBManager()
        with db.get_connection() as conn:
            rows = conn.execute("SELECT name FROM projects").fetchall()
            for r in rows:
                project_names.add(r[0])
    except Exception:
        pass

    try:
        from tools.language_tools import load_project_language
    except ImportError:
        load_project_language = lambda p: None

    portfolio = []
    for name in sorted(project_names):
        p_dir = os.path.join(projects_dir, name)
        r_dir = os.path.join(reports_dir, name)
        
        file_count = 0
        if os.path.exists(p_dir):
            for root, dirs, files in os.walk(p_dir):
                if "__pycache__" in root or ".pytest_cache" in root:
                    continue
                files = [f for f in files if not f.endswith(".pyc")]
                file_count += len(files)
                
        lang = load_project_language(p_dir) or "python"
        srs_path = os.path.join(r_dir, "SRS.md")
        has_srs = os.path.exists(srs_path)
        
        portfolio.append({
            "name": name,
            "path": p_dir,
            "reports_path": r_dir,
            "language": lang,
            "file_count": file_count,
            "has_srs": has_srs
        })
    return portfolio


def get_project_inspect_info(project_name: str) -> Tuple[str, str, List[str], str]:
    """Returns (project_dir, reports_dir, relative_files_list, srs_content) for inspection."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    project_dir = os.path.join(base_dir, "projects", project_name)
    reports_dir = os.path.join(base_dir, "reports", project_name)

    files_list = []
    if os.path.exists(project_dir):
        for root, dirs, files in os.walk(project_dir):
            if "__pycache__" in root or ".pytest_cache" in root:
                continue
            for file in files:
                if file.endswith(".pyc"):
                    continue
                full_p = os.path.join(root, file)
                rel_p = os.path.relpath(full_p, project_dir)
                files_list.append(rel_p)

    srs_content = ""
    srs_path = os.path.join(reports_dir, "SRS.md")
    if os.path.exists(srs_path):
        try:
            with open(srs_path, "r", encoding="utf-8", errors="replace") as f:
                srs_content = f.read()
        except Exception:
            pass

    return project_dir, reports_dir, files_list, srs_content

