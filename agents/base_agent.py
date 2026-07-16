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
        # Determine which LLM provider to use based on env variables
        llm_provider = os.getenv("LLM_PROVIDER", "").lower().strip()
        openai_key = os.getenv("OPENAI_API_KEY", "").strip()
        gemini_key = (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip()

        # 1. Ollama Provider (prioritized if explicitly set)
        if llm_provider == "ollama":
            return self._init_ollama_llm()

        # 2. OpenAI Provider
        elif llm_provider == "openai":
            if not openai_key:
                raise ValueError("LLM_PROVIDER is set to 'openai' but OPENAI_API_KEY is not defined in .env")
            from langchain_openai import ChatOpenAI
            model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
            return ChatOpenAI(
                model=model_name,
                api_key=openai_key,
                temperature=0.2
            )

        # 3. Gemini Provider
        elif llm_provider == "gemini":
            if not gemini_key:
                raise ValueError("LLM_PROVIDER is set to 'gemini' but GEMINI_API_KEY or GOOGLE_API_KEY is not defined in .env")
            if os.getenv("GEMINI_API_KEY") and not os.getenv("GOOGLE_API_KEY"):
                os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(
                model=os.getenv("GEMINI_MODEL", "gemini-1.5-flash"),
                google_api_key=gemini_key,
                temperature=0.2
            )

        # 4. Auto-detect based on available API keys
        elif openai_key:
            print("Warning: LLM_PROVIDER not set but OPENAI_API_KEY found. Using OpenAI.")
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                api_key=openai_key,
                temperature=0.2
            )

        elif gemini_key:
            print("Warning: LLM_PROVIDER not set but GEMINI_API_KEY found. Using Gemini.")
            if os.getenv("GEMINI_API_KEY") and not os.getenv("GOOGLE_API_KEY"):
                os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(
                model=os.getenv("GEMINI_MODEL", "gemini-1.5-flash"),
                temperature=0.2
            )

        # 5. Fallback to Ollama if no provider is explicitly set
        else:
            print("Warning: LLM_PROVIDER not set. Attempting to use Ollama as default.")
            return self._init_ollama_llm()

    def _init_ollama_llm(self):
        """Initialize Ollama LLM client via subprocess."""
        try:
            from langchain_core.language_models.llm import LLM as BaseLLM
        except ImportError:
            try:
                from langchain.llms.base import LLM as BaseLLM
            except ImportError:
                BaseLLM = object

        class OllamaClient(BaseLLM):
            """Lightweight Ollama client compatible with LangChain and CrewAI."""
            model_name: str = "ollama"
            ollama_model: str = None
            base_url: str = None

            def __init__(self, ollama_model=None, base_url=None, **kwargs):
                super().__init__(**kwargs)
                self.ollama_model = ollama_model or os.getenv("OLLAMA_MODEL", "gemma3:1b")
                self.base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
                print(f"[OK] Initialized Ollama client: model={self.ollama_model}")

            @property
            def _llm_type(self) -> str:
                return "ollama"

            def _call(self, prompt: str, **kwargs) -> str:
                return self.generate(prompt)

            def generate(self, prompt: str) -> str:
                import subprocess
                cmd = ["ollama", "run", self.ollama_model]
                try:
                    res = subprocess.run(
                        cmd,
                        input=prompt,
                        capture_output=True,
                        text=True,
                        check=False,
                        timeout=60,
                        encoding="utf-8",
                        errors="replace"
                    )
                    if res.returncode != 0:
                        error_msg = (res.stderr or res.stdout or "Unknown error")[:200]
                        return f"OLLAMA_ERROR: {error_msg}"
                    return res.stdout.strip()
                except subprocess.TimeoutExpired:
                    return "OLLAMA_TIMEOUT: Response took too long"
                except FileNotFoundError:
                    return "OLLAMA_NOT_FOUND: 'ollama' not in PATH"
                except Exception as e:
                    return f"OLLAMA_ERROR: {type(e).__name__}: {str(e)[:100]}"

            def call(self, prompt: str, **kwargs) -> str:
                return self.generate(prompt)

            def acall(self, prompt: str, **kwargs) -> str:
                return self.generate(prompt)

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
                max_iter=5
            )

        return self._build_local_agent(config)

    def _build_local_agent(self, config):
        class LocalAgent:
            def __init__(self, role, goal, backstory, llm_client):
                self.role = role
                self.goal = goal
                self.backstory = backstory
                self.llm = llm_client

            def run(self, prompt: str) -> str:
                # Use the underlying llm client to generate a response.
                try:
                    if hasattr(self.llm, 'generate'):
                        result = self.llm.generate(prompt)
                        return str(result)
                    if hasattr(self.llm, 'call'):
                        result = self.llm.call(prompt)
                        return str(result)
                    if hasattr(self.llm, 'acall'):
                        result = self.llm.acall(prompt)
                        return str(result)
                    if hasattr(self.llm, '__call__'):
                        result = self.llm(prompt)
                        return str(result)
                except Exception as e:
                    return f"LOCAL_AGENT_ERROR: {e}"
                return ""

        return LocalAgent(config["role"], config["goal"], config["backstory"], self.llm)

    def get_local_agent(self):
        config = self.agent_config.get(self.agent_name)
        if not config:
            raise ValueError(f"Agent '{self.agent_name}' config not found in agents.yaml")
        return self._build_local_agent(config)

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
