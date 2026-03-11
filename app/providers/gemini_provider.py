import logging
import requests

from app.config import Config
from app.providers.base import AIProvider, ProviderError

logger = logging.getLogger(__name__)


class GeminiProvider(AIProvider):
    name = "gemini"

    def __init__(self):
        self.api_key = Config.GEMINI_API_KEY
        self.base_url = (
            "https://generativelanguage.googleapis.com/v1beta"
            "/models/gemini-1.5-flash:generateContent"
        )
        self.timeout = Config.TIMEOUT_SECONDS

    def call(self, task: str, text: str) -> dict:
        logger.info("Calling Gemini provider for task: %s", task)

        if not self.api_key:
            raise ProviderError(self.name, "GEMINI_API_KEY not configured")

        url = f"{self.base_url}?key={self.api_key}"
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": f"Task: {task}\n\n{text}"}
                    ]
                }
            ]
        }

        try:
            resp = requests.post(url, json=payload, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            result_text = (
                data["candidates"][0]["content"]["parts"][0]["text"]
            )
            logger.info("Gemini call succeeded")
            return {"result": result_text, "confidence": 0.85}
        except requests.Timeout:
            raise ProviderError(self.name, "Request timed out")
        except requests.RequestException as e:
            raise ProviderError(self.name, f"API request failed: {e}")
        except (KeyError, IndexError) as e:
            raise ProviderError(self.name, f"Unexpected response format: {e}")
