"""Deterministic per-attempt context; originals remain the only authorization source."""
import copy
import json
import re
import time
from collections import OrderedDict
from pathlib import Path

import yaml

from .contracts import ContextEnvelope, ContextPolicy, DecisionRecord, SelectionRecord
from .prompt_contracts import TOOLS, PromptContracts, context_contract, validate_output
from .skills import digest


def load_context_policy(path=None):
    path = path or Path(__file__).resolve().parents[1] / 'config/defaults/context.yaml'
    return ContextPolicy.model_validate(yaml.safe_load(Path(path).read_text(encoding='utf-8')))


class ContextBudgetError(ValueError):
    pass


class DecisionConflict(ValueError):
    pass


class SourceCache:
    def __init__(self, policy, clock=time.monotonic):
        self.policy, self.clock = policy, clock
        self.entries = OrderedDict()
        self.fingerprints = OrderedDict()
        self.bytes = 0
        self.metrics = {'hits': 0, 'misses': 0, 'invalidations': 0}

    def bind(self, logical, current):
        previous = self.fingerprints.pop(logical, None)
        if previous and previous != current:
            entry = self.entries.pop(previous, None)
            if entry:
                self.bytes -= entry[1]
            self.metrics['invalidations'] += 1
        self.fingerprints[logical] = current
        while len(self.fingerprints) > self.policy.cache_max_entries:
            self.fingerprints.popitem(last=False)

    def get(self, key):
        entry = self.entries.get(key)
        if entry:
            expires, size, checksum, value = entry
            if expires > self.clock() and digest(value) == checksum:
                self.entries.move_to_end(key)
                self.metrics['hits'] += 1
                return copy.deepcopy(value)
            self.entries.pop(key)
            self.bytes -= size
            self.metrics['invalidations'] += 1
        self.metrics['misses'] += 1
        return None

    def put(self, key, result):
        if result.get('truncated') or result.get('error') or result.get('reason'):
            return
        size = len(json.dumps(result, ensure_ascii=False).encode('utf-8'))
        if size > self.policy.cache_max_bytes:
            return
        if key in self.entries:
            self.bytes -= self.entries.pop(key)[1]
        while self.entries and (len(self.entries) >= self.policy.cache_max_entries
                                or self.bytes + size > self.policy.cache_max_bytes):
            self.bytes -= self.entries.popitem(last=False)[1][1]
        self.entries[key] = (self.clock() + self.policy.cache_ttl_seconds, size, digest(result), copy.deepcopy(result))
        self.bytes += size


# Only an explicit, narrowly recognizable rule is decomposed. Everything else stays intact.
def _rule(text):
    lower = text.casefold()
    if 'compras' not in lower or 'cero' not in lower:
        return None
    allowed = bool(re.search(r'cero\s+(?:está\s+|es\s+)?permitido', lower))
    rejected = bool(re.search(r'cero\s+(?:está\s+|es\s+)?rechazado|cero\s+(?:se\s+)?rechaza', lower))
    if allowed == rejected:
        return None
    return ('compras:cero', 'allowed' if allowed else 'rejected')


def rebuild_decisions(messages, identity, previous=()):
    records = []
    for index, message in enumerate(messages):
        if message.get('kind') not in {'clarification', 'change'}:
            continue
        text = message['text']
        ref = f'message:{index}'
        rule = _rule(text)
        data = DecisionRecord(
            id=digest([identity['run_id'], ref, text])[:24], kind=message['kind'], text=text,
            scope='hu', run_id=identity['run_id'], attempt_id=identity['attempt_id'],
            revision=message.get('revision', 0), origin_ref=ref, evidence_sha256=digest(message),
            actor=message['actor'], status='confirmed', key=rule[0] if rule else None,
            value=rule[1] if rule else None).model_dump()
        for old in records:
            if rule and old['key'] == data['key'] and old['status'] != 'superseded':
                # A correction must explicitly identify replacement, not merely be newer.
                if re.search(r'\b(ahora|corrijo|corrección|sustituye)\b', text.casefold()):
                    old['status'] = 'superseded'
                    data['supersedes'] = old['id']
                elif old['value'] != data['value']:
                    old['status'] = data['status'] = 'conflict'
        records.append(data)
    # Verified source facts are revalidated separately; model interpretations never auto-confirm.
    records.extend(copy.deepcopy(d) for d in previous if d.get('kind') in {'fact', 'interpretation'})
    return records


