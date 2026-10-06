"""Contracts delivered to the model and rejections before candidate writes."""
import copy
import hashlib
import json
from decimal import Decimal

import pytest

from harness import prompt_contracts
from harness.contracts import ContextPolicy, GeneralPatchPolicy
from harness.context_manager import ContextBudgetError
from harness.models import ModelClient
from harness.patch import FileOperation, ManifestCoverage
from harness.repo_context import ContextResponseError, RepoContext, contextual_answer
from test_context_manager import setup_manager
from test_context_request_contract import Replies
from test_classified_corrections import RepairModels, prepare, approve, finding


def environment(tmp_path):
    snapshots = []
    manager, profile = setup_manager(tmp_path, on_snapshot=lambda data: snapshots.append(copy.deepcopy(data)) or 'a' * 64)
    profile = profile.model_copy(update={'allowed_paths': ['src/'], 'general_patch': GeneralPatchPolicy(
        allowed_paths=['src/'], extensions=['.py'], operations=['create', 'modify', 'delete'],
        max_files=3, max_bytes=10000, test_adapters=['python_compile'], test_paths=['tests'])})
    manager.profile = profile
    (tmp_path / 'src').mkdir()
    (tmp_path / 'src/value.py').write_bytes(b'VALUE = 1\n')
    return manager, profile, snapshots


def canonical():
    return {'operations': [{'op': 'modify', 'path': 'src/value.py', 'content': 'VALUE = 2\n',
                           'expected_sha256': hashlib.sha256(b'VALUE = 1\n').hexdigest()}],
            'coverage': [{'path': 'src/value.py', 'status': 'applied'}], 'notes': 'synthetic'}


def client(values, **kwargs):
    return ModelClient(Replies(values), {'developer': 'sonnet'},
                       {'sonnet': (Decimal('.1'), Decimal('.2'))}, **kwargs)


def test_descriptor_examples_match_editor_and_profile(tmp_path):
    _, profile, _ = environment(tmp_path)
    assert hasattr(prompt_contracts, 'developer_output_contract')
    descriptor = prompt_contracts.developer_output_contract(profile, {'workflow_version': 'classified-corrections-v1'})
    assert descriptor['operation_schema']['properties'] == FileOperation.model_json_schema()['properties']
    assert descriptor['coverage_schema'] == ManifestCoverage.model_json_schema()
    assert descriptor['limits']['max_files'] == 3
    assert descriptor['limits']['max_bytes'] == 10000
    assert {v['op'] for v in descriptor['examples']} == {'create', 'modify', 'delete'}
    for example in descriptor['examples']:
        FileOperation.model_validate(example)
    restricted = profile.model_copy(update={'general_patch': profile.general_patch.model_copy(update={'operations': ['modify']})})
    assert [v['op'] for v in prompt_contracts.developer_output_contract(restricted, {})['examples']] == ['modify']


@pytest.mark.parametrize('managed', [False, True])
@pytest.mark.parametrize('stage', ['applying', 'correcting'])
def test_effective_payload_keeps_contract_after_read(tmp_path, managed, stage):
    manager, profile, snapshots = environment(tmp_path)
    context = RepoContext(tmp_path, profile)
    model = client([{'context_request': {'op': 'read_file', 'path': 'src/value.py'}}, canonical()])
    payload = {'task': 'Corregir o aplicar tareas aprobadas', 'workflow_version': 'classified-corrections-v1',
               'developer_output_contract': {'injected': True},
               'approved_manifest': [{'op': 'modify', 'path': 'src/value.py'}]}
    contextual_answer(model, 'developer', payload, context, phase='apply', stage=stage,
                      profile=profile, context_manager=manager if managed else None)
    for body in model.api.bodies:
        actual = json.loads(body['messages'][1]['content'])
        assert 'developer_output_contract' in actual
        descriptor = actual['developer_output_contract']
        assert 'injected' not in descriptor
        assert 'expected_sha256' in descriptor['operation_schema']['properties']
        assert 'base_sha256' in json.dumps(descriptor)
        assert 'coverage_schema' in descriptor
    assert len(model.calls) == 2
    assert (tmp_path / 'src/value.py').read_bytes() == b'VALUE = 1\n'
    if managed:
        assert all('developer_output_contract' in snap['payload'] for snap in snapshots)


