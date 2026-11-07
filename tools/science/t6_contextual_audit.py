"""Version-two evaluator contract: exact surfaces, contextual propositions and axes.

This module verifies representation/provenance, never scientific truth or clinical
probability. V1 audit and native-run contracts remain unchanged. Surface nodes
are locations, not automatically extracted atomic facts.
"""
from collections import Counter
import hashlib
import json
import math
import re
import unicodedata

from tether_engine.serde import ContractError, canonical, fingerprint, parse_json
from tools.science.reference_packets import IDENTITY_FIELDS
from tools.science.t6_claim_audit import MAX_SOURCE_BYTES, pointer, require, text, validate_question
from tools.science.t6_dossier_binding import _dossier_bytes, verify_binding

MAX_NODES = 200_000
MAX_CLAIMS = 20_000
STRATA = {'annotation', 'scientific', 'operational', 'clinical_unassessable'}
STANCES = {'source_attributed', 'dossier_endorsed', 'caution'}
DISPOSITIONS = {'formatting', 'operational', 'annotation', 'scientific', 'caution',
                'clinical_unassessable', 'uncertain', 'structured_data'}
PROPOSITION_KEYS = {'subject', 'predicate', 'object', 'negation', 'modal', 'population',
                    'tissue', 'intervention', 'comparator', 'outcome', 'timing', 'orientation'}


def _enum(value, choices, message):
    require(isinstance(value, str) and value in choices, message)


def _span(data, span):
    require(isinstance(span, dict) and set(span) == {'start', 'end'} and
            type(span['start']) is int and type(span['end']) is int and
            0 <= span['start'] < span['end'] <= len(data), 'Invalid nonempty UTF-8 byte interval')
    try:
        return data[span['start']:span['end']].decode('utf-8')
    except UnicodeError as error:
        raise ContractError('Interval splits a UTF-8 character') from error


def _reference_json(proof, approved_roots):
    """Hash the same bounded bytes that are parsed, not a prior filesystem read."""
    from tools.science.t6_dossier_binding import _approved
    require(isinstance(proof, dict) and isinstance(proof.get('path'), str) and
            type(proof.get('bytes')) is int and 0 < proof['bytes'] <= MAX_SOURCE_BYTES,
            'Reference proof needs explicit bounded bytes/path')
    path = _approved(proof['path'], approved_roots)
    with path.open('rb') as stream:
        payload = stream.read(MAX_SOURCE_BYTES + 1)
    require(len(payload) == proof['bytes'] and hashlib.sha256(payload).hexdigest() == proof.get('sha256'),
            'Pinned reference bytes differ')
    return parse_json(payload)


