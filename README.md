# ⚡ EvoForge SDLC Framework

> **Autonomous, Multi-Agent Software Development Lifecycle (SDLC) Engineering Engine**

EvoForge is an advanced autonomous multi-agent framework designed to execute complete, end-to-end Software Development Lifecycles. Given a natural language user prompt, EvoForge autonomously triages project requirements, synthesizes ISO/IEC/IEEE 29148 compliant Software Requirements Specifications (SRS), generates Clean Architecture software designs, engineers production-ready code in multiple programming languages (Python, C, C++), creates automated test suites, validates syntax and runtime semantics via self-correction loops, persists versioned state to an SQLite database, and executes automated Git deployment.

---

## 🗺️ Detailed Workflow Architecture

The EvoForge pipeline operates across **6 distinct autonomous stages**, combining LLM-powered specialized agents, static code analysis tools, deterministic fallback generators, runtime compilation/test runners, and version control integrations.

### 🔄 End-to-End Pipeline Flowchart

```mermaid
graph TD
    A["User Input / Requirement Prompt"] --> B["CLI Triage & Language Detection<br/>(main.py & autonomous_triage)"]
    
    subgraph STAGE_0 ["Stage 0: Project Scope & Triage"]
        B --> B1{"Project Exists in DB?"}
        B1 -- Yes --> B2["Mode: EVOLVE<br/>(Load Existing SRS & Codebase)"]
        B1 -- No --> B3["Mode: NEW<br/>(Greenfield Initialization)"]
        B --> B4["Detect Target Language<br/>(Python / C / C++)"]
    end

    B2 --> C["Stage 1: Requirements Analysis<br/>(requirement_agent & classify_requirements)"]
    B3 --> C
    B4 --> C

    subgraph STAGE_1 ["Stage 1: Requirements Analysis & SRS Synthesis"]
        C --> C1["Synthesize ISO/IEC/IEEE 29148 SRS.md"]
        C1 --> C2["Classify Requirements Delta:<br/>[NEW], [MODIFIED], [REMOVED], [UNCHANGED]"]
        C2 --> C3["Persist SRS.md & Requirement_Delta_Report.md"]
        C3 --> C4["Store SRS Version in SQLite DB"]
    end

    C4 --> D["Stage 2: Architecture & Impact Modeling<br/>(design_agent & static_analysis)"]

    subgraph STAGE_2 ["Stage 2: Architecture & Dependency Modeling"]
        D --> D1["Static Dependency Graph Analysis<br/>(build_dependency_graph -> Dependency_Graph.json)"]
        D1 --> D2["Asset Reuse & Impact Analysis<br/>(Reuse_Decision_Report.md & Test_Impact_Report.md)"]
        D2 --> D3["Synthesize Clean Architecture Design<br/>(Design.md with Mermaid Diagrams)"]
    end

    D3 --> E["Stage 3: Automated Code Engineering<br/>(code_agent / c_code_agent)"]

    subgraph STAGE_3 ["Stage 3: Code Generation & Self-Correction Loop"]
        E --> E1["Generate Source & Header Files<br/>(Python / C / C++)"]
        E1 --> E2{"Syntax & Compiler Check<br/>(ast.parse / gcc / g++)"}
        E2 -- "Failed (Syntax / Compiler Error)" --> E3{"Retries < MAX_RETRIES?"}
        E3 -- Yes --> E4["Feedback Error Traceback to LLM<br/>(Self-Correction Prompt)"]
        E4 --> E1
        E3 -- No --> E5["Deterministic Fallback Scaffold Generator"]
        E2 -- "Passed" --> E6["Write Source Code to disk (projects/project_name/)"]
        E5 --> E6
    end

    E6 --> F["Stage 4: Automated Testing & Verification<br/>(testing_agent / c_testing_agent)"]

    subgraph STAGE_4 ["Stage 4: Test Suite & Impact Mapping"]
        F --> F1["Generate Assertion-Backed Test Suite<br/>(pytest for Python / assert.h runner for C/C++)"]
        F1 --> F2{"Test Execution Verification<br/>(pytest / make test)"}
        F2 -- "Failed (C/C++)" --> F3["Automated C/C++ Debugging Pass<br/>(debug_c_project)"]
        F3 --> F4{"Debug Pass Succeeded?"}
        F4 -- Yes --> F5["Test Verification Passed"]
        F4 -- No --> F6["Test Verification Failed"]
        F2 -- "Failed (Python)" --> F6
        F2 -- "Passed" --> F5
    end

    F5 --> G["Stage 5: Documentation & Spec Persistence<br/>(documentation_agent)"]
    F6 --> G

    subgraph STAGE_5 ["Stage 5: Documentation & Database Update"]
        G --> G1["Synthesize Project README.md & User_Manual.md"]
        G1 --> G2["Update SQLite Portfolio Database (db_manager.py)"]
    end

    G2 --> H["Stage 6: Verification Summary & Automated Git Deployment"]

    subgraph STAGE_6 ["Stage 6: Automated Deployment"]
        H --> H1{"All Tests Passed?"}
        H1 -- Yes --> H2["Stage Files: git add projects/ & reports/"]
        H2 --> H3["Commit: git commit -m 'auto(sdlc): update...'"]
        H3 --> H4["Push: git push to Remote Repository"]
        H4 --> H5["Deployment Success Output Summary"]
        H1 -- No --> H6["Skip Git Deployment & Display Diagnostics Warning"]
    end
```

