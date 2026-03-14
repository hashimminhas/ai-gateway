from unittest.mock import patch

from app import db
from app.models import AIRequest


def test_health(client):
    resp = client.get('/health')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['status'] == 'healthy'
    assert 'timestamp' in data


def test_ai_task_missing_fields(client):
    resp = client.post('/ai/task', json={})
    assert resp.status_code == 400

    resp = client.post('/ai/task', json={"task": "summarize"})
    assert resp.status_code == 400

    resp = client.post('/ai/task', json={"text": "hello"})
    assert resp.status_code == 400


def test_ai_task_no_json(client):
    resp = client.post('/ai/task', data="not json")
    assert resp.status_code == 400


@patch('app.routes.orchestrator.execute')
def test_ai_task_valid(mock_execute, client):
    mock_execute.return_value = {
        "provider_used": "gemini",
        "result": "Summary of text",
        "confidence": 0.85,
        "latency_ms": 200,
        "failover_count": 0,
    }
    resp = client.post('/ai/task', json={
        "task": "summarize",
        "text": "Some long text to summarize",
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['provider_used'] == 'gemini'
    assert data['result'] == 'Summary of text'
    assert data['confidence'] == 0.85
    assert data['latency_ms'] == 200


@patch('app.routes.orchestrator.execute')
def test_ai_task_all_fail(mock_execute, client):
    mock_execute.return_value = {
        "provider_used": None,
        "result": None,
        "confidence": 0.0,
        "latency_ms": 0,
        "failover_count": 2,
        "error": "All providers failed",
        "details": ["gemini: timeout", "openai: timeout"],
    }
    resp = client.post('/ai/task', json={
        "task": "summarize",
        "text": "Some text",
    })
    assert resp.status_code == 503


@patch('app.routes.orchestrator.execute')
def test_ai_task_invoice_decision(mock_execute, client):
    mock_execute.return_value = {
        "provider_used": "openai",
        "result": "Invoice total amount is $500, paid in full.",
        "confidence": 0.90,
        "latency_ms": 300,
        "failover_count": 0,
    }
    resp = client.post('/ai/task', json={
        "task": "invoice_check",
        "text": "Invoice for $500 total amount due",
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'decision' in data
    assert data['decision']['decision'] in ('PASS', 'FAIL', 'NEEDS_INFO')


def test_provider_status(client):
    resp = client.get('/provider/status')
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'nvidia_fallback_enabled' in data
    assert 'openai_native_enabled' in data
    assert 'claude_native_enabled' in data
    assert 'gemini_native_enabled' in data
    assert 'huggingface_native_enabled' in data


def test_cleanup_history_errors(client, app):
    with app.app_context():
        db.session.add(AIRequest(
            task='summarize',
            input_text='ok',
            provider='mistral',
            latency_ms=100,
            status='success',
            result_summary='ok',
            error_message=None,
        ))
        db.session.add(AIRequest(
            task='summarize',
            input_text='bad',
            provider='',
            latency_ms=0,
            status='error',
            result_summary='',
            error_message='timeout',
        ))
        db.session.commit()

    cleanup_resp = client.post('/history/cleanup', json={"older_than_minutes": 0})
    assert cleanup_resp.status_code == 200
    cleanup_data = cleanup_resp.get_json()
    assert cleanup_data['deleted'] == 1

    history_resp = client.get('/history')
    assert history_resp.status_code == 200
    rows = history_resp.get_json()
    assert len(rows) == 1
    assert rows[0]['status'] == 'success'