def json_nodes(payload, base_offset=0):
    """Index exact JSON value tokens and decoded values, including repeated strings.

    Duplicate keys/nonfinite values fail. Byte positions refer to original encoded
    tokens; decoded-string positions are a separate coordinate system. No decoded
    text is silently passed off as a contiguous raw dossier quote.
    """
    require(isinstance(payload, bytes) and len(payload) <= MAX_SOURCE_BYTES, 'JSON surface size bound exceeded')
    require(not payload.startswith(b'\xef\xbb\xbf'), 'JSON surface tokens must not include a byte-order marker')
    try:
        document = parse_json(payload)
    except RecursionError as error:
        raise ContractError('JSON surface nesting limit exceeded') from error
    source = payload.decode('utf-8')
    decoder = json.JSONDecoder()
    temporary = []

    def whitespace(index):
        while index < len(source) and source[index] in ' \t\r\n':
            index += 1
        return index

    def walk(index, path, depth):
        require(depth <= 128, 'JSON surface nesting limit exceeded')
        index = whitespace(index)
        start = index
        require(index < len(source), 'Incomplete JSON surface')
        kind = source[index]
        if kind == '{':
            index = whitespace(index + 1)
            while source[index] != '}':
                key, end = decoder.raw_decode(source, index)
                require(isinstance(key, str), 'JSON object key must be a string')
                try:
                    key.encode('utf-8')
                except UnicodeError as error:
                    raise ContractError('Decoded JSON key is not valid UTF-8 text') from error
                index = whitespace(end)
                require(source[index] == ':', 'Invalid JSON object surface')
                index = walk(index + 1, path + '/' + key.replace('~', '~0').replace('/', '~1'), depth + 1)
                index = whitespace(index)
                if source[index] == '}':
                    break
                require(source[index] == ',', 'Invalid JSON object delimiter')
                index = whitespace(index + 1)
            end = index + 1
            value = None
            value_type = 'object'
        elif kind == '[':
            index = whitespace(index + 1)
            number = 0
            while source[index] != ']':
                index = whitespace(walk(index, path + '/' + str(number), depth + 1))
                number += 1
                if source[index] == ']':
                    break
                require(source[index] == ',', 'Invalid JSON array delimiter')
                index = whitespace(index + 1)
            end, value, value_type = index + 1, None, 'array'
        else:
            value, end = decoder.raw_decode(source, index)
            value_type = ('string' if isinstance(value, str) else 'null' if value is None
                          else 'boolean' if type(value) is bool else 'number')
            require(not isinstance(value, float) or math.isfinite(value), 'Nonfinite JSON surface number')
            if isinstance(value, str):
                try:
                    value.encode('utf-8')
                except UnicodeError as error:
                    raise ContractError('Decoded JSON string is not valid UTF-8 text') from error
        require(len(temporary) < MAX_NODES, 'Too many JSON surface nodes')
        temporary.append((path, start, end, value_type))
        return end

    require(whitespace(walk(0, '', 0)) == len(source), 'Trailing JSON surface content')
    # Store only requested boundary offsets, avoiding an O(document bytes) array
    # of Python integers. Encoding disjoint chunks is linear in input length.
    offsets, previous, count = {}, 0, base_offset
    for position in sorted({p for _, start, end, _ in temporary for p in (start, end)}):
        count += len(source[previous:position].encode('utf-8'))
        offsets[position], previous = count, position
    result = []
    for path, start, end, value_type in temporary:
        value = pointer(document, path)
        result.append(dict(pointer=path, raw_span=dict(start=offsets[start], end=offsets[end]),
                           value_type=value_type, value_sha256=fingerprint(value)))
    return sorted(result, key=lambda n: (n['raw_span']['start'], -n['raw_span']['end']))


def surface_from_binding(binding):
    """Compile complete physical lines and original-provider JSON token locations.

    Callers seeking a qualified source report must use compile_surface or audit_v2,
    which replay the binding. This helper alone does not authenticate originals.
    """
    from pathlib import Path
    data = _dossier_bytes(Path(binding['dossier']['path']))
    require(hashlib.sha256(data).hexdigest() == binding['dossier']['sha256'], 'Dossier bytes changed')
    units = sorted(binding['source_units'], key=lambda u: u['section_span']['start'])
    unit_index = 0
    nodes, lines, cursor, used_metrics = [], [], 0, set()
    prefix, suffix = b'Provider metrics (descriptive): `', b'`.'
    for number, raw in enumerate(data.splitlines(keepends=True)):
        start, end = cursor, cursor + len(raw)
        cursor = end
        value = raw.decode('utf-8')
        while unit_index < len(units) and start >= units[unit_index]['section_span']['end']:
            unit_index += 1
        source_unit = units[unit_index] if unit_index < len(units) and start >= units[unit_index]['section_span']['start'] else None
        source_id = source_unit['observation_id'] if source_unit else None
        origin = 'formatting' if not raw.strip() else 'prose'
        if raw.startswith(b'> ') and source_unit:
            origin = 'source_quote'
        if raw.startswith(prefix):
            require(source_unit is not None, 'Provider JSON outside a verified source section')
            stripped = raw.rstrip(b'\r\n')
            require(stripped.endswith(suffix), 'Malformed provider JSON wrapper')
            payload = stripped[len(prefix):-len(suffix)]
            original = source_unit['source_audit']['projected_original_row']
            expected = {k: v for k, v in original.items() if k not in IDENTITY_FIELDS}
            require(parse_json(payload) == expected, 'Rendered provider fields differ from original projection')
            require(source_id not in used_metrics, 'Duplicate provider JSON in one source section')
            used_metrics.add(source_id)
            origin = 'provider_json'
            for item in json_nodes(payload, start + len(prefix)):
                node = dict(item, origin=origin, source_unit_id=source_id, line_id=f'L{number:06d}')
                node['node_id'] = 'J' + fingerprint(node)
                nodes.append(node)
        line = dict(line_id=f'L{number:06d}', span=dict(start=start, end=end),
                    source_unit_id=source_id, origin=origin)
        lines.append(line)
        node = dict(node_id=line['line_id'], origin=origin, source_unit_id=source_id,
                    raw_span=line['span'], value_type='literal', value_sha256=fingerprint(value))
        nodes.append(node)
        require(len(nodes) <= MAX_NODES, 'Surface node count exceeds finite limit')
    require(cursor == len(data), 'Incomplete dossier surface coverage')
    expected_metric_units = {u['observation_id'] for u in units if any(
        k not in IDENTITY_FIELDS for k in u['source_audit']['projected_original_row'])}
    require(used_metrics == expected_metric_units, 'Missing original provider JSON block')
    require(len({n['node_id'] for n in nodes}) == len(nodes), 'Duplicate surface node identity')
    return dict(schema_version=2, role='evaluation_only', kind='contextual_dossier_surface',
        binding_sha256=fingerprint(binding), dossier=dict(binding['dossier']), question=dict(binding['question']),
        lines=lines, nodes=nodes, structural_coverage_bytes=cursor,
        scientific_atomization='not_performed', scientific_validity='not_established')


