import logging
import requests

from app.config import Config
from app.providers.base import AIProvider, ProviderError

logger = logging.getLogger(__name__)


class OpenAIProvider(AIProvider):
    name = "openai"

    def __init__(self):
        self.api_key = Config.OPENAI_API_KEY
        self.base_url = "https://api.openai.com/v1/chat/completions"
        self.timeout = Config.TIMEOUT_SECONDS

    def call(self, task: str, text: str) -> dict:
        logger.info("Calling OpenAI provider for task: %s", task)

        if not self.api_key:
            raise ProviderError(self.name, "OPENAI_API_KEY not configured")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": f"Task: {task}\n\n{text}"},
            ],
            "temperature": 0.3,
        }

        try:
            resp = requests.post(
                self.base_url, headers=headers,
                json=payload, timeout=self.timeout
            )
            resp.raise_for_status()
            data = resp.json()
            result_text = data["choices"][0]["message"]["content"]
            logger.info("OpenAI call succeeded")
            return {"result": result_text, "confidence": 0.90}
        except requests.Timeout:
            raise ProviderError(self.name, "Request timed out")
        except requests.RequestException as e:
            raise ProviderError(self.name, f"API request failed: {e}")
        except (KeyError, IndexError) as e:
            raise ProviderError(self.name, f"Unexpected response format: {e}")
