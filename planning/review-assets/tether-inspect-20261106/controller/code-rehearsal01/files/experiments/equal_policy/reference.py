"""BG02 adapter to the installed, qualified TETHER validator.

This module intentionally uses TETHER. It is not the independent comparator.
Run under the pinned installed Python with -I; package locations are reported.
Preparation never calls quote/select. Native execution is a separate corpus
materialization step, performed before the corpus/expected outcomes are frozen.
"""
from __future__ import annotations

import argparse
import hashlib
import io
from pathlib import Path
import json
import re
import sys
import tempfile


def runtime_identity():
    import asof
    import tether
    return dict(python=sys.executable, asof_version=asof.__version__,
                tether_version=tether.__version__, asof_file=asof.__file__,
                tether_file=tether.__file__)


def trusted_runtime(qualification_root):
    import asof
    from tether._presentation import code_proof
    qualified = Path(qualification_root).resolve()
    core = Path(asof.__file__).parent
    hash_file = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    return dict(schema_version=1, versions=dict(tether='0.5.1', asof='0.3.12'),
        launcher_proof=code_proof(), core_code_sha256={p.relative_to(core).as_posix(): hash_file(p)
            for p in sorted(core.rglob('*.py'))},
        qualification=dict(path=str(qualified / 'QUALIFICATION.json'), sha256=hash_file(qualified / 'QUALIFICATION.json')),
        wheels=[dict(filename=p.name, sha256=hash_file(p), bytes=p.stat().st_size)
                for p in sorted((qualified / 'wheels').glob('*.whl'))],
        runtime_paths=runtime_identity())


def _path(root, paths, name):
    from asof.serde import ContractError, safe_child
    value = paths.get(name)
    if value is None:
        return None
    if type(value) is not str or not value:
        raise ContractError("Descriptor paths must be nonempty relative strings")
    return safe_child(Path(root).absolute(), value)


def _descriptor_contract(value):
    from asof.serde import ContractError
    required = {'schema_version', 'control_id', 'operation', 'variant', 'paths', 'options', 'anchors'}
    if type(value) is not dict or set(value) != required:
        raise ContractError('Descriptor fields differ from the declared experiment envelope')
    if type(value['schema_version']) is not int or value['schema_version'] != 1:
        raise ContractError('Unsupported experiment descriptor schema')
    if type(value['control_id']) is not str or not value['control_id'].strip():
        raise ContractError('Missing experiment control identity')
    for name in ('paths', 'options', 'anchors'):
        if type(value[name]) is not dict:
            raise ContractError('Descriptor ' + name + ' must be an object')
    operation, variant = value['operation'], value['variant']
    if operation not in ('prepare_run', 'verify_run', 'inspect_run') or variant not in ('core_v2_catalog1', 'artifact_policy_v2'):
        raise ContractError('Unknown experiment operation/variant')
    allowed = {'case', 'snapshot', 'catalog', 'scorer', 'replay', 'local_model',
               'catalog_policy', 'policy_roots', 'run_dir', 'trusted_runtime'}
    paths = {key: val for key, val in value['paths'].items() if val is not None}
    if set(value['paths']) - allowed or any(type(v) is not str or not v for v in paths.values()):
        raise ContractError('Invalid experiment path declaration')
    options, anchors = value['options'], value['anchors']
    if set(options) - {'budget', 'disabled', 'review_enabled', 'process_limits', 'policy_use'}:
        raise ContractError('Unknown experiment option')
    if set(anchors) - {'receipt_sha256', 'frame_sha256'}:
        raise ContractError('Unknown experiment anchor')
    if any(type(item) is not str or re.fullmatch(r'[0-9a-f]{64}', item) is None for item in anchors.values()):
        raise ContractError('Malformed experiment anchor')
    if operation == 'prepare_run':
        if not {'case', 'snapshot'} <= set(paths) or 'run_dir' in paths or anchors.get('receipt_sha256') is not None:
            raise ContractError('Inapplicable or missing preparation fields')
        if variant == 'artifact_policy_v2':
            if not {'catalog', 'catalog_policy', 'policy_roots'} <= set(paths) or not options.get('policy_use') or not anchors.get('frame_sha256'):
                raise ContractError('Incomplete artifact policy declaration')
        elif ({'catalog_policy', 'policy_roots'} & set(paths) or options.get('policy_use') is not None or anchors.get('frame_sha256') is not None):
            raise ContractError('Artifact policy fields supplied to catalog1 variant')
    elif 'run_dir' not in paths or set(paths) - {'run_dir', 'trusted_runtime'} or options or anchors.get('frame_sha256') is not None:
        raise ContractError('Inapplicable or missing archived-run descriptor fields')
    if 'budget' in options and (type(options['budget']) is not dict or set(options['budget']) -
            {'max_calls', 'max_input_tokens', 'max_output_tokens', 'max_cost_usd', 'max_seconds', 'max_retries'}):
        raise ContractError('Invalid experiment budget fields')
    if 'disabled' in options and (type(options['disabled']) is not list or
            any(type(item) is not str for item in options['disabled'])):
        raise ContractError('Invalid disabled-category declaration')
    if set(options.get('disabled', [])) - {'genetics', 'perturbation', 'expression', 'modality', 'literature', 'clinical', 'safety', 'pathway'}:
        raise ContractError('Unknown disabled category')
    if 'process_limits' in options and (type(options['process_limits']) is not dict or
            set(options['process_limits']) - {'timeout_seconds', 'max_output_bytes'}):
        raise ContractError('Invalid process limits declaration')
    if 'review_enabled' in options and type(options['review_enabled']) is not bool:
        raise ContractError('Invalid review flag')
    from asof.serde import decode
    from asof.workflow import Budget
    decode(Budget, options.get('budget', {})).validate()