def compile_surface(binding_proof, *, approved_roots):
    return surface_from_binding(verify_binding(binding_proof, approved_roots=approved_roots))


def empty_draft(surface, annotator_id='review_required'):
    """An exhaustive structural template with explicitly unresolved semantics."""
    require(text(annotator_id), 'Draft needs an identified preparation/annotation owner')
    lines = [dict(line_id=line['line_id'], kind='formatting' if line['origin'] == 'formatting' else
        'structured_data' if line['origin'] == 'provider_json' else 'uncertain',
        reason='Structural location only; scientific extraction/review required.', claim_ids=[]) for line in surface['lines']]
    values = [dict(node_id=n['node_id'], kind='container_context' if n['value_type'] in {'object','array'} else 'uncertain',
        reason='Original value located; no automatic scientific proposition or exclusion.', claim_ids=[])
        for n in surface['nodes'] if n['value_type'] != 'literal']
    return dict(schema_version=2, role='evaluation_only', status='draft', annotator_id=annotator_id,
        surface_sha256=fingerprint(surface), question=dict(surface['question']), claims=[],
        line_dispositions=lines, value_dispositions=values)


def build_surface(binding_proof, output, *, approved_roots):
    """Reserve a fresh evaluator job and retain failures, without native inference."""
    from pathlib import Path
    import time
    from tether_engine.journal import RunJournal
    from tether_engine.serde import write_json
    from tools.science.run_comparison import pin
    output = Path(output).resolve()
    require(not output.is_relative_to(Path(binding_proof['path']).resolve().parent),
            'Contextual output must be outside the original binding directory')
    journal = RunJournal(output, kind='build')
    stage, started = 'source_replay', time.monotonic()
    try:
        journal.append('contextual_source_replay_started', binding=binding_proof)
        surface = compile_surface(binding_proof, approved_roots=approved_roots)
        journal.append('contextual_surface_compiled', lines=len(surface['lines']), nodes=len(surface['nodes']),
                       dossier_bytes=surface['structural_coverage_bytes'])
        draft = empty_draft(surface)
        stage = 'draft_validation'
        validate_inventory(draft, surface)
        stage = 'artifact_writes'
        for name, value in [('surface.json', surface), ('draft-inventory.json', draft)]:
            require(len(canonical(value)) <= MAX_SOURCE_BYTES, 'Contextual artifact exceeds 64 MiB; no records dropped')
            write_json(output / name, value)
        report = dict(schema_version=2, role='evaluation_only', status='contextual_surface_and_unqualified_draft_completed',
            binding=binding_proof, surface=pin(output / 'surface.json'), draft=pin(output / 'draft-inventory.json'),
            lines=len(surface['lines']), nodes=len(surface['nodes']), dossier_bytes=surface['structural_coverage_bytes'],
            elapsed_seconds=time.monotonic() - started, native_model_calls=0, clinical_labels_created=0,
            scientific_atomization='not_performed', scientific_validity='not_established',
            code=pin(Path(__file__)), probability=None)
        write_json(output / 'report.json', report)
        journal.append('build_completed', report=pin(output / 'report.json'))
        return report
    except BaseException as error:
        journal.fail(error, stage)
        raise
    finally:
        journal.close()


