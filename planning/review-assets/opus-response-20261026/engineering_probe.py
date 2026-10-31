"""Read-only synthetic reproduction of selected Opus review findings."""
import json
import sys
from dataclasses import replace
from pathlib import Path
from urllib.error import URLError

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'src'))
from asof.agents import EvidenceView, SpecialistRequest, ExtractiveBackend
from asof.artifacts import write_run
from asof.chrono import load_snapshot, observation_exclusion, EvidenceStore
from asof.contracts import Case, Category, Observation
from asof.local_model import parse_selection, selection_payload
from asof.provenance import InputGraph
from asof.retrieval import RetrievalPolicy, bounded_request
from asof.serde import decode, read_json, encode
from asof.workflow import run_workflow

fixture = ROOT / 'src/asof/demo/v2'
case = decode(Case, read_json(fixture/'case.json'))
store = load_snapshot(fixture/'snapshot.json', case)
graph = InputGraph(store.snapshot, fixture, None)
observation = decode(Observation, read_json(fixture/'evidence.json')['observations'][0])
same_year = replace(observation, publication_year=case.origin.year, publication_date=None)
later_exact = replace(same_year, publication_date=case.origin.replace(month=12, day=31))
report = {'fixture_only': True, 'no_model_or_network_calls': True}
report['C1'] = {
    'same_year_exclusion': observation_exclusion(same_year, store.snapshot.artifacts[0], graph, case),
    'later_exact_date_exclusion': observation_exclusion(later_exact, store.snapshot.artifacts[0], graph, case),
    'qualification': 'Synthetic fixture with independently eligible old availability; proves permissive year gate, not a real leakage event.'}

class Failure(ExtractiveBackend):
    def __init__(self, error): self.error = error
    def select(self, request): raise self.error

for name, error in [('URLError', URLError('fixture only')), ('TimeoutError', TimeoutError('fixture only'))]:
    result = run_workflow(case, store, Failure(error))
    report.setdefault('C2', {})[name] = {'status': result.status, 'calls': result.calls,
        'estimated_input_tokens': result.estimated_usage.input_tokens,
        'categories': {key: value['status'] for key,value in result.coverage.items()}}
try:
    parse_selection({'truncated': False}, [])
except Exception as error:
    report['C2']['missing_content_error'] = type(error).__name__

policy = RetrievalPolicy(12,64000)
request = SpecialistRequest('{}', Category.GENETICS,
    (EvidenceView('x', 'x'*20000, 'fixture', '{}'),), 'fixture', ())
prepared,audit = bounded_request(request,policy)
try:
    selection_payload(prepared,256,1)
except Exception as error:
    report['C3'] = {'accepted_request_bytes': audit['request_bytes'],
        'retrieval_policy_bytes': policy.max_request_bytes, 'payload_error': str(error)}

direct = EvidenceStore(store.snapshot, tuple(store._records.values()), store.exclusions, store.source_proofs)
result = run_workflow(case,direct,ExtractiveBackend())
try:
    write_run(ROOT/'data/cache/opus-response-code-20261026/should-not-exist',result,direct,None)
except Exception as error:
    report['C7'] = {'has_snapshot_base': hasattr(direct,'snapshot_base'),
        'write_error_class': type(error).__name__, 'write_error': str(error)}
print(json.dumps(report,indent=2))
(Path(__file__).parent/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
