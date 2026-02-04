"""
LLM Provider Abstraction
Allows swapping between Gemini (Vertex AI) and local LLMs (Ollama via LiteLLM).
"""

import os
from abc import ABC, abstractmethod
from typing import Optional


class LLMProvider(ABC):
    """Abstract base class for LLM providers"""

    @abstractmethod
    def get_model_string(self) -> str:
        """Return model string for ADK Agent constructor"""
        pass

    @abstractmethod
    def format_response(self, prompt: str) -> str:
        """Generate a response from the LLM"""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is available"""
        pass


class GeminiProvider(LLMProvider):
    """Gemini via Vertex AI"""

    def __init__(self, project_id: str = None, location: str = None):
        self.project_id = project_id or os.environ.get("GOOGLE_PROJECT_ID")
        self.location = location or os.environ.get("GOOGLE_LOCATION", "us-central1")
        self.model = None
        self._initialize()

    def _initialize(self):
        """Initialize Vertex AI and model"""
        try:
            import vertexai
            from vertexai.generative_models import GenerativeModel

            vertexai.init(project=self.project_id, location=self.location)
            self.model = GenerativeModel("gemini-2.5-flash")
        except Exception as e:
            print(f"Failed to initialize Gemini: {e}")
            self.model = None

    def get_model_string(self) -> str:
        """Return model string for ADK"""
        return "gemini-2.0-flash"

    def format_response(self, prompt: str) -> str:
        """Generate response using Gemini"""
        if not self.model:
            raise RuntimeError("Gemini model not initialized")
        response = self.model.generate_content(prompt)
        return response.text

    def is_available(self) -> bool:
        """Check if Gemini is available"""
        return self.model is not None


class OllamaProvider(LLMProvider):
    """Local LLM via Ollama (through LiteLLM)"""

    def __init__(self, model_name: str = "llama3.1:8b", base_url: str = None):
        self.model_name = model_name
        self.base_url = base_url or os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        self._available = None

    def get_model_string(self) -> str:
        """Return model string for ADK LiteLLM integration"""
        return f"ollama/{self.model_name}"

    def format_response(self, prompt: str) -> str:
        """Generate response using Ollama via LiteLLM"""
        try:
            import litellm
            response = litellm.completion(
                model=f"ollama/{self.model_name}",
                messages=[{"role": "user", "content": prompt}],
                api_base=self.base_url
            )
            return response.choices[0].message.content
        except Exception as e:
            raise RuntimeError(f"Ollama generation failed: {e}")

    def is_available(self) -> bool:
        """Check if Ollama is available"""
        if self._available is not None:
            return self._available

        try:
            import requests
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            self._available = response.status_code == 200
        except Exception:
            self._available = False

        return self._available


def create_provider(provider_type: str = None) -> LLMProvider:
    """Factory function to create the appropriate LLM provider"""
    provider_type = provider_type or os.environ.get("JAXAI_LLM_PROVIDER", "gemini")

    if provider_type.lower() == "ollama":
        model = os.environ.get("JAXAI_OLLAMA_MODEL", "llama3.1:8b")
        return OllamaProvider(model_name=model)
    else:
        return GeminiProvider()