def _resolve(fragment, nodes, data):
    require(isinstance(fragment, dict) and set(fragment) == {'node_id', 'span', 'text'}, 'Invalid quote fragment')
    require(fragment['node_id'] in nodes, 'Quote fragment references a foreign surface node')
    node = nodes[fragment['node_id']]
    raw = _span(data, node['raw_span'])
    value = raw if node['value_type'] == 'literal' else parse_json(raw)
    # For a JSON string the interval addresses decoded UTF-8 bytes. For other
    # JSON types the entire exact token is a literal, not an invented paraphrase.
    decoded = value if isinstance(value, str) else raw
    selected = _span(decoded.encode('utf-8'), fragment['span'])
    require(selected == fragment['text'], 'Quote fragment differs from exact decoded/raw text')
    return node


def _numeric_component(component, parents, nodes, data):
    """A reported number is an exact located component, never a substring guess."""
    node = _resolve(component, nodes, data)
    span = component['span']
    require(any(p['node_id'] == component['node_id'] and p['span']['start'] <= span['start']
                and span['end'] <= p['span']['end'] for p in parents),
            'Numerical component is outside its declared focus/context fragments')
    raw = _span(data, node['raw_span'])
    value = raw if node['value_type'] == 'literal' else parse_json(raw)
    source = (value if isinstance(value, str) else raw).encode('utf-8')
    before = source[:span['start']].decode('utf-8')
    after = source[span['end']:].decode('utf-8')

    def continuation(c):
        return c.isdigit() or c in '._+−±eExX×^<>=≤≥⁺⁻' or unicodedata.category(c) == 'Pd'

    require(not before or not continuation(before[-1]), 'Numerical component drops a sign/token prefix')
    trailing_sentence_period = after.startswith('.') and (len(after) == 1 or not after[1].isdigit())
    require(not after or trailing_sentence_period or not continuation(after[0]),
            'Numerical component truncates a number/exponent/bound')
    # A spaced sign, comparator or scientific multiplier is still meaningful;
    # do not mistake '- 0.02' or '1.18 × 10^-3' for a positive/plain estimate.
    math_join = '+−±-×^<>=≤≥⁺⁻'
    require(not before or not before[-1].isspace() or not before.rstrip() or
            before.rstrip()[-1] not in math_join, 'Numerical component omits a spaced mathematical prefix')
    require(not after or not after[0].isspace() or not after.lstrip() or
            after.lstrip()[0] not in math_join, 'Numerical component omits a spaced mathematical suffix')
    return component['text']


def proposition_key(claim, question):
    bundle = claim['numeric_bundle']
    numbers = {k: (v['text'] if v is not None else None) for k, v in bundle.items() if k != 'reason'} if bundle else None
    return fingerprint(dict(question=question, context=claim['context'],
                            proposition=claim['proposition'], stratum=claim['stratum'], stance=claim['stance'],
                            unit_kind=claim['unit_kind'], numeric_bundle=numbers))


