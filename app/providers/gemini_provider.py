import logging
import requests

from app.config import Config
from app.providers.base import AIProvider, ProviderError

logger = logging.getLogger(__name__)


class GeminiProvider(AIProvider):
    name = "gemini"

    def __init__(self):
        # Use native Gemini key if present, otherwise route through NVIDIA
        self.gemini_key = Config.GEMINI_API_KEY
        self.nvidia_key = Config.NVIDIA_API_KEY
        self.timeout = Config.TIMEOUT_SECONDS

    def call(self, task: str, text: str) -> dict:
        logger.info("Calling Gemini provider for task: %s", task)

        if self.nvidia_key:
            return self._call_nvidia(task, text)
        elif self.gemini_key:
            return self._call_google(task, text)
        else:
            raise ProviderError(self.name, "No API key configured (set NVIDIA_API_KEY or GEMINI_API_KEY)")

    def _call_nvidia(self, task: str, text: str) -> dict:
        headers = {
            "Authorization": f"Bearer {self.nvidia_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "google/gemma-3-27b-it",
            "messages": [{"role": "user", "content": f"Task: {task}\n\n{text}"}],
            "max_tokens": 1024,
        }
        try:
            resp = requests.post(
                "https://integrate.api.nvidia.com/v1/chat/completions",
                headers=headers, json=payload, timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            result_text = data["choices"][0]["message"]["content"]
            logger.info("Gemini (via NVIDIA/Gemma) call succeeded")
            return {"result": result_text, "confidence": 0.85}
        except requests.Timeout:
            raise ProviderError(self.name, "Request timed out")
        except requests.RequestException as e:
            raise ProviderError(self.name, f"API request failed: {e}")
        except (KeyError, IndexError) as e:
            raise ProviderError(self.name, f"Unexpected response format: {e}")

    def _call_google(self, task: str, text: str) -> dict:
        url = (
            "https://generativelanguage.googleapis.com/v1beta"
            f"/models/gemini-pro:generateContent?key={self.gemini_key}"
        )
        payload = {"contents": [{"parts": [{"text": f"Task: {task}\n\n{text}"}]}]}
        try:
            resp = requests.post(url, json=payload, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            result_text = data["candidates"][0]["content"]["parts"][0]["text"]
            logger.info("Gemini (Google API) call succeeded")
            return {"result": result_text, "confidence": 0.85}
        except requests.Timeout:
            raise ProviderError(self.name, "Request timed out")
        except requests.RequestException as e:
            raise ProviderError(self.name, f"API request failed: {e}")
        except (KeyError, IndexError) as e:
            raise ProviderError(self.name, f"Unexpected response format: {e}")
