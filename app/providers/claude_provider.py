import logging
import requests

from app.config import Config
from app.providers.base import AIProvider, ProviderError

logger = logging.getLogger(__name__)


class ClaudeProvider(AIProvider):
    name = "claude"

    def __init__(self):
        self.api_key = Config.CLAUDE_API_KEY
        self.base_url = "https://api.anthropic.com/v1/messages"
        self.timeout = Config.TIMEOUT_SECONDS

    def call(self, task: str, text: str) -> dict:
        logger.info("Calling Claude provider for task: %s", task)

        if not self.api_key:
            raise ProviderError(self.name, "CLAUDE_API_KEY not configured")

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 1024,
            "messages": [
                {
                    "role": "user",
                    "content": f"Task: {task}\n\n{text}"
                }
            ]
        }

        try:
            resp = requests.post(
                self.base_url, headers=headers,
                json=payload, timeout=self.timeout
            )
            resp.raise_for_status()
            data = resp.json()
            result_text = data["content"][0]["text"]
            logger.info("Claude call succeeded")
            return {"result": result_text, "confidence": 0.90}
        except requests.Timeout:
            raise ProviderError(self.name, "Request timed out")
        except requests.RequestException as e:
            raise ProviderError(self.name, f"API request failed: {e}")
        except (KeyError, IndexError) as e:
            raise ProviderError(self.name, f"Unexpected response format: {e}")