def validate_inventory(inventory, surface):
    require(isinstance(inventory, dict) and type(inventory.get('schema_version')) is int and
            inventory['schema_version'] == 2 and inventory.get('role') == 'evaluation_only', 'Expected v2 evaluator inventory')
    require(inventory.get('surface_sha256') == fingerprint(surface) and
            inventory.get('question') == surface['question'], 'Inventory surface/hypothesis differs')
    validate_question(inventory['question'])
    require(text(inventory.get('annotator_id')), 'Inventory needs an identified annotator')
    _enum(inventory.get('status'), {'draft', 'reviewed'}, 'Invalid inventory review status')
    claims = inventory.get('claims')
    require(isinstance(claims, list) and len(claims) <= MAX_CLAIMS, 'Invalid or oversized claim inventory')
    require(all(isinstance(c, dict) and text(c.get('claim_id')) for c in claims), 'Invalid claim identity')
    require(len({c['claim_id'] for c in claims}) == len(claims), 'Duplicate claim identity')
    from pathlib import Path
    data = _dossier_bytes(Path(surface['dossier']['path']))
    require(hashlib.sha256(data).hexdigest() == surface['dossier']['sha256'], 'Dossier changed before inventory checks')
    nodes = {n['node_id']: n for n in surface['nodes']}
    groups, claim_nodes = {}, {}
    expected_keys = {'claim_id', 'stratum', 'stance', 'unit_kind', 'context', 'proposition',
                     'focus', 'context_fragments', 'entity_resolution', 'entity_reason', 'numeric_bundle', 'dependence'}
    for claim in claims:
        require(set(claim) == expected_keys, 'Unknown/missing v2 claim fields; canonical propositions are not literal statements')
        _enum(claim['stratum'], STRATA, 'Invalid claim stratum')
        _enum(claim['stance'], STANCES, 'Invalid attribution/endorsement mode')
        _enum(claim['unit_kind'], {'proposition', 'estimate_bundle'}, 'Standalone numerical fragments cannot be counting units')
        _enum(claim['entity_resolution'], {'resolved', 'uncertain'}, 'Invalid entity resolution')
        require(text(claim['entity_reason']), 'Entity/coreference resolution needs rationale')
        dependence = claim['dependence']
        require(isinstance(dependence, dict) and set(dependence) == {'status', 'group_ids', 'reason'}
                and text(dependence['reason']), 'Dependence/unknowns need explicit provenance rationale')
        _enum(dependence['status'], {'known_overlap', 'partially_known', 'unknown', 'not_applicable'},
              'Invalid source-dependence status')
        group_ids = dependence['group_ids']
        require(isinstance(group_ids, list) and all(text(x) for x in group_ids) and len(set(group_ids)) == len(group_ids),
                'Invalid source-dependence groups')
        require(bool(group_ids) == (dependence['status'] in {'known_overlap', 'partially_known'}),
                'Unknown dependence is not an independent group or known overlap')
        context = claim['context']
        require(isinstance(context, dict) and set(context) == {'scope', 'id'}, 'Missing proposition context')
        _enum(context['scope'], {'record', 'study', 'hypothesis', 'operational'}, 'Invalid context scope')
        require(text(context['id']), 'Context identity must be explicit, including uncertain named contexts')
        prop = claim['proposition']
        require(isinstance(prop, dict) and set(prop) == PROPOSITION_KEYS, 'Incomplete contextual proposition')
        require(all(text(prop[k]) for k in ('subject', 'predicate', 'object')), 'Proposition needs subject/relation/object')
        require(type(prop['negation']) is bool, 'Negation must remain explicit')
        _enum(prop['modal'], {'asserted', 'possible', 'conditional', 'proposal'}, 'Missing modal force')
        require(all(prop[k] is None or text(prop[k]) for k in
            ('population', 'tissue', 'intervention', 'comparator', 'outcome', 'timing')), 'Context values must remain text or explicit null')
        orientation = prop['orientation']
        require(orientation is None or isinstance(orientation, dict) and set(orientation) == {'exposure', 'outcome'}
                and all(text(v) for v in orientation.values()), 'Invalid exposure/outcome orientation')
        node = _resolve(claim['focus'], nodes, data)
        require(node['origin'] != 'formatting', 'Formatting is not a scientific proposition')
        if node['origin'] in {'provider_json', 'source_quote'}:
            require(claim['stance'] == 'source_attributed', 'Quoted provider content cannot become dossier endorsement')
        require(isinstance(claim['context_fragments'], list) and len(claim['context_fragments']) <= 64,
                'Invalid context fragment inventory')
        refs = [node] + [_resolve(f, nodes, data) for f in claim['context_fragments']]
        if context['scope'] == 'record':
            require(context['id'] == node['source_unit_id'] and context['id'] is not None,
                    'Record context differs from the actual source occurrence')
            require(all(n['source_unit_id'] in {None, context['id']} for n in refs),
                    'Record-scoped proposition cannot import another record as its context')
        if context['scope'] == 'hypothesis':
            require(context['id'] == fingerprint(surface['question']), 'Hypothesis context differs')
        bundle = claim['numeric_bundle']
        if claim['unit_kind'] == 'estimate_bundle':
            require(isinstance(bundle, dict) and set(bundle) == {'estimate', 'interval', 'p_value', 'scale', 'reason'},
                    'Estimate/interval/P must stay in one explicit bundle')
            require(isinstance(bundle['estimate'], dict) and text(bundle['reason']) and orientation is not None,
                    'Numerical bundle needs estimate, orientation and qualification')
            fragments = [claim['focus']] + claim['context_fragments']
            for field in ('estimate', 'interval', 'p_value', 'scale'):
                if bundle[field] is not None:
                    require(isinstance(bundle[field], dict), 'Numerical bundle components need exact coordinates or null')
                    _numeric_component(bundle[field], fragments, nodes, data)
        else:
            require(bundle is None, 'Numerical components cannot silently become extra propositions')
        key = proposition_key(claim, surface['question'])
        groups.setdefault(key, []).append(claim['claim_id'])
        claim_nodes[claim['claim_id']] = refs
    dispositions = inventory.get('line_dispositions')
    require(isinstance(dispositions, list) and len(dispositions) == len(surface['lines']) and
            all(isinstance(d, dict) for d in dispositions) and [d.get('line_id') for d in dispositions] ==
            [line['line_id'] for line in surface['lines']], 'Every physical line needs one ordered disposition')
    ids, covered = {c['claim_id'] for c in claims}, set()
    for line, disposition in zip(surface['lines'], dispositions):
        require(isinstance(disposition, dict) and set(disposition) == {'line_id', 'kind', 'reason', 'claim_ids'},
                'Invalid line disposition')
        _enum(disposition['kind'], DISPOSITIONS, 'Unknown coverage disposition')
        require(text(disposition['reason']), 'Coverage exclusions require an explicit reason')
        linked = disposition['claim_ids']
        require(isinstance(linked, list) and all(text(x) for x in linked) and
                len(set(linked)) == len(linked) and not set(linked) - ids, 'Invalid coverage claim references')
        if disposition['kind'] in {'annotation', 'scientific', 'caution', 'clinical_unassessable'}:
            require(bool(linked), 'Asserted content cannot silently vanish from the inventory')
        if inventory['status'] == 'reviewed':
            require(disposition['kind'] != 'uncertain', 'Unresolved extraction cannot be marked reviewed')
        if disposition['kind'] == 'structured_data':
            require(line['origin'] == 'provider_json', 'Structured-data disposition on a prose line')
        if line['origin'] == 'provider_json' and inventory['status'] == 'reviewed':
            require(disposition['kind'] == 'structured_data', 'Embedded JSON needs its own complete value dispositions')
        for identity in linked:
            require(any(n.get('line_id', n['node_id']) == line['line_id'] for n in claim_nodes[identity]),
                    'Coverage points to a claim without a fragment on this line')
        covered.update(linked)
    values = [n for n in surface['nodes'] if n['value_type'] != 'literal']
    value_dispositions = inventory.get('value_dispositions')
    require(isinstance(value_dispositions, list) and len(value_dispositions) == len(values) and
            all(isinstance(d, dict) for d in value_dispositions) and
            [d.get('node_id') for d in value_dispositions] == [n['node_id'] for n in values],
            'Every provider JSON value needs one ordered disposition')
    for node, disposition in zip(values, value_dispositions):
        require(set(disposition) == {'node_id', 'kind', 'reason', 'claim_ids'} and text(disposition['reason']),
                'Invalid provider-value disposition/rationale')
        _enum(disposition['kind'], (DISPOSITIONS - {'formatting', 'structured_data'}) | {'source_data', 'container_context'},
              'Unknown provider-value disposition')
        if node['value_type'] in {'object', 'array'}:
            require(disposition['kind'] == 'container_context', 'JSON containers supply context, not extra atomic facts')
        else:
            require(disposition['kind'] != 'container_context', 'Scalar facts cannot disappear as container context')
        linked = disposition['claim_ids']
        require(isinstance(linked, list) and all(text(x) for x in linked) and len(set(linked)) == len(linked)
                and not set(linked) - ids, 'Invalid provider-value claim links')
        if re.fullmatch(r'/textMiningSentences(?:/\d+(?:/text)?)?', node['pointer']) and node['value_type'] == 'string':
            require(disposition['kind'] not in {'source_data', 'operational'},
                    'Mined scientific text requires explicit proposition/uncertainty disposition')
        if disposition['kind'] in {'annotation', 'scientific', 'caution', 'clinical_unassessable'}:
            require(bool(linked), 'Scientific provider content cannot be silently omitted')
        if inventory['status'] == 'reviewed':
            require(disposition['kind'] != 'uncertain', 'Unresolved provider extraction cannot be marked reviewed')
        for identity in linked:
            require(any(n['node_id'] == node['node_id'] for n in claim_nodes[identity]),
                    'Provider-value disposition links a claim without that exact node')
        covered.update(linked)
    require(covered == ids,
            'Every proposed claim needs a coverage disposition')
    return groups