def _configuration(root, descriptor):
    from asof.agents import ExtractiveBackend, ReplayBackend
    from asof.contracts import Category
    from asof.local_model import LocalSelectionBackend
    from asof.serde import ContractError
    from asof.workflow import Budget
    from tether._process import ProcessLimits
    paths, options = descriptor['paths'], descriptor.get('options', {})
    limits = ProcessLimits(**options.get('process_limits', {}))
    limits.validate()
    budget = Budget(**options.get('budget', {}))
    budget.validate()
    disabled = tuple(Category(value) for value in options.get('disabled', []))
    review = options.get('review_enabled', True)
    if type(review) is not bool:
        raise ContractError('Invalid review flag in experiment descriptor')
    if paths.get('replay') and paths.get('local_model'):
        raise ContractError('Choose replay or explicit local inference')
    # Constructors parse/validate controls; none makes an inference request.
    backend = (ReplayBackend(_path(root, paths, 'replay')) if paths.get('replay') else
               LocalSelectionBackend(_path(root, paths, 'local_model')) if paths.get('local_model') else
               ExtractiveBackend())
    return budget, disabled, review, backend, limits


def _core_prepare(root, descriptor):
    from asof.chrono import load_snapshot
    from asof.contracts import Case, Category, EvidenceStatus
    from asof.scorer import ScorerArtifact, preflight_scorer
    from asof.serde import decode, encode, read_json
    paths = descriptor['paths']
    _configuration(root, descriptor)
    case = decode(Case, read_json(_path(root, paths, 'case')), 'case')
    case.validate()
    store = load_snapshot(_path(root, paths, 'snapshot'), case, _path(root, paths, 'catalog'))
    store.execution_base()
    model = decode(ScorerArtifact, read_json(_path(root, paths, 'scorer')), 'scorer') if paths.get('scorer') else None
    reason = preflight_scorer(case, store.snapshot.profile, model)
    observed = [record.observation.observation_id for category in Category
                for record in store.query(case, category)
                if record.observation.status == EvidenceStatus.OBSERVED]
    return dict(admitted_observation_ids=sorted(store.admitted_fingerprints),
                eligible_observation_ids=sorted(observed), exclusions=encode(store.exclusions),
                scorer_preflight=reason)


def _policy_request(root, descriptor):
    from asof.serde import ContractError
    from tether._catalog_binding import PolicyRequest
    paths = descriptor['paths']
    if any(paths.get(key) for key in ('scorer', 'replay', 'local_model')):
        raise ContractError('Artifact policy supports offline execution without scorer/replay/local-model')
    request = PolicyRequest(*(_path(root, paths, key) for key in
        ('catalog_policy', 'policy_roots', 'case', 'snapshot', 'catalog')),
        descriptor.get('options', {}).get('policy_use'), descriptor.get('anchors', {}).get('frame_sha256'))
    request.validate()
    return request


