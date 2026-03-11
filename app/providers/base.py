from abc import ABC, abstractmethod


class ProviderError(Exception):
    def __init__(self, provider, message):
        self.provider = provider
        self.message = message
        super().__init__(f"[{provider}] {message}")


class AIProvider(ABC):
    name = "base"

    @abstractmethod
    def call(self, task: str, text: str) -> dict:
        """Call the AI provider and return {"result": str, "confidence": float}."""
        pass