def audit_v2(binding_proof, inventory, review, references, *, approved_roots):
    """Replay original sources, then check contextual reviewer assertions.

    References are separately byte-pinned evaluator records scoped to the exact
    hypothesis/proposition. Their scientific qualification remains a reviewer
    attestation, not a truth guarantee supplied by hashing.
    """
    surface = compile_surface(binding_proof, approved_roots=approved_roots)
    result = assess_review(inventory, surface, review, references, approved_roots=approved_roots)
    result.update(source_binding='current_originals_replayed', binding=binding_proof)
    return result


def assess_review(inventory, surface, review, references, *, approved_roots):
    """Contract check for a supplied surface; audit_v2 additionally replays sources."""
    groups = validate_inventory(inventory, surface)
    require(isinstance(references, list), 'Missing evaluator reference inventory')
    registered = {}
    for proof in references:
        reference = _reference_json(proof, approved_roots)
        require(isinstance(reference, dict) and type(reference.get('schema_version')) is int and reference['schema_version'] == 1 and
                reference.get('role') == 'evaluation_only' and text(reference.get('reference_id')),
                'Scientific reference must remain evaluator-only')
        require(text(reference.get('attestor_id')) and text(reference.get('basis')) and text(reference.get('limitations')),
                'Reference qualification needs an identified attestor, basis and limits')
        _enum(reference.get('qualification'), {'unreviewed', 'scope_adjudicated'}, 'Unknown reference qualification')
        identity = reference['reference_id']
        require(identity not in registered, 'Duplicate scientific reference identity')
        require(reference.get('question_sha256') == fingerprint(surface['question']), 'Reference hypothesis differs')
        require(reference.get('binding_sha256') == surface['binding_sha256'],
                'Reference run/temporal/program context differs')
        parent = reference.get('basis_proof')
        require(isinstance(parent, dict), 'Scoped reference needs an immutable evaluator parent')
        parent_document = _reference_json(parent, approved_roots)
        require(isinstance(parent_document, dict) and parent_document.get('role') == 'evaluation_only',
                'Reference parent cannot become an agent input')
        located = pointer(parent_document, reference.get('basis_pointer'))
        require(fingerprint(located) == reference.get('basis_value_sha256'), 'Scoped reference parent value differs')
        registered[identity] = reference
    require(isinstance(review, dict) and type(review.get('schema_version')) is int and review['schema_version'] == 2
            and review.get('role') == 'evaluation_only' and text(review.get('reviewer_id')), 'Expected v2 evaluator review')
    require(review.get('inventory_sha256') == fingerprint(inventory) and review.get('surface_sha256') == fingerprint(surface)
            and review.get('references_sha256') == fingerprint(references), 'Review input binding differs')
    _enum(review.get('mode'), {'development_source_review', 'blinded_paired_review'}, 'Unknown review mode')
    rows = review.get('claims')
    require(isinstance(rows, list) and all(isinstance(r, dict) for r in rows) and
            [r.get('claim_id') for r in rows] == [c['claim_id'] for c in inventory['claims']], 'Review must cover every proposed claim')
    counters = {}
    judged_groups, uncertainty_groups = {}, {}
    for claim, row in zip(inventory['claims'], rows):
        for axis, values in {
            'source_fidelity': {'supported', 'contradicted', 'unsupported', 'unassessable'},
            'scientific_validity': {'supported', 'contradicted', 'disputed', 'unsupported', 'unassessable', 'not_applicable'},
            'applicability': {'applicable', 'context_mismatch', 'uncertain', 'not_claimed'},
            'attribution': {'correct', 'misattributed', 'unresolved'},
            'uncertainty': {'low', 'moderate', 'high'},
        }.items():
            _enum(row.get(axis), values, 'Invalid review axis: ' + axis)
        require(text(row.get('reason')), 'Every contextual judgment needs rationale')
        used = row.get('reference_ids')
        require(isinstance(used, list) and all(text(x) for x in used) and len(set(used)) == len(used)
                and not set(used) - registered.keys(), 'Invalid scientific reference links')
        key = proposition_key(claim, surface['question'])
        for identity in used:
            require(registered[identity].get('proposition_key') == key, 'Reference proposition/orientation/context differs')
        if row['scientific_validity'] in {'supported', 'contradicted', 'disputed'}:
            require(bool(used) and all(registered[i].get('qualification') == 'scope_adjudicated' for i in used),
                    'A substantive scientific rating requires scoped adjudication references')
        if claim['stratum'] == 'clinical_unassessable':
            require(row['scientific_validity'] == 'unassessable' and row['applicability'] in {'uncertain', 'not_claimed'},
                    'Clinical assertions are quarantined in this source-quality phase')
        if claim['entity_resolution'] == 'uncertain':
            require(row['scientific_validity'] not in {'supported', 'contradicted'} and row['applicability'] != 'applicable',
                    'Unresolved entity/coreference cannot become a definite scientific/applicability judgment')
        signature = tuple(row[a] for a in ('source_fidelity', 'scientific_validity', 'applicability', 'attribution'))
        require(key not in judged_groups or judged_groups[key] == signature,
                'Repeated canonical proposition has conflicting judgments; adjudicate explicitly')
        if key not in judged_groups:
            stratum = counters.setdefault((claim['stratum'], claim['stance']), {})
            for axis in ('source_fidelity', 'scientific_validity', 'applicability', 'attribution'):
                stratum.setdefault(axis, Counter())[row[axis]] += 1
        judged_groups[key] = signature
        previous = uncertainty_groups.get(key, (None, 'low'))[1]
        ranks = {'low': 0, 'moderate': 1, 'high': 2}
        worst = max((previous, row['uncertainty']), key=ranks.get)
        uncertainty_groups[key] = ((claim['stratum'], claim['stance']), worst)
    for stratum, uncertainty in uncertainty_groups.values():
        counters[stratum].setdefault('uncertainty', Counter())[uncertainty] += 1
    strata = [dict(stratum=k[0], stance=k[1], canonical_groups=sum(v['source_fidelity'].values()),
                   axes={axis: dict(sorted(count.items())) for axis, count in v.items()})
              for k, v in sorted(counters.items())]
    dependence_groups = {}
    for claim in inventory['claims']:
        for identity in claim['dependence']['group_ids']:
            dependence_groups.setdefault(identity, []).append(claim['claim_id'])
    return dict(schema_version=2, role='evaluation_only', status='contextual_contract_verified_not_scientific_truth',
        inventory_sha256=fingerprint(inventory), review_sha256=fingerprint(review), surface_sha256=fingerprint(surface),
        occurrence_count=len(inventory['claims']), canonical_group_count=len(groups), strata=strata,
        declared_dependence_groups=dependence_groups,
        unknown_dependence_occurrences=sum(c['dependence']['status'] == 'unknown' for c in inventory['claims']),
        uncertainty_aggregation='maximum_ordinal_across_occurrences_per_canonical_group',
        atomic_completeness='reviewer_attestation_only' if inventory['status'] == 'reviewed' else 'unqualified_draft',
        coverage_bytes=surface['structural_coverage_bytes'], scientific_error_rate=None,
        scientific_validity='not_established_by_contract', clinical_probability=None,
        source_binding='not_replayed_by_this_entrypoint',
        limitations='Complete line disposition and exact fragments do not prove complete/correct semantic atomization. Reference qualification, proposition grouping, source dependence and review mode are attested. No pooled strata, independent sample count, superiority or clinical prediction is inferred.')