@pytest.mark.parametrize('managed', [False, True])
def test_alias_rejected_precisely_and_accounted_without_repair(tmp_path, managed):
    manager, profile, _ = environment(tmp_path)
    value = canonical()
    value['operations'][0]['base_sha256'] = value['operations'][0].pop('expected_sha256')
    saved = []
    model = client([value], on_call=lambda role, response: saved.append(response))
    with pytest.raises(ContextResponseError) as caught:
        contextual_answer(model, 'developer', {'workflow_version': 'classified-corrections-v1'}, phase='apply',
                          profile=profile, context_manager=manager if managed else None)
    message = str(caught.value)
    assert all(s in message for s in ['operations[0]', 'base_sha256', 'expected_sha256'])
    assert caught.value.category == 'invalid_contract'
    assert len(model.api.bodies) == 1 and model.calls[-1].acceptance == 'invalid_contract'
    assert saved[-1].acceptance == 'invalid_contract'
    assert json.loads(saved[-1].text) == value
    assert saved[-1].input_tokens == 10 and saved[-1].output_tokens == 20
    assert saved[-1].cost_usd == Decimal('5')
    assert (tmp_path / 'src/value.py').read_bytes() == b'VALUE = 1\n'


@pytest.mark.parametrize('operation', [
    {'op': 'modify', 'path': 'src/value.py', 'content': 'SECRET'},
    {'op': 'delete', 'path': 'src/value.py', 'content': 'SECRET', 'expected_sha256': 'a' * 64},
    {'op': 'create', 'path': 'src/new.py', 'content': 17},
    {'op': 'modify', 'path': 'src/value.py', 'content': 'SECRET', 'expected_sha256': 'SECRET'},
    {'op': 'modify', 'path': 'src/value.py', 'content': 'SECRET', 'expected_sha256': 'a' * 64, 'SECRET\nkey': 'SECRET'},
    {'op': [], 'path': 'src/value.py', 'content': 'SECRET'},
    {'op': {}, 'path': 'src/value.py', 'content': 'SECRET'},
])
def test_shape_diagnostics_never_echo_arbitrary_input(tmp_path, operation):
    _, profile, _ = environment(tmp_path)
    with pytest.raises(ValueError) as caught:
        prompt_contracts.validate_output('developer', {'operations': [operation]}, {}, profile)
    assert 'operations[0]' in str(caught.value)
    assert 'SECRET' not in str(caught.value) and 'src/value.py' not in str(caught.value)
    assert len(str(caught.value)) <= 600


def test_historical_and_ratio_descriptors_do_not_require_coverage(tmp_path):
    _, profile, _ = environment(tmp_path)
    assert hasattr(prompt_contracts, 'developer_output_contract')
    historical = prompt_contracts.developer_output_contract(profile, {})
    assert 'coverage_schema' not in historical
    ratio = prompt_contracts.developer_output_contract(profile.model_copy(update={'general_patch': None}), {})
    assert set(ratio['fields']) == {'expression', 'notes'} and 'operation_schema' not in ratio


@pytest.mark.parametrize('managed', [False, True])
def test_policy_denial_keeps_plain_value_error(tmp_path, managed):
    manager, profile, _ = environment(tmp_path)
    value = canonical()
    value['operations'][0]['path'] = 'denied/value.py'
    with pytest.raises(ValueError) as caught:
        contextual_answer(client([value]), 'developer', {}, profile=profile, phase='apply',
                          context_manager=manager if managed else None)
    assert not isinstance(caught.value, ContextResponseError)
    assert 'fuera del perfil' in str(caught.value)


@pytest.mark.parametrize('managed', [False, True])
def test_file_count_denial_keeps_policy_error(tmp_path, managed):
    manager, profile, _ = environment(tmp_path)
    value = canonical()
    value['operations'] *= 4
    with pytest.raises(ValueError) as caught:
        contextual_answer(client([value]), 'developer', {}, profile=profile, phase='apply',
                          context_manager=manager if managed else None)
    assert not isinstance(caught.value, ContextResponseError)
    assert 'Límite de operaciones' in str(caught.value)


