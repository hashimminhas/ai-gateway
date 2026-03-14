from unittest.mock import patch, MagicMock
from app.orchestrator import Orchestrator
from app.providers.base import ProviderError
from app.circuit_breaker import STATE_OPEN


@patch('app.orchestrator.HuggingFaceProvider')
@patch('app.orchestrator.ClaudeProvider')
@patch('app.orchestrator.GeminiProvider')
@patch('app.orchestrator.MistralProvider')
def test_fallback_on_failure(mock_mistral_cls, mock_gemini_cls, mock_claude_cls, mock_hf_cls):
    mock_mistral = MagicMock()
    mock_mistral.name = 'mistral'
    mock_mistral.call.side_effect = ProviderError('mistral', 'not configured')
    mock_mistral_cls.return_value = mock_mistral

    mock_gemini = MagicMock()
    mock_gemini.name = 'gemini'
    mock_gemini.call.side_effect = ProviderError('gemini', 'timeout')
    mock_gemini_cls.return_value = mock_gemini

    mock_claude = MagicMock()
    mock_claude.name = 'claude'
    mock_claude.call.return_value = {"result": "done", "confidence": 0.90}
    mock_claude_cls.return_value = mock_claude

    mock_hf = MagicMock()
    mock_hf.name = 'huggingface'
    mock_hf_cls.return_value = mock_hf

    orch = Orchestrator()
    result = orch.execute("summarize", "test text")

    assert result["provider_used"] == "claude"
    assert result["result"] == "done"
    assert result["confidence"] == 0.90
    assert "latency_ms" in result


@patch('app.orchestrator.HuggingFaceProvider')
@patch('app.orchestrator.ClaudeProvider')
@patch('app.orchestrator.GeminiProvider')
@patch('app.orchestrator.MistralProvider')
def test_skip_open_circuit(mock_mistral_cls, mock_gemini_cls, mock_claude_cls, mock_hf_cls):
    mock_mistral = MagicMock()
    mock_mistral.name = 'mistral'
    mock_mistral.call.side_effect = ProviderError('mistral', 'not configured')
    mock_mistral_cls.return_value = mock_mistral

    mock_gemini = MagicMock()
    mock_gemini.name = 'gemini'
    mock_gemini_cls.return_value = mock_gemini

    mock_claude = MagicMock()
    mock_claude.name = 'claude'
    mock_claude.call.return_value = {"result": "ok", "confidence": 0.90}
    mock_claude_cls.return_value = mock_claude

    mock_hf = MagicMock()
    mock_hf.name = 'huggingface'
    mock_hf_cls.return_value = mock_hf

    orch = Orchestrator()
    # Force gemini circuit to OPEN
    orch.breakers["gemini"].state = STATE_OPEN
    orch.breakers["gemini"].last_failure_time = 9999999999

    result = orch.execute("summarize", "test text")

    assert result["provider_used"] == "claude"
    mock_gemini.call.assert_not_called()


@patch('app.orchestrator.HuggingFaceProvider')
@patch('app.orchestrator.ClaudeProvider')
@patch('app.orchestrator.GeminiProvider')
@patch('app.orchestrator.MistralProvider')
def test_result_structure(mock_mistral_cls, mock_gemini_cls, mock_claude_cls, mock_hf_cls):
    mock_mistral = MagicMock()
    mock_mistral.name = 'mistral'
    mock_mistral.call.side_effect = ProviderError('mistral', 'not configured')
    mock_mistral_cls.return_value = mock_mistral

    mock_gemini = MagicMock()
    mock_gemini.name = 'gemini'
    mock_gemini.call.return_value = {"result": "summary", "confidence": 0.85}
    mock_gemini_cls.return_value = mock_gemini

    mock_claude = MagicMock()
    mock_claude.name = 'claude'
    mock_claude_cls.return_value = mock_claude

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
@patch('app.orchestrator.ClaudeProvider')
@patch('app.orchestrator.GeminiProvider')
@patch('app.orchestrator.MistralProvider')
def test_all_providers_fail(mock_mistral_cls, mock_gemini_cls, mock_claude_cls, mock_hf_cls):
    for mock_cls, name in [(mock_mistral_cls, 'mistral'),
                           (mock_gemini_cls, 'gemini'),
                           (mock_claude_cls, 'claude'),
                           (mock_hf_cls, 'huggingface')]:
        mock_provider = MagicMock()
        mock_provider.name = name
        mock_provider.call.side_effect = ProviderError(name, 'fail')
        mock_cls.return_value = mock_provider

    orch = Orchestrator()
    result = orch.execute("summarize", "test")

    assert result["provider_used"] is None
    assert result["error"] == "All providers failed"
