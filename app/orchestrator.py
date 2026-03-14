import time
import logging

from app.config import Config
from app.circuit_breaker import CircuitBreaker
from app.providers.mistral_provider import MistralProvider
from app.providers.gemini_provider import GeminiProvider
from app.providers.openai_provider import OpenAIProvider
from app.providers.claude_provider import ClaudeProvider
from app.providers.huggingface_provider import HuggingFaceProvider
from app.providers.base import ProviderError
from app.metrics import request_count, error_count, provider_latency, failover_count as failover_metric

logger = logging.getLogger(__name__)

PROVIDER_ORDER = ["mistral", "gemini", "openai", "claude", "huggingface"]


class Orchestrator:
    def __init__(self):
        self.providers = {
            "mistral": MistralProvider(),
            "gemini": GeminiProvider(),
            "openai": OpenAIProvider(),
            "claude": ClaudeProvider(),
            "huggingface": HuggingFaceProvider(),
        }
        self.breakers = {
            name: CircuitBreaker(
                name,
                failure_threshold=Config.CIRCUIT_BREAKER_THRESHOLD,
                reset_timeout=Config.CIRCUIT_BREAKER_RESET_TIMEOUT,
            )
            for name in self.providers
        }

    def execute(self, task, text, preferred_provider="auto"):
        # When caller picks a specific provider, only try that one — no silent fallback.
        # Fallback chain only runs in "auto" mode.
        if preferred_provider != "auto" and preferred_provider in self.providers:
            order = [preferred_provider]
        else:
            order = list(PROVIDER_ORDER)

        failover_count = 0
        errors = []

        for idx, name in enumerate(order):
            breaker = self.breakers[name]
            provider = self.providers[name]

            if not breaker.can_execute():
                logger.info("Skipping %s — circuit OPEN", name)
                if idx > 0:
                    failover_count += 1
                continue

            for attempt in range(1 + Config.MAX_RETRIES):
                start = time.time()
                try:
                    result = provider.call(task, text)
                    latency_ms = int((time.time() - start) * 1000)
                    breaker.record_success()
                    provider_latency.labels(provider=name).observe(latency_ms)
                    request_count.labels(task=task, provider=name, status='success').inc()
                    logger.info(
                        "Provider %s succeeded in %dms", name, latency_ms
                    )
                    return {
                        "provider_used": name,
                        "result": result["result"],
                        "confidence": result["confidence"],
                        "latency_ms": latency_ms,
                        "failover_count": failover_count,
                    }
                except ProviderError as e:
                    latency_ms = int((time.time() - start) * 1000)
                    logger.warning(
                        "Provider %s attempt %d failed (%dms): %s",
                        name, attempt + 1, latency_ms, e.message,
                    )
                    provider_latency.labels(provider=name).observe(latency_ms)
                    error_count.labels(provider=name).inc()
                    errors.append(f"{name}: {e.message}")

            breaker.record_failure()
            if idx > 0:
                failover_count += 1
                prev = order[idx - 1]
                failover_metric.labels(from_provider=prev, to_provider=name).inc()

        request_count.labels(task=task, provider='none', status='error').inc()
        logger.error("All providers failed: %s", "; ".join(errors))
        return {
            "provider_used": None,
            "result": None,
            "confidence": 0.0,
            "latency_ms": 0,
            "failover_count": failover_count,
            "error": "All providers failed",
            "details": errors,
        }
