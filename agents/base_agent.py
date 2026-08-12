import os
import yaml
from dotenv import load_dotenv

# Load environment variables from .env first before importing crewai
load_dotenv()

# Defensive import: prefer crewai.Agent if available, otherwise provide a local fallback
try:
    from crewai import Agent
    HAS_CREW = True
except Exception:
    Agent = None
    HAS_CREW = False

class BaseAgent:
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config")
        self.agent_config = self._load_config("agents.yaml")
        self.task_config = self._load_config("tasks.yaml")
        self.llm = self._init_llm()

    def _load_config(self, filename: str) -> dict:
        filepath = os.path.join(self.config_dir, filename)
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Configuration file not found: {filepath}")
        with open(filepath, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def _init_llm(self):
        # Prefer crewai's LLM wrapper for local Ollama if available
        try:
            if HAS_CREW:
                from crewai import LLM
                ollama_model = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:14b")
                if not ollama_model.startswith("ollama/"):
                    model_name = f"ollama/{ollama_model}"
                else:
                    model_name = ollama_model
                base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
                llm = LLM(
                    model=model_name,
                    base_url=base_url,
                    temperature=0.1,
                    timeout=1800,
                    max_tokens=4096,
                    num_ctx=16384
                )
                llm.supports_function_calling = lambda: False
                return llm
        except Exception:
            pass

        # Fallback: call Ollama REST API directly
        class OllamaClient:
            def __init__(self, model_name=None, base_url=None, temperature=0.2):
                self.model = model_name or os.getenv("OLLAMA_MODEL", "qwen2.5-coder:14b")
                self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")).rstrip("/")
                self.temperature = temperature

            def generate(self, prompt: str) -> str:
                import urllib.request
                import json as _json
                payload = _json.dumps({
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": self.temperature}
                }).encode("utf-8")
                req = urllib.request.Request(
                    f"{self.base_url}/api/generate",
                    data=payload,
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )
                try:
                    with urllib.request.urlopen(req, timeout=1800) as resp:
                        data = _json.loads(resp.read().decode("utf-8"))
                        return data.get("response", "").strip()
                except Exception as e:
                    return f"ERROR_RUNNING_OLLAMA: {e}"

        return OllamaClient()

    def get_agent(self, tools=None):
        config = self.agent_config.get(self.agent_name)
        if not config:
            raise ValueError(f"Agent '{self.agent_name}' config not found in agents.yaml")

        # If crewai.Agent is available, construct it
        if HAS_CREW and Agent is not None:
            return Agent(
                role=config["role"],
                goal=config["goal"],
                backstory=config["backstory"],
                llm=self.llm,
                tools=tools or [],
                verbose=True,
                allow_delegation=False,
                max_iter=15
            )

        # Fallback: simple local agent that uses the LLM client created in _init_llm
        class LocalAgent:
            def __init__(self, role, goal, backstory, llm_client):
                self.role = role
                self.goal = goal
                self.backstory = backstory
                self.llm = llm_client

            def run(self, prompt: str) -> str:
                # Use the underlying llm client to generate a response
                try:
                    # OllamaClient defines .generate
                    if hasattr(self.llm, 'generate') and callable(getattr(self.llm, 'generate')):
                        res = self.llm.generate(prompt)
                        return res if isinstance(res, str) else str(res)
                    # LangChain/Chat models specify .invoke
                    if hasattr(self.llm, 'invoke') and callable(getattr(self.llm, 'invoke')):
                        res = self.llm.invoke(prompt)
                        if hasattr(res, 'content'):
                            return str(res.content)
                        return str(res)
                    if callable(self.llm):
                        res = self.llm(prompt)
                        if hasattr(res, 'content'):
                            return str(res.content)
                        return str(res)
                except Exception as e:
                    return f"LOCAL_AGENT_ERROR: {e}"
                return ""

        return LocalAgent(config["role"], config["goal"], config["backstory"], self.llm)

    def get_task_description(self, task_name: str) -> str:
        config = self.task_config.get(task_name)
        if not config:
            raise ValueError(f"Task '{task_name}' config not found in tasks.yaml")
        return config["description"]

    def get_task_expected_output(self, task_name: str) -> str:
        config = self.task_config.get(task_name)
        if not config:
            raise ValueError(f"Task '{task_name}' config not found in tasks.yaml")
        return config["expected_output"]