---

### ⏱️ Agent Interaction & Execution Sequence Diagram

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant CLI as Main CLI (main.py)
    participant DB as SQLite DB (db_manager.py)
    participant Crew as SDLC Crew Orchestrator
    participant ReqAgent as Requirement Agent
    participant DesignAgent as Design Agent
    participant CodeAgent as Code Engineering Agent
    participant QAAgent as Testing QA Agent
    participant DocAgent as Documentation Agent
    participant Runner as Verification Runner (Pytest / Make)
    participant Git as Git Version Control

    User->>CLI: main.py run-new / evolve --prompt "..."
    CLI->>DB: Query existing projects & portfolio
    DB-->>CLI: Project list & metadata
    CLI->>CLI: Autonomous Triage (Determine project_name, mode, language)
    CLI->>Crew: Launch SDLCCrewManager(project_name)

    %% Stage 1
    Note over Crew,ReqAgent: Stage 1: Requirements Analysis
    Crew->>ReqAgent: Run requirement_task with Prompt & SRS history
    ReqAgent-->>Crew: Generate raw SRS specification
    Crew->>Crew: classify_requirements() -> Tag [NEW], [MODIFIED], [REMOVED], [UNCHANGED]
    Crew->>DB: Persist SRS version & Requirement_Delta_Report.md

    %% Stage 2
    Note over Crew,DesignAgent: Stage 2: Architecture & Dependency Modeling
    Crew->>Crew: build_dependency_graph() -> Dependency_Graph.json
    Crew->>Crew: generate_reuse_decision_report() & generate_test_impact_report()
    Crew->>DesignAgent: Run design_task with SRS & Delta Reports
    DesignAgent-->>Crew: Design.md (Clean Architecture & Mermaid Diagrams)

    %% Stage 3
    Note over Crew,CodeAgent: Stage 3: Automated Code Generation & Self-Correction
    loop Self-Correction Retry Loop (up to MAX_RETRIES)
        Crew->>CodeAgent: Run code_task (Python / C / C++)
        CodeAgent-->>Crew: Raw Code Blocks
        Crew->>Crew: Validate Syntax (ast.parse / Compiler check)
        alt Syntax / Compiler Error
            Crew-->>CodeAgent: Re-prompt with error output for self-correction
        else Syntax Passed
            Crew->>Crew: Write source files to disk
        end
    end

    %% Stage 4
    Note over Crew,QAAgent: Stage 4: Test Suite Synthesis & Execution
    Crew->>QAAgent: Run testing_task with AST signatures
    QAAgent-->>Crew: Write Pytest / C Assert tests
    Crew->>Runner: Execute Pytest / Make Test Suite
    Runner-->>Crew: Test Execution Results (Passed/Failed)
    opt C/C++ Failure
        Crew->>Runner: debug_c_project() fallback pass
    end

    %% Stage 5 & 6
    Note over Crew,DocAgent: Stage 5 & 6: Documentation & Git Deployment
    Crew->>DocAgent: Run documentation_task
    DocAgent-->>Crew: README.md & User_Manual.md
    Crew->>DB: Register project completion status
    
    alt Tests Passed
        CLI->>Git: git add, git commit, git push
        Git-->>CLI: Pushed to remote
        CLI-->>User: Display Success Summary & Deployment Status
    else Tests Failed
        CLI-->>User: Display Verification Diagnostics (Deployment Skipped)
    end
