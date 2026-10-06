import hashlib

from harness.contracts import StoryRequest
from test_conversation import make_engine


def test_artifact_revisions_keep_immutable_versions_and_latest_reference(tmp_path):
    engine, _, _, store, _, _ = make_engine(tmp_path)
    run_id = engine.submit(StoryRequest(hu='HU-history', description='Synthetic artifact history'), actor='ana@example.com')
    record = store.load(run_id)
    attempt = record['attempts'][-1]
    path = 'openspec/changes/synthetic/specs/bronze-ingestion/spec.md'
    before, after = 'Old requirement\n', 'Updated requirement\n'
    engine._save_artifact(record, attempt, path, before, hashlib.sha256(before.encode()).hexdigest())
    old_ref = dict(attempt['openspec']['artifacts'][path])
    attempt['revision'] += 1
    engine._save_artifact(record, attempt, path, after, hashlib.sha256(after.encode()).hexdigest())
    current_ref = attempt['openspec']['artifacts'][path]
    assert old_ref['artifact_id'] != current_ref['artifact_id']
    assert store.load_openspec_artifact(run_id, attempt['attempt_id'], old_ref['artifact_id'])['content'] == before
    assert store.load_openspec_artifact(run_id, attempt['attempt_id'], current_ref['artifact_id'])['content'] == after
    assert len(attempt['openspec']['artifact_history'][path]) == 2
    engine._save_artifact(record, attempt, path, after, hashlib.sha256(after.encode()).hexdigest())
    assert len(attempt['openspec']['artifact_history'][path]) == 2
    assert store.load(run_id)['attempts'][-1]['openspec']['artifacts'][path] == current_ref
