import json
import hashlib
from pathlib import Path
import tempfile
import unittest

from tools.feasibility.render_outcome_review import render


class OutcomeReviewTests(unittest.TestCase):
    def fixture(self, root):
        origin = root / 'origin'; origin.mkdir()
        case = {'candidate_id': 'P01', 'drug_anchor': 'drug', 'target_anchor': 'target',
                'origin_record': {'nct_id': 'NCT12345678'}}
        (origin / 'selected.json').write_text(json.dumps([case]))
        (root / 'outcome-protocol.json').write_text(json.dumps({'selection_sha256': hashlib.sha256((origin / 'selected.json').read_bytes()).hexdigest()}))
        (root / 'review-notes.json').write_text(json.dumps({'cases': [{'candidate_id': 'P01', 'source_ids': ['source'],
            'review_disposition': 'unresolved', 'finding': 'No label', 'timing_note': 'Unknown', 'endpoint_result': None}]}))
        for folder in ('primary-source-receipts', 'supplemental-source-receipts'):
            (root / folder).mkdir()
            (root / folder / 'index.json').write_text('[]')
        body = root / 'primary-source-receipts/source.body'; body.write_bytes(b'<p>source</p>')
        (root / 'primary-source-receipts/index.json').write_text(json.dumps([{'source_id': 'source', 'url': 'https://example.org/',
            'status': 'retrieved_unreviewed', 'sha256': hashlib.sha256(body.read_bytes()).hexdigest()}]))
        return origin, body

    def test_retained_source_cannot_disappear(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); origin, body = self.fixture(root)
            body.unlink()
            with self.assertRaises(ValueError): render(root, origin, root / 'out')

    def test_content_qualifications_are_bound_to_notes_receipts_and_body(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); origin, body = self.fixture(root)
            digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
            review = {'review_notes_sha256':digest(root/'review-notes.json'), 'sources':[
                {'source_id':'source','body_sha256':digest(body),
                 'index_sha256':digest(root/'primary-source-receipts/index.json'),
                 'display_label':'Publication metadata and abstract reviewed'}]}
            path = root/'source-content-review.json'; path.write_text(json.dumps(review))
            result = render(root,origin,root/'good')
            self.assertEqual(result['source_content_review_sha256'],digest(path))
            self.assertIn('Publication metadata and abstract reviewed',(root/'good/Review.html').read_text(encoding='utf-8'))
            review['sources'][0]['body_sha256']='0'*64
            path.write_text(json.dumps(review))
            with self.assertRaisesRegex(ValueError,'Content qualification'):
                render(root,origin,root/'bad')
            self.assertFalse((root/'bad').exists())

    def test_optional_timeline_requires_same_cases_and_sealed_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); origin, body = self.fixture(root)
            timeline = root / 'timeline'; timeline.mkdir()
            rows = [{'candidate_id': 'P01', 'nct_id': 'NCT12345678', 'observations': [
                {'snapshot_date': '2023-01-01', 'record': {'overall_status': 'Recruiting', 'phase': 'Phase 2'}}]}]
            path = timeline / 'timeline.json'; path.write_text(json.dumps(rows))
            (timeline / 'evidence-manifest.json').write_text(json.dumps({'files': [{'path': 'timeline.json',
                'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'bytes': path.stat().st_size}]}))
            result = render(root, origin, root / 'good', timeline)
            self.assertEqual(result['registry_timeline_cases'], 1)
            self.assertIn('Recruiting', (root / 'good/Review.html').read_text(encoding='utf-8'))
            path.write_text('[]')
            with self.assertRaises(ValueError): render(root, origin, root / 'bad', timeline)