```

---

## 📌 Detailed Breakdown of Pipeline Stages

| Stage | Name | Key Components & Tools | Artifacts Produced | Description |
| :--- | :--- | :--- | :--- | :--- |
| **0** | **Autonomous Triage & Scope** | `autonomous_triage()`, `detect_language()`, SQLite DB | Triage Metadata | Classifies user prompt into `project_name`, determines execution mode (`new` vs `evolve`), and auto-detects programming language (`python`, `c`, `cpp`). |
| **1** | **Requirements Engineering** | `requirement_agent`, `classify_requirements()`, DB Manager | `SRS.md`, `Requirement_Delta_Report.md` | Synthesizes ISO/IEEE 29148 compliant software specs. Classifies every requirement line with explicit status tags: `[NEW]`, `[MODIFIED]`, `[REMOVED]`, `[UNCHANGED]`. |
| **2** | **Architecture & Dependency Modeling** | `design_agent`, `build_dependency_graph()`, `generate_reuse_decision_report()` | `Design.md`, `Dependency_Graph.json`, `Reuse_Decision_Report.md`, `Test_Impact_Report.md` | Maps static dependencies, evaluates existing codebase components for reuse, and generates Clean Architecture software specifications with visual Mermaid diagrams. |
| **3** | **Automated Code Engineering** | `code_agent`, `c_code_agent`, `ast.parse`, GCC/G++ Compiler | Source (`.py`, `.c`, `.cpp`), Headers (`.h`, `.hpp`), `Makefile` | Generates modular source code. Runs an automated syntax/compiler validation loop (`_validate_syntax`) with pre-compilation static auto-repair (`debug_c_project`), language-specific header isolation, and C module function prefixing. Falls back to domain-matched templates if retries expire. |
| **4** | **Testing & Impact Mapping** | `testing_agent`, `c_testing_agent`, Pytest / Make Runner | `tests/test_*.py` or `tests/test_runner.c` | Synthesizes assertion-backed automated test suites covering positive, boundary, and negative vectors. Makefile dynamically filters out `main()` entry files to prevent linker collisions. Executes test suites automatically and triggers automated C/C++ debugging if compilation fails. |
| **5** | **Documentation & Persistence** | `documentation_agent`, `DBManager` | Project `README.md`, `User_Manual.md`, SQLite State | Updates project-level documentation, user interaction manuals, and commits full execution history to `database/project_state.db`. |
| **6** | **Verification & Git Deployment** | `compile_project()`, `run_c_tests()`, Pytest, Git Subprocess | Git Commit & Push Logs | Verifies final test pass state. If 100% clean, automatically stages modified directories (`projects/`, `reports/`), commits changes, and pushes to remote Git repository. |

---

## 🛠️ Features & Capabilities

- 🤖 **Autonomous Multi-Agent Crew Orchestration**: CrewAI-backed specialized role-playing agents (Requirements Engineer, Software Architect, Code Engineer, QA Engineer, Technical Writer).
- 🏷️ **Requirement Delta Classification**: Precise line-item tracking using `[NEW]`, `[MODIFIED]`, `[REMOVED]`, and `[UNCHANGED]` tags across project iterations.
- 🔁 **Self-Correction & Static Guardrails**: Pre-compilation static bug repair pass (`debug_c_project`), automated standard header injection (`<limits.h>`, `<stdbool.h>`, `<iostream>`), and multi-pass error feedback loops for Python and C/C++.
- 🛡️ **C/C++ Symbol Collision Guard**: Enforces module function prefixing (e.g. `avl_remove`, `queue_push`) to prevent global namespace collisions with standard C library functions (`remove`, `rename`, `read`, `write`, `log`).
- ⚙️ **Dynamic Build Isolation**: Auto-detects non-test `main()` entry points and dynamically excludes their object files from test runner linking.
- 🌐 **Multi-Language Support**: Native generation and verification for Python 3 (Pytest), C11 (GCC/Make), and C++17 (G++/Make).
- 💾 **SQLite Portfolio & State Tracking**: Persistent schema tracking projects, SRS versions, dependency graphs, and build outcomes.
- 🔌 **LLM Provider Support**:
  - **Offline / Local**: Ollama (`qwen2.5-coder`, `llama3`).
- 🚀 **Automated Git Deployment**: Intelligent git staging, commit messaging, and remote repository push upon successful verification.

---

## 📁 Project Directory Structure

```
EvoForge/
├── agents/                      # Multi-agent definitions & crew orchestrator
│   ├── base_agent.py            # Base LLM provider initialization (Ollama)
│   └── sdlc_crew.py             # 5-stage SDLC crew pipeline & self-correction loops
├── config/                      # Agent roles, goals, and task prompt templates
│   ├── agents.yaml
│   └── tasks.yaml
├── database/                    # SQLite version control & state storage
│   ├── db_manager.py
│   └── project_state.db
├── projects/                    # Generated project codebases (Python / C / C++)
├── reports/                     # SDLC specs (SRS.md, Design.md, Delta Reports)
├── tools/                       # Core analysis, build, and static analysis utilities
│   ├── build_tools.py           # Makefile generation & C/C++ build/debug runner
│   ├── cli_ui.py                # Rich terminal UI rendering
│   ├── impact_tools.py          # Impact analysis reporting
│   ├── language_tools.py        # Language auto-detection
│   ├── requirement_tools.py     # Requirement delta classifier
│   ├── reuse_tools.py           # Asset reuse analysis
│   ├── semantic_evaluation.py   # Semantic coverage scorer
│   └── static_analysis.py       # AST & static dependency graph generator
├── .env.example                 # Environment configuration template
├── main.py                      # CLI entry point & autonomous project triage
├── README.md                    # System documentation & detailed workflow chart
└── README_offline.md            # Offline execution guide for Ollama
```

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- Python 3.8+
- Git
- *(Optional for C/C++)* GCC / G++ and `make`
- *(LLM Provider)* [Ollama](https://ollama.com)

### 2. Environment Setup
Clone the repository and set up your `.env` file:
```bash
cp .env.example .env
```

Configure your `LLM_PROVIDER` in `.env`:
```env
# For Execution via Ollama
LLM_PROVIDER=ollama
OLLAMA_MODEL=qwen2.5-coder:14b
OLLAMA_BASE_URL=http://localhost:11434
```

### 📦 Conda Environment Setup & Packed Env Restore

#### Option A: Unpacking Pre-packed Conda Archive (`evoforge_env.tar.gz`)
If you have the pre-packed environment archive (`evoforge_env.tar.gz`), unpack and activate it directly without downloading packages:

```bash
# 1. Create a directory for the unpacked environment
mkdir -p evoforge_env

# 2. Extract the environment archive
tar -xzf evoforge_env.tar.gz -C evoforge_env

# 3. Activate the environment
source evoforge_env/bin/activate

# 4. Re-bind binary paths for the target location (run once upon unpacking)
conda-unpack
```

#### Option B: Creating Environment from `environment.yml`
```bash
# Create environment from environment.yml specification
conda env create -f environment.yml -n evoforge_env
conda activate evoforge_env
```

### 3. Execution Commands

#### 🔹 Run Greenfield Project (New)
```bash
python main.py run-new --prompt "Create a Python utility that parses CSV files and exports to JSON and XML."
```

#### 🔹 Evolve Existing Project
```bash
python main.py evolve --name "csv_parser" --prompt "Add support for YAML export format."
```

#### 🔹 Interactive Mode (Direct Prompt Entry)
```bash
python main.py
```

#### 🔹 Inspect Portfolio & Diagnostics
```bash
# List all generated projects in database
python main.py list

# Inspect project artifacts and SRS specs
python main.py inspect --name "csv_parser"

# Check LLM configuration and database connection
python main.py config
```

---

## 🧪 Testing & Verification

Run the EvoForge core test suite:
```bash
pytest
```

---

## 📄 License

This project is licensed under the MIT License.
