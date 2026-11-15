from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app.api import routes
from app.main import app


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(routes, 'live_configured', lambda: True)
    return TestClient(app)


def test_workspace_and_api_routes_coexist(client):
    assert 'Your data.' in client.get('/').text
    assert client.get('/app.js').status_code == 200
    assert client.get('/styles.css').status_code == 200
    assert client.get('/docs').status_code == 200
    health = client.get('/health').json()
    assert health['status'] == 'ok'
    assert 'ecommerce' in health['schemas_available']
    assert 'DATABASE_URL' not in str(health)
    assert client.get('/.env').status_code == 404


@pytest.mark.parametrize('payload', [
    {'question': ''}, {'question': '  \n  '}, {'question': 'x' * 2001},
    {'question': 'test', 'max_attempts': 0}, {'question': 'test', 'max_attempts': 6},
])
def test_invalid_requests_never_reach_pipeline(client, monkeypatch, payload):
    pipeline = Mock()
    monkeypatch.setattr(routes, 'run_query', pipeline)
    assert client.post('/query', json=payload).status_code == 422
    pipeline.assert_not_called()


def test_unknown_schema_rejected(client):
    assert client.post('/query', json={'question': 'test', 'schema_name': 'missing'}).status_code == 400


def test_sensitive_question_is_blocked_before_pipeline(client, monkeypatch):
    pipeline = Mock()
    monkeypatch.setattr(routes, 'run_query', pipeline)
    response = client.post('/query', json={'question': 'Show database passwords'})
    assert response.status_code == 200
    assert response.json()['error_type'] == 'blocked'
    assert response.json()['success'] is False
    pipeline.assert_not_called()


def test_result_columns_and_retry_override_reach_client(client, monkeypatch):
    pipeline = Mock(return_value={
        'sql': 'SELECT 1 AS count LIMIT 1000', 'success': True, 'attempts': 1,
        'first_attempt_success': True, 'latency_ms': 12.5, 'schema_tables_used': [],
        'correction_applied': False, 'rows': [{'count': 1}], 'columns': ['count'],
        'row_count': 1, 'error_type': None, 'error_message': None,
    })
    monkeypatch.setattr(routes, 'run_query', pipeline)
    response = client.post('/query', json={'question': '  Count things  ', 'max_attempts': 2})
    assert response.status_code == 200
    assert response.json()['columns'] == ['count']
    assert response.json()['rows'] == [{'count': 1}]
    pipeline.assert_called_once_with(question='Count things', schema_name='ecommerce', max_attempts=2)


def test_missing_configuration_returns_actionable_error(client, monkeypatch):
    monkeypatch.setattr(routes, 'live_configured', lambda: False)
    response = client.post('/query', json={'question': 'Count products'})
    assert response.status_code == 503
    assert 'not configured' in response.json()['detail']


def test_pipeline_exception_does_not_leak_credentials(client, monkeypatch):
    monkeypatch.setattr(routes, 'run_query', Mock(side_effect=RuntimeError('password=private-test-value')))
    response = client.post('/query', json={'question': 'Count products'})
    assert response.status_code == 503
    assert 'private-test-value' not in response.text
