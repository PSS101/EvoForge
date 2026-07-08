import os
import yaml
from dotenv import load_dotenv

# Load environment variables from .env first before importing crewai
load_dotenv()

from crewai import Agent

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
        llm_provider = os.getenv("LLM_PROVIDER", "").lower()
        openai_key = os.getenv("OPENAI_API_KEY")
        gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

        # 1. Ollama Provider
        if llm_provider == "ollama":
            from crewai import LLM
            ollama_model = os.getenv("OLLAMA_MODEL", "llama3")
            if not ollama_model.startswith("ollama/"):
                model_name = f"ollama/{ollama_model}"
            else:
                model_name = ollama_model
            
            base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            llm = LLM(
                model=model_name,
                base_url=base_url,
                temperature=0.2
            )
            # Override supports_function_calling to return False for Ollama.
            # Small local models fail or return empty responses when native tools are enabled.
            # Forcing ReAct text tool calling resolves these failures.
            llm.supports_function_calling = lambda: False
            return llm

        # 2. OpenAI Provider
        elif llm_provider == "openai" or (not llm_provider and openai_key and not gemini_key):
            if not openai_key:
                raise ValueError("LLM_PROVIDER is set to 'openai' but OPENAI_API_KEY is not defined in .env")
            from langchain_openai import ChatOpenAI
            model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
            return ChatOpenAI(
                model=model_name,
                api_key=openai_key,
                temperature=0.2
            )

        # 3. Gemini Provider / Fallback
        else:
            # If GEMINI_API_KEY is defined but GOOGLE_API_KEY is not, set it for langchain compatibility
            if os.getenv("GEMINI_API_KEY") and not os.getenv("GOOGLE_API_KEY"):
                os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]

            model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

            if gemini_key:
                from langchain_google_genai import ChatGoogleGenerativeAI
                return ChatGoogleGenerativeAI(
                    model=model_name,
                    google_api_key=gemini_key,
                    temperature=0.2
                )
            elif llm_provider == "gemini":
                raise ValueError("LLM_PROVIDER is set to 'gemini' but GEMINI_API_KEY is not defined in .env")
            
            # Default fallback: try ChatGoogleGenerativeAI assuming environment auth exists,
            # or raise helper warning.
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI
                return ChatGoogleGenerativeAI(model=model_name, temperature=0.2)
            except Exception:
                raise ValueError(
                    "No LLM configuration found. Please configure LLM_PROVIDER as 'ollama' in your .env "
                    "or set API keys for GEMINI_API_KEY or OPENAI_API_KEY."
                )

    def get_agent(self, tools=None) -> Agent:
        config = self.agent_config.get(self.agent_name)
        if not config:
            raise ValueError(f"Agent '{self.agent_name}' config not found in agents.yaml")
        
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
