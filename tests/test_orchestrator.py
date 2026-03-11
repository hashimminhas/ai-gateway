from unittest.mock import patch, MagicMock
from app.orchestrator import Orchestrator
from app.providers.base import ProviderError
from app.circuit_breaker import STATE_OPEN


@patch('app.orchestrator.HuggingFaceProvider')
@patch('app.orchestrator.OpenAIProvider')
@patch('app.orchestrator.GeminiProvider')
def test_fallback_on_failure(mock_gemini_cls, mock_openai_cls, mock_hf_cls):
    mock_gemini = MagicMock()
    mock_gemini.name = 'gemini'
    mock_gemini.call.side_effect = ProviderError('gemini', 'timeout')
    mock_gemini_cls.return_value = mock_gemini

    mock_openai = MagicMock()
    mock_openai.name = 'openai'
    mock_openai.call.return_value = {"result": "done", "confidence": 0.90}
    mock_openai_cls.return_value = mock_openai

    mock_hf = MagicMock()
    mock_hf.name = 'huggingface'
    mock_hf_cls.return_value = mock_hf

    orch = Orchestrator()
    result = orch.execute("summarize", "test text")

    assert result["provider_used"] == "openai"
    assert result["result"] == "done"
    assert result["confidence"] == 0.90
    assert "latency_ms" in result


@patch('app.orchestrator.HuggingFaceProvider')
@patch('app.orchestrator.OpenAIProvider')
@patch('app.orchestrator.GeminiProvider')
def test_skip_open_circuit(mock_gemini_cls, mock_openai_cls, mock_hf_cls):
    mock_gemini = MagicMock()
    mock_gemini.name = 'gemini'
    mock_gemini_cls.return_value = mock_gemini

    mock_openai = MagicMock()
    mock_openai.name = 'openai'
    mock_openai.call.return_value = {"result": "ok", "confidence": 0.90}
    mock_openai_cls.return_value = mock_openai

    mock_hf = MagicMock()
    mock_hf.name = 'huggingface'
    mock_hf_cls.return_value = mock_hf

    orch = Orchestrator()
    # Force gemini circuit to OPEN
    orch.breakers["gemini"].state = STATE_OPEN
    orch.breakers["gemini"].last_failure_time = 9999999999

    result = orch.execute("summarize", "test text")

    assert result["provider_used"] == "openai"
    mock_gemini.call.assert_not_called()


@patch('app.orchestrator.HuggingFaceProvider')
@patch('app.orchestrator.OpenAIProvider')
@patch('app.orchestrator.GeminiProvider')
def test_result_structure(mock_gemini_cls, mock_openai_cls, mock_hf_cls):
    mock_gemini = MagicMock()
    mock_gemini.name = 'gemini'
    mock_gemini.call.return_value = {"result": "summary", "confidence": 0.85}
    mock_gemini_cls.return_value = mock_gemini

    mock_openai = MagicMock()
    mock_openai.name = 'openai'
    mock_openai_cls.return_value = mock_openai

    mock_hf = MagicMock()
    mock_hf.name = 'huggingface'
    mock_hf_cls.return_value = mock_hf

    orch = Orchestrator()
    result = orch.execute("summarize", "test")

    assert "provider_used" in result
    assert "result" in result
    assert "confidence" in result
    assert "latency_ms" in result
    assert "failover_count" in result


@patch('app.orchestrator.HuggingFaceProvider')
@patch('app.orchestrator.OpenAIProvider')
@patch('app.orchestrator.GeminiProvider')
def test_all_providers_fail(mock_gemini_cls, mock_openai_cls, mock_hf_cls):
    for mock_cls, name in [(mock_gemini_cls, 'gemini'),
                           (mock_openai_cls, 'openai'),
                           (mock_hf_cls, 'huggingface')]:
        mock_provider = MagicMock()
        mock_provider.name = name
        mock_provider.call.side_effect = ProviderError(name, 'fail')
        mock_cls.return_value = mock_provider

    orch = Orchestrator()
    result = orch.execute("summarize", "test")

    assert result["provider_used"] is None
    assert result["error"] == "All providers failed"