def _policy_prepare(root, descriptor, *, scratch_dir=None):
    from asof.serde import read_json
    from tether._catalog_binding import prepare_policy_run
    _configuration(root, descriptor)
    request = _policy_request(root, descriptor)
    # Retained preparations are separate from immutable input bundles. The
    # comparator must report its retention boundary before timing comparisons.
    temporary = Path(tempfile.mkdtemp(prefix='bg02-reference-policy-', dir=scratch_dir))
    binding = prepare_policy_run(temporary, request)
    seal = read_json(temporary / binding['path'])
    copied = dict(descriptor)
    copied['paths'] = {key: value for key, value in seal['execution'].items()}
    result = _core_prepare(temporary, copied)
    result['preparation_evidence'] = dict(directory=str(temporary), binding=binding)
    return result


def _verified_observations(root):
    """Project verified outputs; validity comes from canonical verification."""
    from asof.serde import read_json, read_ledger_json, encode
    from asof.journal import read_chain
    run = read_json(root / 'run.json')
    ledger = read_ledger_json(root / 'ledger.json')
    trace = encode(read_chain(root / 'trace.jsonl'))
    return dict(status=run['status'], selected_observation_ids=[
        item['evidence']['observation']['observation_id'] for item in ledger['claims']],
        admitted_observation_ids=list(read_json(root / 'receipt.json')['admitted_fingerprints']),
        exclusions=run['exclusions'], features=read_json(root / 'features.json'),
        prediction=read_json(root / 'prediction.json'), calls=run['calls'],
        measured_usage=run['measured_usage'], estimated_usage=run['estimated_usage'],
        accounting=[event['details'] for event in trace if event['event'] == 'attempt_accounted'],
        dispatches=[event['details'] for event in trace if event['event'] == 'dispatch'])


def validate_bundle(root: Path, descriptor: dict, *, scratch_dir=None):
    from asof.serde import ContractError, encode
    from asof.journal import inspect_run
    from tether import _presentation as presentation
    stage, checked = 'descriptor', []
    result = dict(schema_version=1, control_id=descriptor.get('control_id') if type(descriptor) is dict else None,
                  decision='error', stage=stage, violated_obligations=[],
                  checked_scope=checked, observables={})
    try:
        _descriptor_contract(descriptor)
        operation, variant = descriptor.get('operation'), descriptor.get('variant')
        if operation not in ('prepare_run', 'verify_run', 'inspect_run') or variant not in ('core_v2_catalog1', 'artifact_policy_v2'):
            raise ContractError('Unknown benchmark operation/variant')
        checked.append('descriptor')
        stage = operation
        if operation == 'prepare_run':
            observed = _policy_prepare(root, descriptor, scratch_dir=scratch_dir) if variant == 'artifact_policy_v2' else _core_prepare(root, descriptor)
        else:
            run_dir = _path(root, descriptor['paths'], 'run_dir')
            outer = any((run_dir / name).exists() for name in
                        (presentation.RECEIPT, presentation.MANIFEST, presentation.FAILURE, 'attempt'))
            if operation == 'verify_run':
                from asof.serde import read_json
                policy_present = outer and read_json(run_dir / presentation.MANIFEST).get('artifact_policy') is not None
                if (variant == 'artifact_policy_v2') != bool(policy_present):
                    raise ContractError('Requested comparison variant differs from sealed artifact policy scope')
                if not outer:
                    if read_json(run_dir / 'receipt.json').get('schema_version') == 1:
                        result.update(decision='unsupported', stage=stage,
                            reason='Legacy v1 receipt-only interface is outside current-v2 semantic comparison')
                        return result
                anchor = descriptor.get('anchors', {}).get('receipt_sha256')
                verification = (presentation.verify_outer(run_dir, anchor) if outer else
                                presentation.verify_engine(run_dir, anchor, True))
                observed = _verified_observations(run_dir / 'engine' if outer else run_dir)
                observed['verification'] = verification
                observed['code_matches_current'] = verification.get('engine', verification).get('code_matches_current')
            else:
                if not outer:
                    presentation.preflight_run_journals(run_dir)
                observed = dict(recovery=encode(presentation.inspect_outer(run_dir) if outer else inspect_run(run_dir)))
        checked.append(operation)
        result.update(decision='inspect_only' if operation == 'inspect_run' else 'accept', observables=observed)
    except ContractError as error:
        result.update(decision='reject', reason=str(error), error_class=type(error).__name__)
    except (FileNotFoundError, IsADirectoryError, NotADirectoryError) as error:
        result.update(decision='reject', reason=str(error), error_class=type(error).__name__)
    except Exception as error:
        # An unexpected implementation exception is not a successful rejection.
        result.update(decision='error', reason=str(error), error_class=type(error).__name__)
    result['stage'] = stage
    return encode(result)


