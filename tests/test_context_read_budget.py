import pytest

from harness.repo_context import RepoContext
from test_repository_workflow import repository_profile


def test_model_latency_does_not_consume_or_reset_tool_time(tmp_path, monkeypatch):
    moment = [0.0]
    monkeypatch.setattr('harness.repo_context.time.monotonic', lambda: moment[0])
    (tmp_path / 'source.txt').write_text('Synthetic source', encoding='utf-8')
    policy = repository_profile()
    policy.repository_policy.timeout_seconds = 1
    def read_complete(result):
        moment[0] += 0.4
    context = RepoContext(tmp_path, policy, on_result=read_complete)
    request = {'op': 'read_file', 'path': 'source.txt'}
    assert context.request(request)['content'] == 'Synthetic source'
    moment[0] += 100  # LLM latency, with no context operation.
    assert context.request(request)['content'] == 'Synthetic source'
    assert context.elapsed_seconds == pytest.approx(0.8)
    with pytest.raises(ValueError, match='tiempo'):
        context.request(request)
    assert context.elapsed_seconds == pytest.approx(1.2)
    with pytest.raises(ValueError, match='tiempo'):
        context.request(request)
    assert context.reads == 3


def test_each_successful_uncached_read_emits_one_observation(tmp_path):
    (tmp_path / 'source.txt').write_text('Synthetic source', encoding='utf-8')
    observations = []
    context = RepoContext(tmp_path, repository_profile(), on_result=observations.append)
    context.request({'op': 'read_file', 'path': 'source.txt'})
    assert len(observations) == 1
