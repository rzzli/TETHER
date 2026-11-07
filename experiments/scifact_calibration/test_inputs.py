"""Invented source-preservation controls; production references are never opened."""
import copy
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tether_engine.serde import canonical, parse_json, ContractError
from experiments.scifact.tests.test_scifact_data_views import write_tar, acquisition
from experiments.scifact.data_views import prepare_release


ROOT = Path(__file__).resolve().parents[2]


def proof(path):
    raw = Path(path).read_bytes()
    return dict(path=str(Path(path).resolve()), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def write(path, value):
    path.write_bytes(canonical(value) + b'\n')
    return proof(path)


def fixture(root):
    """Use the maintained producer only to author an independent-reader fixture."""
    archive = write_tar(root/'scifact-data.tar.gz')
    source = acquisition(root, archive)
    prepared = root/'prepared'
    prepare_release(source, prepared)
    manifest = parse_json((prepared/'manifest.json').read_bytes())
    projectors = []
    old_name = bytes((97, 115, 111, 102)).decode()
    for name in ('data_views.py', 'split.py'):
        current = ROOT/'experiments/scifact'/name
        archived = root/('archived-'+name)
        archived.write_bytes(current.read_bytes().replace(b'from tether_engine.', ('from '+old_name+'.').encode()))
        manifest['source_pins'][str(current)] = proof(archived)['sha256']
        projectors.append(dict(logical_path='experiments/scifact/'+name, historical=proof(archived), current=proof(current)))
    manifest_proof = write(prepared/'manifest.json', manifest)
    report = parse_json((prepared/'build-report.json').read_bytes())
    report['manifest_sha256'] = manifest_proof['sha256']; write(prepared/'build-report.json', report)
    rows = [parse_json(x) for x in (prepared/'journal.jsonl').read_bytes().splitlines()]
    previous = None
    for row in rows:
        row.pop('sha256'); row['previous_sha256'] = previous
        if row['event'] == 'build_completed': row['details']['manifest_sha256'] = manifest_proof['sha256']
        previous = hashlib.sha256(canonical(row)).hexdigest(); row['sha256'] = previous
    (prepared/'journal.jsonl').write_bytes(b''.join(canonical(x)+b'\n' for x in rows))
    split = parse_json((prepared/'restricted/split.json').read_bytes())
    frame = dict(schema_version=1, kind='sc05_preparation_transition_v1', purpose='calibrate',
        original_repository_root=str(ROOT), manifest=manifest_proof, archive=proof(archive),
        acquisition=proof(source), archive_receipt=proof(archive.with_suffix('.receipt.json')),
        journal=proof(prepared/'journal.jsonl'), build_report=proof(prepared/'build-report.json'),
        projectors=projectors, expected_counts=manifest['counts'],
        expected_partitions=manifest['split_counts'], expected_calibration_ids=split['partitions']['calibration'])
    path = root/'transition.json'; write(path, frame)
    return path, frame, prepared


class TransitionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path, self.frame, self.prepared = fixture(self.root)

    def verify(self, **kwargs):
        from experiments.scifact_calibration.inputs import verify_preparation_transition
        return verify_preparation_transition(self.path, proof(self.path)['sha256'], **kwargs)

    def test_independent_projection_and_exact_purpose(self):
        with (patch('experiments.scifact.data_views.verify_preparation', side_effect=AssertionError('producer verifier')),
              patch('experiments.scifact.data_views.load_archive', side_effect=AssertionError('producer parser'))):
            result = self.verify()
        self.assertEqual(result.calibration_ids, tuple(self.frame['expected_calibration_ids']))
        self.assertTrue(all(set(q) == {'id','claim'} for q in result.queries))
        self.assertTrue(all(set(d) == {'doc_id','title','abstract'} for d in result.corpus))
        with self.assertRaises(TypeError): result.queries[0]['claim'] = 'changed'

    def test_wrong_purpose_fails_before_file_open(self):
        from experiments.scifact_calibration.inputs import verify_preparation_transition
        with patch.object(Path, 'open', side_effect=AssertionError('opened before purpose')):
            with self.assertRaises(ContractError): verify_preparation_transition(self.path, '0'*64, purpose='predict')

    def test_external_anchor_and_archived_source_are_required(self):
        from experiments.scifact_calibration.inputs import verify_preparation_transition
        with self.assertRaises(ContractError): verify_preparation_transition(self.path, '0'*64)
        Path(self.frame['projectors'][0]['historical']['path']).write_bytes(b'changed')
        with self.assertRaises(ContractError): self.verify()

    def test_changed_product_and_added_orphan_are_rejected(self):
        path=self.prepared/'views/queries_calibration.jsonl'; original=path.read_bytes()
        path.write_bytes(original+b'{}\n')
        with self.assertRaises(ContractError): self.verify()
        path.write_bytes(original); (self.prepared/'orphan.json').write_bytes(b'{}')
        with self.assertRaises(ContractError): self.verify()

    def test_reanchored_role_laundering_and_schedule_change_fail(self):
        self.frame['expected_calibration_ids'].reverse(); write(self.path,self.frame)
        with self.assertRaises(ContractError): self.verify()

    def test_reanchored_reference_permission_laundering_fails(self):
        path=self.prepared/'manifest.json';manifest=parse_json(path.read_bytes())
        manifest['products']['references_calibration']['purposes'].append('predict')
        self.frame['manifest']=write(path,manifest);write(self.path,self.frame)
        with self.assertRaisesRegex(ContractError,'purpose'):self.verify()

    def test_empty_orphan_directory_is_not_original_membership(self):
        (self.prepared/'unrecorded').mkdir()
        with self.assertRaises(ContractError):self.verify()

    def test_boolean_count_is_not_integer_schedule_authority(self):
        self.frame['expected_counts']['dev']=True;write(self.path,self.frame)
        with self.assertRaises(ContractError):self.verify()

    def test_source_transition_rejects_executable_changes(self):
        entry=self.frame['projectors'][0]; p=Path(entry['historical']['path'])
        p.write_bytes(p.read_bytes()+b'\nraise RuntimeError("must never execute")\n')
        entry['historical']=proof(p); write(self.path,self.frame)
        with self.assertRaises(ContractError): self.verify()

    def test_proof_parsing_uses_the_captured_bytes(self):
        from experiments.scifact_calibration import inputs
        original=inputs.capture
        reads=[]
        def captured(p,*a,**kw):
            raw=original(p,*a,**kw); reads.append(p['path'])
            if p['path']==str(self.path): self.path.write_bytes(b'{}')
            return raw
        with patch.object(inputs,'capture',side_effect=captured):
            result=self.verify()
        self.assertEqual(result.calibration_ids,tuple(self.frame['expected_calibration_ids']))
        self.assertEqual(reads.count(str(self.path)),1)


if __name__ == '__main__': unittest.main()
