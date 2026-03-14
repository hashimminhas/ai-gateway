import logging
import requests

from app.config import Config
from app.providers.base import AIProvider, ProviderError

logger = logging.getLogger(__name__)


class OpenAIProvider(AIProvider):
    name = "openai"

    def __init__(self):
        self.openai_key = Config.OPENAI_API_KEY
        self.nvidia_key = Config.NVIDIA_API_KEY
        self.timeout = Config.TIMEOUT_SECONDS

    def call(self, task: str, text: str) -> dict:
        logger.info("Calling OpenAI provider for task: %s", task)

        if self.openai_key and self.openai_key.startswith("sk-"):
            url = "https://api.openai.com/v1/chat/completions"
            auth = self.openai_key
            model = "gpt-4o-mini"
        elif self.nvidia_key:
            # NVIDIA-hosted Llama as OpenAI-equivalent
            url = "https://integrate.api.nvidia.com/v1/chat/completions"
            auth = self.nvidia_key
            model = "meta/llama-3.3-70b-instruct"
        else:
            raise ProviderError(self.name, "No API key configured (set NVIDIA_API_KEY or OPENAI_API_KEY)")

        headers = {
            "Authorization": f"Bearer {auth}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": f"Task: {task}\n\n{text}"}],
            "temperature": 0.3,
            "max_tokens": 1024,
        }
        try:
            resp = requests.post(
                url, headers=headers, json=payload, timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            result_text = data["choices"][0]["message"]["content"]
            logger.info("OpenAI provider call succeeded (model: %s)", model)
            return {"result": result_text, "confidence": 0.89}
        except requests.Timeout:
            raise ProviderError(self.name, "Request timed out")
        except requests.RequestException as e:
            raise ProviderError(self.name, f"API request failed: {e}")
        except (KeyError, IndexError) as e:
            raise ProviderError(self.name, f"Unexpected response format: {e}")
