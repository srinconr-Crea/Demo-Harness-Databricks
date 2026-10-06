import json

import pytest

from harness.prompt_contracts import validate_artifact_content, validate_planner_manifest


@pytest.mark.parametrize('artifact,template,content', [
    ('proposal', '## Why\n## Impact', '## Why\nMotivo suficiente.\n## Impact\nCódigo.'),
    ('design', '## Context\n## Decisions', '## Context\r\nContexto.\r\n## Decisions\r\nDecisión.'),
    ('tasks', '# Tasks', '# Tasks\n\n- [ ] 1.1 Probar salida.'),
    ('specs', '## ADDED Requirements', '## MODIFIED Requirements\n\n### Requirement: Salida\nSHALL funcionar.\n#### Scenario: Caso\n- **WHEN** entrada\n- **THEN** salida'),
])
def test_content_preserved_and_double_serialization_rejected(artifact, template, content):
    payload = {'artifact': artifact, 'template': template}
    validate_artifact_content(content, payload)
    with pytest.raises(ValueError, match='serializaci|estructura'):
        validate_artifact_content(content.replace('\r\n', '\n').replace('\n', '\\n'), payload)


def test_examples_do_not_supply_missing_document_headings():
    with pytest.raises(ValueError, match='estructura'):
        validate_artifact_content('```markdown\n## Why\n## Impact\n```',
                                  {'artifact': 'proposal', 'template': '## Why\n## Impact'})


@pytest.mark.parametrize('content,payload', [
    ('```markdown\n```python\n## Why\nEjemplo.\n## Impact\nEjemplo.\n```',
     {'artifact': 'proposal', 'template': '## Why\n## Impact'}),
    ('    - [ ] 1.1 Ejemplo indentado\n    sigue dentro del bloque de código',
     {'artifact': 'tasks', 'template': '# Tasks'}),
])
def test_code_blocks_cannot_supply_document_structure(content, payload):
    with pytest.raises(ValueError, match='estructura'):
        validate_artifact_content(content, payload)


def test_legitimate_literals_are_unchanged():
    content = '## Why\nAcentos: Bogotá.\n```python\nprint("\\n", "\\\\", "á")\n```\n## Impact\nPruebas.'
    validate_artifact_content(content, {'artifact': 'proposal', 'template': '## Why\n## Impact'})
    assert json.loads(json.dumps({'content': content}))['content'] == content


def test_manifest_openspec_entry_is_rejected_without_filtering(tmp_path):
    from test_conversation import make_engine
    engine, *_ = make_engine(tmp_path)
    manifest = [{'op': 'modify', 'path': 'src/value.py'},
                {'op': 'modify', 'path': 'openspec/changes/demo/specs/demo/spec.md'}]
    with pytest.raises(ValueError, match='entrada 2.*OpenSpec'):
        validate_planner_manifest(manifest, engine.profile)
    assert len(manifest) == 2


@pytest.mark.parametrize('item', [
    {'op': 'shell', 'path': 'src/value.py'}, {'op': 'modify', 'path': '../private/key.py'},
    {'op': 'modify', 'path': 'src/value.exe'}, {'op': 'modify', 'path': '.agents/key.py'},
])
def test_manifest_policy_rejections_do_not_echo_untrusted_paths(tmp_path, item):
    from test_conversation import make_engine
    engine, *_ = make_engine(tmp_path)
    with pytest.raises(ValueError) as error:
        validate_planner_manifest([item], engine.profile)
    assert item['path'] not in str(error.value)


def test_manifest_duplicate_and_invalid_fields(tmp_path):
    from test_conversation import make_engine
    engine, *_ = make_engine(tmp_path)
    item = {'op': 'modify', 'path': 'src/value.py'}
    assert validate_planner_manifest([item], engine.profile) == {'src/value.py'}
    with pytest.raises(ValueError, match='duplicada'):
        validate_planner_manifest([item, item], engine.profile)
    with pytest.raises(ValueError, match='campos'):
        validate_planner_manifest([{'op': 'modify', 'path': 1}], engine.profile)


def test_prompt_fields_and_serialization_example(tmp_path):
    from harness.prompt_contracts import planner_artifact_output, PromptContracts
    from test_conversation import make_engine
    engine, *_ = make_engine(tmp_path)
    assert set(planner_artifact_output('proposal', engine.profile)) == {'content', 'summary', 'manifest'}
    for artifact in ('specs', 'design', 'tasks'):
        assert set(planner_artifact_output(artifact, engine.profile)) == {'content'}
    prompt, provenance = PromptContracts().compose('planner', 'propose')
    assert 'Nunca incluyas rutas OpenSpec' in prompt and 'una sola vez' in prompt
    assert provenance['version'] == 'role-contracts-v5'


@pytest.mark.parametrize('enabled', [False, True])
def test_invalid_markdown_preserves_partial_checkpoint_without_extra_calls(tmp_path, enabled):
    from harness.contracts import ContextPolicy, StoryRequest
    from test_conversation import make_engine
    engine, github, models, store, _, _ = make_engine(tmp_path)
    engine.context_policy = ContextPolicy(enabled=enabled)
    run_id = engine.submit(StoryRequest(hu='HU-artifact', description='Salida nueva'), actor='ana')
    engine.advance(run_id)
    original = models.complete
    planner_calls = []
    def malformed(role, prompt, **kwargs):
        response = original(role, prompt, **kwargs)
        if role == 'planner':
            payload = json.loads(prompt)
            artifact = payload['artifact']
            assert isinstance(payload['serialization_example'], dict)
            assert '\n' in payload['serialization_example']['content']
            assert '\\n' not in payload['serialization_example']['content']
            planner_calls.append(artifact)
            if artifact == 'specs':
                value = json.loads(response.text)
                value['content'] = value['content'].replace('\n', '\\n')
                response.text = json.dumps(value)
        return response
    models.complete = malformed
    engine.act(run_id, 'answer', actor='ana', text='Salida 2', expected_revision=0, key='answer')
    record = engine.get(run_id)
    attempt = record['attempts'][-1]
    assert record['state'] == 'failed' and attempt['failure']['category'] == 'invalid_contract'
    checkpoint = store.load_checkpoint(run_id, attempt['attempt_id'], attempt['checkpoint_id'])
    assert any(path.endswith('proposal.md') for path in checkpoint['files'])
    assert not any('/specs/' in path for path in checkpoint['files'])
    assert planner_calls == ['proposal', 'specs'] and not github.published
