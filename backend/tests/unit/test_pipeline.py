from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from sqlalchemy import create_engine, text

from app.agents.executor import ExecutorAgent, ExecutionResult, ExecutionMetrics
from app.agents.orchestrator import _serialize_rows, run_query
from app.agents.self_correction import CorrectionAgent


def make_agent(name, fail=False):
    linker = Mock()
    linker.link_schema.return_value = {'schema_dict': {name: {'columns': {'id': {'type': 'integer'}}}}, 'tables': [name]}
    generator = Mock()
    generator.generate.return_value = f'SELECT id FROM {name}'
    generator.generate_with_correction.return_value = f'SELECT id FROM {name} LIMIT 5'
    critic = Mock()
    critic.validate.return_value = SimpleNamespace(is_valid=True, confidence=1.0, issues=[])
    executor = Mock()
    executor.execute.return_value = ExecutionResult(
        success=not fail, data=[(name,)] if not fail else None,
        columns=['id'], sql_executed=f'SELECT id FROM {name} LIMIT 1000',
        row_count=0 if fail else 1, error_type='syntax_error' if fail else None,
        error_message='syntax error' if fail else None,
    )
    return CorrectionAgent(linker, generator, critic, executor)


def test_graphs_keep_their_own_schema_agents():
    first = make_agent('products')
    second = make_agent('books')
    # Construct both graphs before invoking either: the former globals mixed them up.
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda agent: agent.execute_with_retry('List items'), [first, second]))
    assert results[0].schema_tables_used == ['products']
    assert results[1].schema_tables_used == ['books']
    assert 'products' in results[0].final_sql
    assert 'books' in results[1].final_sql


def test_runtime_retry_budget_does_not_mutate_cached_default():
    agent = make_agent('products', fail=True)
    result = agent.execute_with_retry('List items', max_attempts=1)
    assert result.attempts == 1
    assert result.success is False
    assert agent.max_attempts == 3
    assert agent.executor.execute.call_count == 1


@pytest.mark.parametrize('attempts', [0, 6, True, '3'])
def test_invalid_retry_budget_rejected(attempts):
    with pytest.raises(ValueError):
        make_agent('products').execute_with_retry('List items', max_attempts=attempts)


def test_sqlalchemy_result_names_survive_serialization():
    engine = create_engine('sqlite://')
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT 'Studio' AS product, 3 AS quantity")).fetchall()
    assert _serialize_rows(rows) == [{'product': 'Studio', 'quantity': 3}]
    assert _serialize_rows([(1, 2)]) == [[1, 2]]
    assert _serialize_rows(None) is None


def test_executor_enforces_read_only_and_preserves_empty_result_columns():
    executor = ExecutorAgent.__new__(ExecutorAgent)
    executor.engine = Mock()
    executor.metrics = ExecutionMetrics()
    executor.classifier = Mock()
    connection = executor.engine.connect.return_value.__enter__ = Mock()
    executor.engine.connect.return_value.__exit__ = Mock(return_value=False)
    conn = connection.return_value
    result = conn.execute.return_value
    result.fetchmany.return_value = []
    result.keys.return_value = ['product']
    response = executor.execute('SELECT product FROM products')
    commands = [str(call.args[0]) for call in conn.execute.call_args_list]
    assert commands[0] == 'SET TRANSACTION READ ONLY'
    assert commands[1].startswith('SET LOCAL statement_timeout')
    assert commands[2].startswith('SELECT product FROM products')
    assert response.success is True
    assert response.columns == ['product']
    assert response.row_count == 0


def test_orchestrator_returns_executed_sql_and_passes_retry_budget(monkeypatch):
    from app.agents import orchestrator
    agent = make_agent('products')
    monkeypatch.setattr(orchestrator, '_get_agent', lambda schema: agent)
    result = run_query('List products', max_attempts=1)
    assert result['sql'] == 'SELECT id FROM products LIMIT 1000'
    assert result['columns'] == ['id']
    assert result['row_count'] == 1
