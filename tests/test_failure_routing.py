import pytest

from harness.failure_routing import Finding, failure_route, progress_key


def finding(category='implementation', **kwargs):
    return {'category': category, 'code': 'wrong_result', 'criterion': 'Salida',
            'evidence': 'test_output: expected 2, got 1', 'paths': ['src/value.py'],
            'operations': [], 'recommendation': 'Corregir salida', **kwargs}


def test_scoped_implementation_can_correct():
    assert failure_route([finding()], [{'op': 'modify', 'path': 'src/value.py'}]) == 'correcting'


def test_one_repair_can_modify_a_base_file_and_a_created_test():
    assert failure_route([finding(paths=['src/value.py', 'tests/new.py'], operations=['modify'])],
        [{'op': 'modify', 'path': 'src/value.py'}, {'op': 'create', 'path': 'tests/new.py'}]) == 'correcting'


def test_unknown_scope_cannot_correct():
    assert failure_route([finding(paths=['src/other.py'])], [{'op': 'modify', 'path': 'src/value.py'}]) == 'updating'


def test_mixed_findings_need_replan():
    assert failure_route([finding(), finding('scope_spec')], [{'op': 'modify', 'path': 'src/value.py'}]) == 'updating'


@pytest.mark.parametrize('category', ['harness_defect', 'infrastructure_evidence'])
def test_non_candidate_failure_does_not_replan(category):
    assert failure_route([finding(category)], []) == 'failed'


def test_invalid_or_informational_rejection_cannot_repair():
    with pytest.raises(ValueError):
        Finding.model_validate(finding('other'))
    with pytest.raises(ValueError):
        failure_route([], [])


def test_prose_does_not_make_progress():
    assert progress_key([finding()], 'candidate', [{'op': 'modify', 'path': 'src/value.py'}]) == progress_key(
        [finding(recommendation='Otra redacción', evidence='el mismo test')], 'candidate', [{'op': 'modify', 'path': 'src/value.py'}])
    assert progress_key([finding()], 'candidate', []) != progress_key([finding()], 'corrected', [])


def test_unrelated_scope_and_criterion_prose_do_not_clear_blocker():
    manifest = [{'op': 'modify', 'path': 'src/value.py'}]
    assert progress_key([finding()], 'candidate', manifest) == progress_key(
        [finding(criterion='Salida redactada de otra forma')], 'candidate',
        manifest + [{'op': 'create', 'path': 'src/unrelated.py'}])


@pytest.mark.parametrize('value', [{'approved': True, 'findings': [finding()]},
                                 {'approved': False, 'findings': []}])
def test_semantic_verification_must_have_consistent_blocking_findings(value):
    from harness.prompt_contracts import validate_output
    from test_general_patch import profile
    with pytest.raises(ValueError, match='contradictorios'):
        validate_output('openspec_verifier', value, {'workflow_version': 'classified-corrections-v1'}, profile())


def test_unknown_workflow_version_cannot_resume_as_historical():
    from pathlib import Path
    from harness.conversation import ConversationEngine
    from harness.failure_routing import WorkflowFailure
    engine = object.__new__(ConversationEngine)
    engine._require_profile = lambda record: None
    with pytest.raises(WorkflowFailure, match='incompatible'):
        engine._step(Path('.'), {'story': {'hu': 'HU', 'description': 'Synthetic'}},
                     {'stage': 'correcting', 'context': {'workflow_version': 'future-contract'}}, None, None, None)


def test_inconclusive_test_result_remains_readable_in_progress():
    from harness.progress import checklist
    attempt = {'revision': 1, 'stage': 'failed', 'context': {'code_candidate_hash': 'candidate', 'tests': None},
               'failure': {'failed_stage': 'verifying'}, 'timeline': []}
    assert next(row for row in checklist(attempt) if row['phase'] == 'verify')['status'] == 'failed'