def test_contract_overhead_is_bounded_and_not_truncated(tmp_path):
    manager, profile, snapshots = environment(tmp_path)
    model = client([canonical()])
    contextual_answer(model, 'developer', {}, profile=profile, phase='apply', context_manager=manager)
    descriptor_bytes = len(json.dumps(snapshots[-1]['payload']['developer_output_contract']).encode())
    assert 0 < descriptor_bytes < 12000
    manager.policy = ContextPolicy(enabled=True, max_prompt_bytes=2048)
    with pytest.raises(ContextBudgetError):
        contextual_answer(client([canonical()]), 'developer', {'task': 'x' * 3000},
                          profile=profile, phase='apply', context_manager=manager)


@pytest.mark.parametrize('managed', [False, True])
def test_rejection_storage_failure_is_not_swallowed(tmp_path, managed):
    manager, profile, _ = environment(tmp_path)
    value = canonical()
    value['operations'][0]['base_sha256'] = value['operations'][0].pop('expected_sha256')
    def persist(role, response):
        if response.acceptance == 'invalid_contract':
            raise RuntimeError('synthetic storage unavailable')
    model = client([value], on_call=persist)
    with pytest.raises(RuntimeError, match='storage unavailable'):
        contextual_answer(model, 'developer', {}, profile=profile, phase='apply',
                          context_manager=manager if managed else None)
    assert len(model.calls) == 1
    assert (tmp_path / 'src/value.py').read_bytes() == b'VALUE = 1\n'


@pytest.mark.parametrize('managed', [False, True])
@pytest.mark.parametrize('bad_op', [[], {}])
def test_invalid_operation_type_marks_rejection(tmp_path, managed, bad_op):
    manager, profile, _ = environment(tmp_path)
    value = canonical()
    value['operations'][0]['op'] = bad_op
    model = client([value])
    with pytest.raises(ContextResponseError, match=r'operations\[0\]'):
        contextual_answer(model, 'developer', {}, profile=profile, phase='apply',
                          context_manager=manager if managed else None)
    assert model.calls[-1].acceptance == 'invalid_contract'


@pytest.mark.parametrize('operation', [
    {'op': 'create', 'path': 'src/new.py', 'content': '', 'expected_sha256': None},
    {'op': 'delete', 'path': 'src/value.py', 'content': None, 'expected_sha256': 'a' * 64},
])
def test_null_compatibility_keeps_valid_shapes(tmp_path, operation):
    _, profile, _ = environment(tmp_path)
    prompt_contracts.validate_output('developer', {'operations': [operation]}, {}, profile)


@pytest.mark.parametrize('managed', [False, True])
def test_real_checkpoint_alias_retry_and_correction(tmp_path, managed):
    class Incident(RepairModels):
        bad = True
        def complete(self, role, prompt, **kwargs):
            response = super().complete(role, prompt, **kwargs)
            if role == 'developer' and self.bad:
                value = json.loads(response.text)
                value['operations'][0]['base_sha256'] = value['operations'][0].pop('expected_sha256')
                response.text = json.dumps(value)
            return response
    models = Incident(semantic=[[finding()]])
    prepared = prepare(tmp_path, models, managed=managed)
    engine, github, _, store, _, _, run_id, plan = prepared
    verified_values = []
    def runner(root, profile, paths, record, attempt):
        namespace = {}
        exec(compile((root / 'src/value.py').read_bytes(), 'synthetic_value.py', 'exec'), namespace)
        verified_values.append(namespace['VALUE'])
        return {'passed': namespace['VALUE'] == len(verified_values) + 2,
                'evidence': ['Compiled and evaluated synthetic candidate VALUE']}
    engine.test_runner = runner
    approve(prepared)
    failed = store.load(run_id)['attempts'][-1]
    assert failed['failure']['retryable'] is True
    assert failed['failure']['failed_stage'] == 'applying'
    assert github.published == [] and failed['context']['candidate_revision'] == 0
    models.bad = False
    engine.retry(run_id, actor='ana@example.com', expected_revision=failed['revision'],
                 failure_id=failed['failure']['id'])
    engine.advance(run_id)
    final = store.load(run_id)['attempts'][-1]
    assert final['stage'] == 'complete' and len(github.published) == 1
    assert final['context']['implementation_correction_count'] == 1
    assert verified_values == [3, 4]
    assert all('developer_output_contract' in payload for role, payload, _ in models.prompts if role == 'developer')
