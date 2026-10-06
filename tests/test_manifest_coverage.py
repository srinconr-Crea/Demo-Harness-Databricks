import hashlib
import subprocess

import pytest

from harness import patch
from harness.contracts import ClientProfile


def sha(value):
    return hashlib.sha256(value).hexdigest()


def profile(max_bytes=1000, max_files=3):
    return ClientProfile(repository='example/client', base_branch='develop',
                         allowed_paths=['src/'], openspec_root='openspec',
                         general_patch={'allowed_paths': ['src/'], 'extensions': ['.py'],
                                        'operations': ['create', 'modify', 'delete'],
                                        'max_files': max_files, 'max_bytes': max_bytes,
                                        'test_adapters': ['python_compile']})


@pytest.fixture
def repo(tmp_path):
    def git(*args):
        return subprocess.run(['git', *args], cwd=tmp_path, capture_output=True,
                              check=True).stdout.decode().strip()
    git('init')
    git('config', 'user.name', 'Synthetic test')
    git('config', 'user.email', 'test@example.invalid')
    git('config', 'core.autocrlf', 'false')
    (tmp_path / 'src').mkdir()
    (tmp_path / 'src/a.py').write_bytes(b'old\n')
    (tmp_path / 'src/b.py').write_bytes(b'base\n')
    git('add', '.')
    git('commit', '-m', 'Synthetic base')
    return tmp_path, git('rev-parse', 'HEAD')


def validate(repo, manifest, operations, coverage, policy=None):
    validator = getattr(patch, 'validate_manifest_coverage', None)
    assert validator is not None, 'Missing cumulative coverage validator'
    return validator(repo[0], policy or profile(), repo[1], manifest, operations, coverage)


def conformant(path, content):
    return {'path': path, 'status': 'already_conformant', 'sha256': sha(content)}


def test_empty_operations_verify_current_coverage_without_writing(repo):
    root, _ = repo
    (root / 'src/a.py').write_bytes(b'new\n')
    assert validate(repo, [{'op': 'modify', 'path': 'src/a.py'}], [],
                    [conformant('src/a.py', b'new\n')]) == ['src/a.py']
    assert (root / 'src/a.py').read_bytes() == b'new\n'
    with pytest.raises(ValueError):
        patch.apply_file_operations(root, profile(), [])


@pytest.mark.parametrize('coverage', [[], [{'path': 'src/a.py', 'status': 'already_conformant'}],
    [conformant('src/a.py', b'stale')], [{'path': 'src/a.py', 'status': 'blocked', 'reason': 'Missing evidence'}]])
def test_incomplete_or_stale_coverage_does_not_confer_conformity(repo, coverage):
    with pytest.raises(ValueError):
        validate(repo, [{'op': 'modify', 'path': 'src/a.py'}], [], coverage)
    assert (repo[0] / 'src/a.py').read_bytes() == b'old\n'


def test_partial_repair_preserves_other_cumulative_component(repo):
    root, _ = repo
    (root / 'src/a.py').write_bytes(b'new\n')
    (root / 'src/b.py').write_bytes(b'changed\n')
    operations = [patch.FileOperation(op='modify', path='src/a.py', content='fixed\n', expected_sha256=sha(b'new\n'))]
    assert validate(repo, [{'op': 'modify', 'path': 'src/a.py'}, {'op': 'modify', 'path': 'src/b.py'}], operations,
                    [{'path': 'src/a.py', 'status': 'applied'}, conformant('src/b.py', b'changed\n')]) == ['src/a.py', 'src/b.py']
    assert (root / 'src/a.py').read_bytes() == b'new\n'
    patch.apply_file_operations(root, profile(), operations)
    assert (root / 'src/a.py').read_bytes() == b'fixed\n'


def test_created_file_can_be_modified_under_base_creation_manifest(repo):
    root, _ = repo
    (root / 'src/test.py').write_bytes(b'assert False\n')
    operation = patch.FileOperation(op='modify', path='src/test.py', content='assert True\n', expected_sha256=sha(b'assert False\n'))
    assert validate(repo, [{'op': 'create', 'path': 'src/test.py'}], [operation],
                    [{'path': 'src/test.py', 'status': 'applied'}]) == ['src/test.py']


def test_deletion_cannot_expand_modify_authorization_atomically(repo):
    root, _ = repo
    operations = [patch.FileOperation(op='modify', path='src/a.py', content='new\n', expected_sha256=sha(b'old\n')),
                  patch.FileOperation(op='delete', path='src/b.py', expected_sha256=sha(b'base\n'))]
    with pytest.raises(ValueError):
        validate(repo, [{'op': 'modify', 'path': 'src/a.py'}, {'op': 'modify', 'path': 'src/b.py'}], operations,
                 [{'path': 'src/a.py', 'status': 'applied'}, {'path': 'src/b.py', 'status': 'applied'}])
    assert (root / 'src/a.py').read_bytes() == b'old\n'
    assert (root / 'src/b.py').read_bytes() == b'base\n'


