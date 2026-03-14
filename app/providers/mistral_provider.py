import logging
import requests

from app.config import Config
from app.providers.base import AIProvider, ProviderError

logger = logging.getLogger(__name__)


class MistralProvider(AIProvider):
    name = "mistral"

    def __init__(self):
        self.api_key = Config.MISTRAL_API_KEY
        self.base_url = "https://integrate.api.nvidia.com/v1/chat/completions"
        self.timeout = Config.TIMEOUT_SECONDS

    def call(self, task: str, text: str) -> dict:
        logger.info("Calling Mistral provider for task: %s", task)

        if not self.api_key:
            raise ProviderError(self.name, "MISTRAL_API_KEY not configured")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "mistralai/devstral-2-123b-instruct-2512",
            "messages": [
                {
                    "role": "user",
                    "content": f"Task: {task}\n\n{text}",
                }
            ],
            "max_tokens": 1024,
        }

        try:
            resp = requests.post(
                self.base_url,
                headers=headers,
                json=payload,
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            result_text = data["choices"][0]["message"]["content"]
            logger.info("Mistral call succeeded")
            return {"result": result_text, "confidence": 0.88}
        except requests.Timeout:
            raise ProviderError(self.name, "Request timed out")
        except requests.RequestException as e:
            raise ProviderError(self.name, f"API request failed: {e}")
        except (KeyError, IndexError) as e:
            raise ProviderError(self.name, f"Unexpected response format: {e}")
