import logging
import requests

from app.config import Config
from app.providers.base import AIProvider, ProviderError

logger = logging.getLogger(__name__)


class ClaudeProvider(AIProvider):
    name = "claude"

    def __init__(self):
        self.claude_key = Config.CLAUDE_API_KEY
        self.nvidia_key = Config.NVIDIA_API_KEY
        self.timeout = Config.TIMEOUT_SECONDS

    def call(self, task: str, text: str) -> dict:
        logger.info("Calling Claude provider for task: %s", task)

        if self.claude_key:
            return self._call_anthropic(task, text)
        elif self.nvidia_key:
            return self._call_nvidia(task, text)
        else:
            raise ProviderError(self.name, "No API key configured (set NVIDIA_API_KEY or CLAUDE_API_KEY)")

    def _call_anthropic(self, task: str, text: str) -> dict:
        headers = {
            "x-api-key": self.claude_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "claude-3-5-haiku-20241022",
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": f"Task: {task}\n\n{text}"}],
        }
        try:
            resp = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers, json=payload, timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            result_text = data["content"][0]["text"]
            logger.info("Claude (Anthropic) call succeeded")
            return {"result": result_text, "confidence": 0.90}
        except requests.Timeout:
            raise ProviderError(self.name, "Request timed out")
        except requests.RequestException as e:
            raise ProviderError(self.name, f"API request failed: {e}")
        except (KeyError, IndexError) as e:
            raise ProviderError(self.name, f"Unexpected response format: {e}")

    def _call_nvidia(self, task: str, text: str) -> dict:
        headers = {
            "Authorization": f"Bearer {self.nvidia_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "mistralai/mistral-large-2-instruct",
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
            logger.info("Claude (via NVIDIA/Mistral-Large) call succeeded")
            return {"result": result_text, "confidence": 0.90}
        except requests.Timeout:
            raise ProviderError(self.name, "Request timed out")
        except requests.RequestException as e:
            raise ProviderError(self.name, f"API request failed: {e}")
        except (KeyError, IndexError) as e:
            raise ProviderError(self.name, f"Unexpected response format: {e}")
