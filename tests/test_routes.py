from unittest.mock import patch


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
