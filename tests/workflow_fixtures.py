"""Invented comparison workflows and responses, not TestCase dependencies."""
from dataclasses import replace
import io
from pathlib import Path
import shutil
import tempfile

from tether_engine.chrono import load_snapshot
from tether_engine.contracts import Case, Category
from tether_engine.serde import canonical, decode, fingerprint, parse_json, read_json, sha256_file, write_json
from tether_engine.workflow import Budget
from tools.science.role_backend import RoleSelectionBackend
from tools.science.comparison_workflow import STAGES, run_case, verify_case, _seal


ROOT = Path(__file__).resolve().parents[1]


class NativeFixture:
    def __init__(self, error=None, malformed=False, take=1):
        self.calls = []
        self.error = error
        self.malformed = malformed
        self.take = take

    def open(self, request, timeout):
        self.calls.append(request.data)
        if self.error:
            raise self.error
        import json
        payload = json.loads(request.data)
        ids = payload['json_schema']['properties']['observation_ids']['items']['enum'][:min(self.take,payload['json_schema']['properties']['observation_ids']['maxItems'])]
        return io.BytesIO(canonical({'content': '{broken' if self.malformed else json.dumps({'observation_ids': ids}),
            'tokens_evaluated': 10, 'tokens_predicted': 5, 'truncated': False}))


def synthetic_policy():
    return {'schema_version': 1, 'stage_order': list(STAGES), 'control_reserve_bytes': 2048,
        'output_constraint_policy':'native_json_schema_reviewed_subset_v1',
        'stage_guidance': {s: 'Fixture role ' + s + ': select only provided source IDs.' for s in STAGES},
        'specialists': {c.value: 'fixture-specialist' for c in Category}, 'scope': 'Synthetic test only'}


class ComparisonWorkflowFixture:
    def prepare(self, add_cleanup):
        self.temp = tempfile.TemporaryDirectory(); add_cleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.fixture = self.root/'input'
        shutil.copytree(ROOT/'src/tether_engine/demo/v2', self.fixture)
        packet = read_json(self.fixture/'evidence.json')
        packet['observations'] = [r for r in packet['observations'] if r['category'] == 'genetics']
        for row in packet['observations']:
            row['features'] = {}
        write_json(self.fixture/'evidence.json', packet)
        snapshot = read_json(self.fixture/'snapshot.json')
        snapshot['artifacts'][0]['sha256'] = sha256_file(self.fixture/'evidence.json')
        write_json(self.fixture/'snapshot.json', snapshot)
        self.case = replace(decode(Case, read_json(self.fixture/'case.json')), task='T6', endpoint=None)
        self.store = load_snapshot(self.fixture/'snapshot.json', self.case)
        self.policy = synthetic_policy()
        self.config = {'schema_version':1,'endpoint':'http://127.0.0.1:55581','model_id':'synthetic-only',
            'model_provenance':{'weights_sha256':{'fixture':'a'*64},'runtime_sha256':'b'*64},
            'retrieval':{'max_records':12,'max_request_bytes':12000,'wire_format':'tether-shared-scientific-fields-v1'},
            'max_output_tokens':256,'timeout_seconds':2,'seed':123}
        self.config_path = self.root/'config.json'; write_json(self.config_path,self.config)

    def backend(self, **options):
        backend = RoleSelectionBackend(self.config_path)
        backend.opener = NativeFixture(**options)
        return backend

    def run_arm(self, arm='tether', backend=None, **budget):
        backend = backend or self.backend()
        output = self.root/('run-'+arm)
        result = run_case(self.case,self.store,backend,Budget(**budget),arm,output,self.policy)
        return result, output, backend

    def verify(self, out):
        return verify_case(out,self.case,self.store,self.config,self.policy)

    def rebind(self, out, event_change=None):
        events=[parse_json(line) for line in (out/'journal.jsonl').read_bytes().splitlines()]
        previous=None
        for event in events:
            if event_change: event_change(event)
            if event['event']=='comparison_finalized':
                event['details']['result_sha256']=sha256_file(out/'result.json')
            event['previous_sha256']=previous
            event.pop('sha256')
            event['sha256']=fingerprint(event);previous=event['sha256']
        (out/'journal.jsonl').write_bytes(b'\n'.join(canonical(e) for e in events)+b'\n')
        _seal(out)
