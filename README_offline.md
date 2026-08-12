# Offline Execution Guide (Ollama)

This guide provides instructions on how to run the SDLC framework offline using Ollama.

## 1. Prerequisites

### Install Ollama
Download and install Ollama for Windows from [ollama.com](https://ollama.com).

### Start Ollama
Ensure Ollama is running. By default, it runs as a background service and is accessible at:
`http://localhost:11434`

### Pull a Model
Pull the LLM model you wish to use. We recommend `llama3` (or `qwen2.5:7b` for code generation):
```bash
ollama pull llama3
```
Or:
```bash
ollama pull qwen2.5
```

---

## 2. Environment Configuration

The framework is configured to use Ollama when the `LLM_PROVIDER` environment variable is set to `ollama` in the `.env` file.

Open the `.env` file in the project root and configure it as follows:

```env
# LLM Provider Selection
LLM_PROVIDER=ollama

# Ollama Local Configuration (Offline)
OLLAMA_MODEL=llama3
OLLAMA_BASE_URL=http://localhost:11434
```

*Note: You can replace `llama3` with `qwen2.5` or any other pulled model name.*

---

## 3. Running the Pipeline

Once Ollama is running and configured, run the framework using the local virtual environment.

The framework supports both Python and C/C++ projects. For C/C++ projects, the bot will auto-detect the target language, generate or use a Makefile, compile the code, and run C/C++ tests if a `tests/` directory is present.

### For Windows PowerShell:
```powershell
# Run a new project initialization
.venv\Scripts\python.exe main.py run-new --name "MyOfflineProject" --prompt "Create a simple Python utility that parses CSV files and exports them to JSON."

# Evolve an existing project
.venv\Scripts\python.exe main.py evolve --name "MyOfflineProject" --prompt "Add support for XML export format to the parser."
```

### For Windows CMD:
```cmd
.venv\Scripts\python.exe main.py run-new --name "MyOfflineProject" --prompt "Create a simple Python utility that parses CSV files and exports them to JSON."
```
