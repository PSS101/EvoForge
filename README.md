# EvoForge

EvoForge is an incremental software evolution framework that combines requirement analysis, static code intelligence, component reuse, and offline AI execution into a local development workflow.

## Offline Execution with Ollama

This repository can run locally with Ollama and a Python virtual environment. The core agent framework is designed to use Ollama when `LLM_PROVIDER=ollama` is set.

### Prerequisites

- Python 3.11 or later installed.
- Ollama installed and running locally.
- A pulled Ollama model such as `gemma3:1b`.

### Recommended setup

```powershell
Set-Location D:\DRDO PROJ.worktrees\agents-incremental-software-evolution-framework
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Configure offline Ollama in `.env`

```env
LLM_PROVIDER=ollama
OLLAMA_MODEL=gemma3:1b
OLLAMA_BASE_URL=http://localhost:11434
CREWAI_DISABLE_TELEMETRY=true
OTEL_SDK_DISABLED=true
CREWAI_TRACING_ENABLED=false
```

### Verify Ollama model

```powershell
ollama --version
ollama list
```

You should see `gemma3:1b` in the model list.

## Running the Framework

### New project initialization

```powershell
.\.venv\Scripts\python.exe main.py run-new --name "MyOfflineProject" --prompt "Create a simple Python utility that parses CSV files and exports them to JSON."
```

### Evolve an existing project

```powershell
.\.venv\Scripts\python.exe main.py evolve --name "MyOfflineProject" --prompt "Add support for XML export format to the parser."
```

## Calculator Example

A simple calculator example is available under `projects/calculator`.

### Run the calculator

```powershell
.\.venv\Scripts\python.exe .\projects\calculator\main.py
```

Supported operations:
- `+` addition
- `-` subtraction
- `*` multiplication
- `/` division
- `%` modulo
- `s` square root
- `h` history
- `q` quit

### Example: square root

Enter `s` and then enter a number, for example `9`, to compute `sqrt(9) = 3.0`.

## Tests

Run the calculator tests with:

```powershell
.\.venv\Scripts\python.exe -m pytest .\projects\calculator\tests\test_calculator.py -q
```

### Fallback smoke tests
If generated test files are invalid or fail to run, the framework can automatically generate a deterministic smoke test suite that validates the project modules can be imported cleanly.

## Notes

- The calculator app runs locally and does not require Ollama.
- The framework is configured for offline Ollama with `gemma3:1b`.
- If you prefer a different local model, update `OLLAMA_MODEL` in `.env`.
