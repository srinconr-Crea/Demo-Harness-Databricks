"""Comparable synthetic fixtures; no endpoint calls, billing claims or client edits."""
import json
import sys
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src/agents/harness'))
from harness.context_manager import ContextBudgetError, ContextManager
from harness.contracts import ClientProfile, ContextPolicy
from harness.repo_context import RepoContext, contextual_answer
from harness.store import LocalRunStore


def measure(root):
    profile = ClientProfile(repository='example/synthetic', base_branch='develop', openspec_root='openspec')
    identity = {'run_id': 'a' * 32, 'attempt_id': 'b' * 32, 'repository': profile.repository,
                'profile_sha256': 'c' * 64, 'base_sha': 'd' * 40, 'revision': 0,
                'stage': 'exploring', 'checkpoint_id': None}
    (root / 'source.txt').write_text('evidence\n' * 1000, encoding='utf-8')
    messages = [{'kind': 'clarification', 'actor': 'human', 'text': 'Cero permitido en compras. Negativos rechazados.'}]
    results = []
    for enabled in (False, True):
        manager = ContextManager(root, profile, ContextPolicy(enabled=True), identity, messages) if enabled else None
        context = RepoContext(root, profile, cache=manager.cache if manager else None, identity=identity)
        class Model:
            def __init__(self):
                self.bytes = []
            def complete(self, role, prompt, **kwargs):
                self.bytes.append(len(prompt.encode('utf-8')) + len(kwargs.get('system_prompt', '').encode('utf-8')))
                value = ({'context_request': {'op': 'read_file', 'path': 'source.txt'}}
                         if len(self.bytes) <= 4 else {'summary': 'evidence', 'questions': []})
                return SimpleNamespace(text=json.dumps(value))
        model = Model()
        started = time.perf_counter()
        final = contextual_answer(model, 'explorer', {'hu': 'synthetic', 'clarifications': messages}, context,
                                  context_manager=manager, phase='explore')
        results.append({'enabled': enabled, 'calls': len(model.bytes), 'bytes_total': sum(model.bytes),
                        'bytes_per_call': model.bytes, 'latency_ms': round((time.perf_counter() - started) * 1000, 3),
                        'usage': None, 'cost_usd': None, 'final': final,
                        'cache': dict(manager.cache.metrics) if manager else None})
    store = LocalRunStore(root / 'records')
    for turn in range(40):
        if turn:
            messages.append({'kind': 'change', 'actor': 'human', 'revision': turn,
                             'text': f'Corrijo: cero {"permitido" if turn % 2 == 0 else "rechazado"} en compras ahora.'})
        manager = ContextManager(root, profile, ContextPolicy(enabled=True), {**identity, 'revision': turn}, messages)
        ref = store.save_context_snapshot(identity['run_id'], identity['attempt_id'], manager.memory_snapshot())
        restored = ContextManager(root, profile, manager.policy, manager.identity, messages,
                                 previous=store.load_context_snapshot(identity['run_id'], identity['attempt_id'], ref))
        payload, _, _ = restored.prepare('explorer', 'explore', {'hu': 'synthetic'}, [], None)
        assert len(json.loads(payload)['confirmed_decisions']) == 1
        assert len(restored.decisions) == turn + 1
    blocked = ContextManager(root, profile, ContextPolicy(enabled=True, max_prompt_bytes=1024), identity, messages)
    try:
        blocked.prepare('explorer', 'explore', {'source': 'x' * 1024}, [], None)
    except ContextBudgetError:
        budget_blocked = True
    else:
        raise AssertionError('Expected budget block')
    return {'comparison': results, 'stress': {'turns': 40, 'substitutions': 39, 'restorations': 40,
                                             'originals_preserved': True, 'budget_blocked': budget_blocked},
            'scope': 'local synthetic stub; latency includes deterministic work, no network or LLM usage'}


if __name__ == '__main__':
    with tempfile.TemporaryDirectory(prefix='hc-measure-') as directory:
        print(json.dumps(measure(Path(directory)), indent=2))