def materialize_core(root, descriptor, producer):
    """Run a fictional producer once; never used during scored validation."""
    from asof.agents import ExtractiveBackend, ReplayBackend, Selection, Usage, make_request
    from asof.artifacts import write_run
    from asof.chrono import load_snapshot
    from asof.contracts import Case, Category, EvidenceStatus
    from asof.journal import RunJournal
    from asof.scorer import ScorerArtifact
    from asof.serde import decode, read_json, write_json, fingerprint
    from asof.workflow import BackendFailure, run_workflow
    paths = descriptor['paths']
    budget, disabled, review, backend, _ = _configuration(root, descriptor)
    case = decode(Case, read_json(_path(root, paths, 'case')))
    store = load_snapshot(_path(root, paths, 'snapshot'), case, _path(root, paths, 'catalog'))
    model = decode(ScorerArtifact, read_json(_path(root, paths, 'scorer'))) if paths.get('scorer') else None
    if producer == 'valid_recorded':
        responses = {}
        for category in Category:
            records = tuple(r for r in store.query(case, category) if r.observation.status == EvidenceStatus.OBSERVED)
            if records:
                request = make_request(case, category, records)
                responses[category.value] = [dict(request_sha256=fingerprint(request),
                    selection=Selection(tuple(r.observation.observation_id for r in records), Usage(0, 0, 0)))]
        replay_path = root / 'input/materialized-replay.json'
        write_json(replay_path, dict(schema_version=2, responses=responses))
        backend = ReplayBackend(replay_path)
    elif producer.startswith('local_'):
        from asof.local_model import LocalSelectionBackend
        if not isinstance(backend, LocalSelectionBackend):
            raise RuntimeError('Local corpus recipe requires explicit native configuration')

        class FixtureTransport:
            def open(self, http, timeout):
                payload = json.loads(http.data)
                output = payload['json_schema']['properties']['observation_ids']
                selected = output['items']['enum'][:output['maxItems']]
                response = dict(truncated=False, tokens_evaluated=1, tokens_predicted=1,
                    content=json.dumps(dict(observation_ids=selected)))
                if producer == 'local_malformed_response':
                    response['content'] = 'not-json (intentional fixture)'
                elif producer == 'local_known_overquote':
                    response['tokens_predicted'] = backend.max_output + 1
                elif producer != 'local_valid':
                    raise RuntimeError('Undeclared local fixture recipe')
                return io.BytesIO(json.dumps(response).encode('utf-8'))
        backend.opener = FixtureTransport()
    elif producer not in ('valid_scored', 'offline', 'unresolved_dispatch'):
        class FixtureBackend:
            backend_id = 'bg02-fictional-scripted-v1'
            provenance = dict(kind='fictional_no_network', recipe=producer)

            def quote(self, request):
                return Usage(1, 1, 0)

            def select(self, request):
                if producer == 'known_overquote':
                    raise BackendFailure('Fictional measured over-reservation', Usage(2, 2, 0))
                if producer == 'unknown_timeout':
                    raise TimeoutError('Fictional timeout; no request was sent')
                if producer == 'malformed_usage':
                    return Selection((), Usage(-1, 0, 0))
                if producer == 'unknown_selection':
                    return Selection(('fictional-not-admitted',), Usage(1, 1, 0))
                if producer == 'duplicate_selection':
                    key = request.evidence[0].observation_id
                    return Selection((key, key), Usage(1, 1, 0))
                raise RuntimeError('Undeclared materializer recipe: ' + producer)
        backend = FixtureBackend()
    output = root / 'run'
    journal = RunJournal(output)
    try:
        write_json(output / 'request.json', dict(case=case, snapshot=store.snapshot, scorer=model,
            budget=budget, disabled=disabled, review_enabled=review, catalog_policy=store.catalog_policy,
            backend_provenance=getattr(backend, 'provenance', None)))
        journal.append('inputs_archived', request_sha256=fingerprint(read_json(output / 'request.json')))
        if producer == 'unresolved_dispatch':
            records = tuple(r for r in store.query(case, Category.GENETICS) if r.observation.status == EvidenceStatus.OBSERVED)
            request = make_request(case, Category.GENETICS, records)
            # A crash after durable dispatch has no final receipt/selection.
            journal.append('dispatch', category=Category.GENETICS, attempt=1, attempt_id='genetics:1',
                           request_sha256=fingerprint(request), reserved=Usage(2, 3, 0))
            digest = None
        else:
            result = run_workflow(case, store, backend, model, budget, disabled, review, journal)
            if hasattr(backend, 'records'):
                write_json(output / 'backend-execution.json', dict(schema_version=1, attempts=backend.records))
            digest = write_run(output, result, store, model, journal)
    finally:
        journal.close()
    descriptor['paths']['run_dir'] = 'run'
    if digest is not None:
        descriptor.setdefault('anchors', {})['receipt_sha256'] = digest
    descriptor['paths'] = {key: value for key, value in descriptor['paths'].items() if key in ('run_dir', 'trusted_runtime')}
    descriptor['operation'] = 'inspect_run' if producer == 'unresolved_dispatch' else 'verify_run'
    descriptor['options'] = {}
    return descriptor