class ContextManager:
    def __init__(self, root, profile, policy, identity, messages, questions=(), *, cache=None,
                 on_snapshot=None, on_event=None, previous=None):
        self.root, self.profile, self.policy = Path(root), profile, policy
        self.identity = dict(identity)
        self.prompts = PromptContracts()
        self.cache = cache if cache is not None else SourceCache(policy)
        self.on_snapshot, self.on_event = on_snapshot, on_event
        self.decisions = rebuild_decisions(messages, identity, (previous or {}).get('decisions', ()))
        self.questions = list(questions)
        self.last_envelope = None
        self.prompt_identity = {'engine': policy.version, 'policy_sha256': digest(policy.model_dump()),
                                'catalog_sha256': self.prompts.sha256}
        self._messages = messages

    def verify_view(self, decisions):
        required = {d['id']: d for d in self._memory()}
        if {d['id']: d for d in decisions} != required:
            raise ValueError('Cobertura o procedencia de decisiones inválida')

    def observe_fact(self, path, content, sha256):
        rule = _rule(content)
        if not rule or len(content) > 10000:
            return
        identifier = digest([path, sha256])[:24]
        if any(d['id'] == identifier for d in self.decisions):
            return
        item = DecisionRecord(id=identifier, kind='fact', text=content, scope=path,
                              origin_ref=path, evidence_sha256=sha256, actor=None, status='confirmed',
                              key=rule[0], value=rule[1], **{k: self.identity[k] for k in ('run_id', 'attempt_id', 'revision')})
        self.decisions.append(item.model_dump())

    def _memory(self):
        from .repository_policy import safe_target
        originals = {d['id']: d for d in rebuild_decisions(self._messages, self.identity)}
        for decision in self.decisions:
            DecisionRecord.model_validate(decision)
            if (decision['run_id'], decision['attempt_id']) != (self.identity['run_id'], self.identity['attempt_id']):
                raise ValueError('Memoria fuera del intento')
            if decision['kind'] in {'clarification', 'change'}:
                if originals.get(decision['id']) != decision:
                    raise ValueError('Origen de decisión alterado')
            elif decision['kind'] == 'interpretation' and decision['status'] != 'proposed':
                raise ValueError('Interpretación sin confirmación humana original')
            elif decision['kind'] == 'fact':
                if not self.profile.allows_read(decision['scope']):
                    decision['status'] = 'stale'
                    continue
                target = safe_target(self.root, decision['scope'])
                import hashlib
                if (decision['scope'] != decision['origin_ref']
                        or hashlib.sha256(decision['text'].encode('utf-8')).hexdigest() != decision['evidence_sha256']):
                    raise ValueError('Contenido de hecho sin procedencia válida')
                if not target.is_file() or hashlib.sha256(target.read_bytes()).hexdigest() != decision['evidence_sha256']:
                    decision['status'] = 'stale'
        live = [d for d in self.decisions if d['status'] in {'confirmed', 'conflict'}]
        keys = {}
        for decision in live:
            if decision['key']:
                keys.setdefault(decision['key'], set()).add(decision['value'])
        if any(d['status'] == 'conflict' for d in live) or any(len(v) > 1 for v in keys.values()):
            raise DecisionConflict('Decisiones incompatibles requieren aclaración de su sustitución')
        return live

    def prepare(self, role, phase, payload, history, repo_context, *, max_bytes=None, max_tokens=None):
        system, prompt_ref = self.prompts.compose(role, phase)
        try:
            memory = self._memory()
        except DecisionConflict:
            if self.on_snapshot and self.on_event:
                ref = self.on_snapshot(self.memory_snapshot())
                self.on_event({'snapshot_sha256': ref, 'reason': 'conflict'})
            raise
        value = copy.deepcopy(payload)
        value['confirmed_decisions'] = memory
        value['pending_questions'] = self.questions
        if repo_context:
            value['context_tools'] = TOOLS
            value['context_contract'] = context_contract()
        before = json.dumps({**value, 'context_history': history}, ensure_ascii=False)
        selected, excluded, seen = [], [], set()
        sources = []
        for index, item in enumerate(history):
            result = item['result']
            # Cache keys include inventory and current bytes; re-fingerprint old evidence too.
            if repo_context and not result.get('error') and item.get('fingerprint') != repo_context.fingerprint(item['request']):
                excluded.append({'ref': f'round:{index}', 'reason': 'source_changed'})
                # Retrieve the current version rather than leaving the required evidence absent.
                result = repo_context.request(item['request'])
                item = {**item, 'result': result, 'fingerprint': repo_context.fingerprint(item['request'])}
            checksum = digest(result)
            if checksum in seen and not result.get('error'):
                excluded.append({'ref': f'round:{index}', 'reason': 'exact_duplicate'})
                continue
            seen.add(checksum)
            selected.append({'request': item['request'], 'result': result})
            if result.get('path') and result.get('sha256'):
                sources.append({'path': result['path'], 'sha256': result['sha256'], 'ref': f'round:{index}'})
            sources.extend({'path': match['path'], 'sha256': match['sha256'], 'ref': f'round:{index}'}
                           for match in result.get('matches', []))
        value['context_history'] = selected
        # Each payload already carries the minimum for its role. Unclassified human text is never dropped.
        if role not in {'explorer', 'planner', 'developer'} and 'source_summary' in value:
            value.pop('source_summary')
            excluded.append({'ref': 'source_summary', 'reason': 'not_used_by_verification_contract'})
        serialized = json.dumps(value, ensure_ascii=False)
        overhead = len(system.encode('utf-8'))
        size = len(serialized.encode('utf-8')) + overhead
        before_size = len(before.encode('utf-8')) + overhead
        reserve = max(self.policy.output_reserve_tokens, max_tokens or 0)
        # One token per UTF-8 byte is deliberately conservative, not measured endpoint usage.
        selection = SelectionRecord(role=role, phase=phase, included=[d['id'] for d in memory], excluded=excluded,
                                    reason='direct' if not excluded else 'deterministic_reduction', bytes_before=before_size,
                                    bytes_after=size, estimated_input_tokens=size, output_reserve_tokens=reserve,
                                    cache=dict(self.cache.metrics))
        envelope = ContextEnvelope(**self.identity, role=role, policy_sha256=self.prompt_identity['policy_sha256'],
                                   prompt_sha256=prompt_ref['prompt_sha256'], sources=sources,
                                   decisions=memory, questions=self.questions, selection=selection)
        data = {'envelope': envelope.model_dump(), 'decisions': self.decisions, 'prompt': system,
                'contracts': self.prompts.catalog, 'payload': value}
        ref = self.on_snapshot(data) if self.on_snapshot else digest(data)
        metadata = {**self.prompt_identity, **prompt_ref, 'snapshot_sha256': ref,
                    'selection': selection.model_dump()}
        self.last_envelope = data
        if self.on_event:
            self.on_event(metadata)
        if size > min(max_bytes or self.policy.max_prompt_bytes, self.policy.max_prompt_bytes) or size + reserve > self.policy.max_input_tokens:
            raise ContextBudgetError('El mínimo obligatorio y reserva exceden presupuesto; no se truncó contexto')
        self.verify_view(value['confirmed_decisions'])
        return serialized, system, metadata

    def validate(self, role, value, payload):
        validate_output(role, value, payload, self.profile)

    def memory_snapshot(self):
        return {'decisions': self.decisions, 'questions': self.questions}
