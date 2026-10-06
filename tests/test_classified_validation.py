from types import SimpleNamespace

import pytest
from harness.contracts import ClientProfile
from harness.sandbox import verify_general_patch


def profile(extension, adapter):
    return ClientProfile(repository='example/client', base_branch='develop', allowed_paths=['src/'],
        openspec_root='openspec', general_patch={'allowed_paths': ['src/'], 'extensions': [extension],
        'operations': ['modify'], 'max_files': 2, 'max_bytes': 10000,
        'test_adapters': [adapter, 'pytest_sandbox'], 'test_paths': ['tests']})


@pytest.mark.parametrize('extension,adapter,content', [
    ('.py', 'python_compile', 'def broken(:'),
    ('.sql', 'sql_lint', 'SELECT * FROM'),
    ('.yaml', 'yaml_validate', 'value: [unterminated'),
])
def test_parser_failure_is_authorized_implementation(tmp_path, extension, adapter, content):
    (tmp_path / 'src').mkdir()
    path = 'src/value' + extension
    (tmp_path / path).write_text(content, encoding='utf-8')
    result = verify_general_patch(tmp_path, profile(extension, adapter), [path], None,
        run_id='a' * 32, attempt_id='b' * 32, revision=1)
    assert result['passed'] is False
    assert result['findings'][0]['category'] == 'implementation'
    assert result['findings'][0]['paths'] == [path]


@pytest.mark.parametrize('failure_category,expected', [('implementation', 'implementation'),
    ('infrastructure_evidence', 'infrastructure_evidence'), (None, None)])
def test_runner_evidence_controls_classification(tmp_path, failure_category, expected):
    (tmp_path / 'src').mkdir()
    (tmp_path / 'src/value.py').write_text('VALUE = 2\n', encoding='utf-8')
    runner = SimpleNamespace(run=lambda *args, **kwargs: {'passed': False,
        'failure_category': failure_category, 'failure_code': 'pytest_failed', 'evidence': ['test failed']})
    result = verify_general_patch(tmp_path, profile('.py', 'python_compile'), ['src/value.py'], runner,
        run_id='a' * 32, attempt_id='b' * 32, revision=1)
    assert [item['category'] for item in result['findings']] == ([expected] if expected else [])


def test_runner_timeout_does_not_trigger_code_repair(tmp_path):
    (tmp_path / 'src').mkdir()
    (tmp_path / 'src/value.py').write_text('VALUE = 2\n', encoding='utf-8')
    def unavailable(*args, **kwargs):
        raise TimeoutError('No Job result')
    result = verify_general_patch(tmp_path, profile('.py', 'python_compile'), ['src/value.py'],
        SimpleNamespace(run=unavailable), run_id='a' * 32, attempt_id='b' * 32, revision=1)
    assert result['findings'][0]['category'] == 'infrastructure_evidence'