def test_already_deleted_file_requires_matching_base_hash(repo):
    (repo[0] / 'src/a.py').unlink()
    assert validate(repo, [{'op': 'delete', 'path': 'src/a.py'}], [],
                    [conformant('src/a.py', b'old\n')]) == ['src/a.py']
    with pytest.raises(ValueError):
        validate(repo, [{'op': 'delete', 'path': 'src/a.py'}], [], [conformant('src/a.py', b'')])


def test_missing_base_file_cannot_claim_completed_deletion(repo):
    with pytest.raises(ValueError):
        validate(repo, [{'op': 'delete', 'path': 'src/absent.py'}], [], [conformant('src/absent.py', b'')])


def test_cumulative_bytes_exceed_limit_even_when_repair_is_small(repo):
    root, _ = repo
    (root / 'src/b.py').write_bytes(b'large accumulated content\n')
    operations = [patch.FileOperation(op='modify', path='src/a.py', content='x', expected_sha256=sha(b'old\n'))]
    with pytest.raises(ValueError, match='bytes'):
        validate(repo, [{'op': 'modify', 'path': 'src/a.py'}, {'op': 'modify', 'path': 'src/b.py'}], operations,
                 [{'path': 'src/a.py', 'status': 'applied'}, conformant('src/b.py', b'large accumulated content\n')], profile(max_bytes=10))
    assert (root / 'src/a.py').read_bytes() == b'old\n'


def test_cumulative_unapproved_change_is_rejected(repo):
    (repo[0] / 'src/b.py').write_bytes(b'unapproved\n')
    with pytest.raises(ValueError):
        validate(repo, [{'op': 'modify', 'path': 'src/a.py'}], [], [conformant('src/a.py', b'old\n')])


@pytest.mark.parametrize('coverage', [
    [{'path': 'src/a.py', 'status': 'applied'}],
    [conformant('src/a.py', b'old\n'), conformant('src/a.py', b'old\n')],
    [conformant('src/a.py', b'old\n'), conformant('src/b.py', b'base\n')],
    [{'path': 'src/a.py', 'status': 'already_conformant', 'sha256': sha(b'old\n'), 'extra': True}],
])
def test_coverage_must_match_manifest_and_operation_status(repo, coverage):
    with pytest.raises(ValueError):
        validate(repo, [{'op': 'modify', 'path': 'src/a.py'}], [], coverage)


def test_operation_outside_manifest_is_rejected_before_writes(repo):
    operations = [patch.FileOperation(op='modify', path='src/b.py', content='new', expected_sha256=sha(b'base\n'))]
    with pytest.raises(ValueError):
        validate(repo, [{'op': 'modify', 'path': 'src/a.py'}], operations, [conformant('src/a.py', b'old\n')])
    assert (repo[0] / 'src/b.py').read_bytes() == b'base\n'


def test_deleted_bytes_are_counted_in_cumulative_size(repo):
    with pytest.raises(ValueError, match='bytes'):
        validate(repo, [{'op': 'delete', 'path': 'src/a.py'}],
                 [patch.FileOperation(op='delete', path='src/a.py', expected_sha256=sha(b'old\n'))],
                 [{'path': 'src/a.py', 'status': 'applied'}], profile(max_bytes=3))


def test_manifest_file_count_limit_applies_before_operations(repo):
    with pytest.raises(ValueError):
        validate(repo, [{'op': 'modify', 'path': 'src/a.py'}, {'op': 'modify', 'path': 'src/b.py'}], [],
                 [conformant('src/a.py', b'old\n'), conformant('src/b.py', b'base\n')], profile(max_files=1))


def test_conformant_coverage_rejects_non_utf8_bytes(repo):
    (repo[0] / 'src/a.py').write_bytes(b'\xff')
    with pytest.raises(ValueError, match='UTF-8'):
        validate(repo, [{'op': 'modify', 'path': 'src/a.py'}], [], [conformant('src/a.py', b'\xff')])


def test_invalid_parent_file_prevents_partial_batch_write(repo):
    root, _ = repo
    operations = [patch.FileOperation(op='modify', path='src/b.py', content='changed', expected_sha256=sha(b'base\n')),
                  patch.FileOperation(op='create', path='src/a.py/nested.py', content='new')]
    with pytest.raises(ValueError):
        patch.apply_file_operations(root, profile(), operations)
    assert (root / 'src/b.py').read_bytes() == b'base\n'


def test_overlapping_new_paths_prevent_partial_batch_write(repo):
    root, _ = repo
    operations = [patch.FileOperation(op='create', path='src/new.py', content='new'),
                  patch.FileOperation(op='create', path='src/new.py/nested.py', content='nested')]
    with pytest.raises(ValueError):
        patch.apply_file_operations(root, profile(), operations)
    assert not (root / 'src/new.py').exists()
