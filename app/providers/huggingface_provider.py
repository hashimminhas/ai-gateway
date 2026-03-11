import logging
import requests

from app.config import Config
from app.providers.base import AIProvider, ProviderError

logger = logging.getLogger(__name__)


class HuggingFaceProvider(AIProvider):
    name = "huggingface"

    def __init__(self):
        self.api_key = Config.HF_API_KEY
        self.base_url = (
            "https://api-inference.huggingface.co/models"
            "/facebook/bart-large-mnli"
        )
        self.timeout = Config.TIMEOUT_SECONDS

    def call(self, task: str, text: str) -> dict:
        logger.info("Calling HuggingFace provider for task: %s", task)

        if not self.api_key:
            raise ProviderError(self.name, "HF_API_KEY not configured")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "inputs": f"Task: {task}\n\n{text}",
            "parameters": {"max_length": 512},
        }

        try:
            resp = requests.post(
                self.base_url, headers=headers,
                json=payload, timeout=self.timeout
            )
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list) and len(data) > 0:
                result_text = data[0].get("summary_text", str(data[0]))
            else:
                result_text = str(data)
            logger.info("HuggingFace call succeeded")
            return {"result": result_text, "confidence": 0.75}
        except requests.Timeout:
            raise ProviderError(self.name, "Request timed out")
        except requests.RequestException as e:
            raise ProviderError(self.name, f"API request failed: {e}")
        except (KeyError, IndexError) as e:
            raise ProviderError(self.name, f"Unexpected response format: {e}")