def materialize_outer(root, descriptor):
    from tether._presentation import create_outer
    paths = descriptor['paths']
    budget, disabled, review, _, limits = _configuration(root, descriptor)
    output = root / 'run'
    argv = ['run', '--output', str(output)]
    for key in ('case', 'snapshot', 'catalog', 'scorer', 'replay', 'local_model'):
        if paths.get(key):
            argv += ['--' + key.replace('_', '-'), str(_path(root, paths, key))]
    for name in ('max_calls', 'max_input_tokens', 'max_output_tokens', 'max_cost_usd', 'max_seconds', 'max_retries'):
        argv += ['--' + name.replace('_', '-'), str(getattr(budget, name))]
    for category in disabled:
        argv += ['--disable', category.value]
    if not review:
        argv += ['--no-review-retries']
    request = None
    if descriptor['variant'] == 'artifact_policy_v2':
        request = _policy_request(root, descriptor)
        argv += ['--catalog-policy', str(request.policy_path), '--policy-roots', str(request.roots_path),
                 '--policy-use', request.use_id, '--policy-frame-sha256', request.frame_sha256]
    result = create_outer(output, argv, limits=limits, policy_request=request)
    descriptor['paths']['run_dir'] = 'run'
    descriptor.setdefault('anchors', {})['receipt_sha256'] = result['receipt_sha256']
    descriptor['paths'] = {key: value for key, value in descriptor['paths'].items() if key in ('run_dir', 'trusted_runtime')}
    descriptor['operation'] = 'verify_run'
    descriptor['options'] = {}
    descriptor['anchors'] = {'receipt_sha256': result['receipt_sha256']}
    return descriptor


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path)
    parser.add_argument('--descriptor', type=Path)
    parser.add_argument('--materialize', help='Explicit unscored native producer recipe')
    parser.add_argument('--identity', action='store_true')
    parser.add_argument('--trusted-runtime', type=Path, help='Qualified installed wheel directory')
    args = parser.parse_args()
    if args.trusted_runtime:
        answer = trusted_runtime(args.trusted_runtime)
    elif args.identity:
        answer = runtime_identity()
    else:
        descriptor = json.loads(args.descriptor.read_bytes())
        answer = (materialize_outer(args.root, descriptor) if args.materialize in ('valid_outer_schema1', 'valid_outer_policy') else
                  materialize_core(args.root, descriptor, args.materialize) if args.materialize else
                  validate_bundle(args.root, descriptor))
    print(json.dumps(answer, ensure_ascii=False, allow_nan=False))


if __name__ == '__main__':
    main()
