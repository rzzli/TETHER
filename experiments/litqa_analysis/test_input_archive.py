"""Fictional evaluator freezes survive explicit source archives, never fallback."""
from collections import Counter
import copy
from pathlib import Path
import tempfile
import unittest

from experiments.litqa_analysis import inputs, source_archive
from experiments.litqa_analysis.native_records import canonical, digest


class ArchivedInputTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.original_root = self.root / 'original'
        self.archive_root = self.root / 'archive'
        self.archive_root.mkdir()
        self.name = 'experiments/labbench/evaluate.py'
        self.scorer_bytes = b"raise RuntimeError('historical scorer must not execute')\n"
        self.original_scorer = self.original_root / self.name
        self.original_scorer.parent.mkdir(parents=True)
        self.original_scorer.write_bytes(b'# current different bytes\n')
        source = self.write(self.archive_root / 'scorer.py', self.scorer_bytes)
        self.manifest = dict(kind='sc04_analysis_inputs_v1', role='evaluation_only',
            primary_answers_existed_at_freeze=False, questions=199, bootstrap_replicates=10000,
            seed=20261106, created_at_utc='2026-01-01T00:00:00+00:00',
            native_scorer=dict(source, path=str(self.original_scorer)),
            primary_metrics=['raw_accuracy', 'correct_and_admitted_yield'],
            primary_contrasts=['expansion_at_lexical', 'ranking_at_lexical', 'combined_vs_lexical',
                               'interaction', 'marginal_expansion', 'marginal_ranking'])
        for key in ('specification', 'addendum', 'grouping_code', 'freeze_helper'):
            self.manifest[key] = self.write(self.root / key, b'fictional metadata\n')
        original_rows = []
        for i in range(199):
            sources = [f'https://doi.org/10.1234/fictional-{i % 190}']
            if i < 6:
                sources.append(f'https://doi.org/10.1234/fictional-{(i+1) % 190}')
            original_rows.append(dict(id=f'00000000-0000-0000-0000-{i:012d}',
                question=f'Invented experiment {i}?', ideal='Right', distractors=['Wrong'], sources=sources))
        raw = b'\n'.join(canonical(r) for r in original_rows) + b'\n'
        projected = inputs.projection(raw)
        ids = [r['id'] for r in projected['queries']]
        self.manifest['question_schedule'] = ids
        self.manifest['answer_queries'] = self.write_json('queries.json', projected['queries'])
        self.manifest['reference_keys'] = self.write_json('references.json', projected['references'])
        self.manifest['annotation_projection'] = self.write_json('annotation.json', dict(
            role='diagnostic_selection_only', ordinary_retrieval_permitted=False,
            answerer_may_read=False, correct_answers_included=False, key_passages_included=False,
            original=self.write(self.root / 'original.jsonl', raw), schedule=ids,
            products={key: self.write_json(key+'.json', projected[key]) for key in ('hints', 'doi_schedule')}))
        groups = inputs.graph_groups(ids, projected['hints'])
        self.manifest['groups'] = self.write_json('groups.json', dict(
            kind='shared_annotated_doi_connected_components', role='evaluation_only', groups=groups,
            questions=199, components=len(groups),
            size_distribution={str(k): v for k, v in Counter(map(len, groups)).items()}))
        archive_manifest = dict(schema_version=1, kind='sc04_executed_source_archive_v1',
            original_repository_root=str(self.original_root), files={self.name: source})
        proof = self.write(self.archive_root / 'MANIFEST.json', canonical(archive_manifest))
        self.archive = source_archive.load_archive(proof['path'], proof['sha256'],
            {self.name: source['sha256']}, str(self.original_root))

    def write(self, path, raw):
        path.write_bytes(raw)
        return dict(path=str(path), bytes=len(raw), sha256=digest(raw))

    def write_json(self, name, value):
        return self.write(self.root / name, canonical(value))

    def verify(self, **kwargs):
        proof = self.write_json('FROZEN.json', self.manifest)
        return inputs.verify(proof['path'], proof['sha256'],
            answer_started_at='2026-01-02T00:00:00+00:00', **kwargs)

    def test_default_still_rejects_changed_original_scorer(self):
        with self.assertRaises(ValueError):
            self.verify()

    def test_default_still_accepts_original_scorer_without_archive(self):
        self.original_scorer.write_bytes(self.scorer_bytes)
        result = self.verify()
        self.assertEqual(len(result['queries']), 199)
        self.assertNotIn('native_scorer_binding', result)

    def test_explicit_archive_reconstructs_full_original_inputs_without_execution(self):
        result = self.verify(native_scorer_archive=self.archive)
        self.assertEqual(len(result['queries']), 199)
        self.assertEqual(len(result['doi_schedule']), 190)
        self.assertEqual(sum(len(h['dois']) for h in result['hints']), 205)
        self.assertEqual(result['native_scorer_binding']['original'], self.manifest['native_scorer'])
        self.assertEqual(result['native_scorer_binding']['archived'], self.archive.proof(self.name))
        self.assertEqual(result['native_scorer_binding']['archive'], self.archive.manifest_proof)

    def test_wrong_original_path_size_or_digest_fails(self):
        original = copy.deepcopy(self.manifest['native_scorer'])
        for key, value in (('path', str(self.root/'same-bytes.py')), ('bytes', 1), ('sha256', '0'*64)):
            self.manifest['native_scorer'] = dict(original, **{key: value})
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.verify(native_scorer_archive=self.archive)

    def test_changed_archive_payload_fails_without_current_fallback(self):
        self.original_scorer.write_bytes(self.scorer_bytes)
        (self.archive_root / 'scorer.py').write_bytes(b'# changed\n')
        with self.assertRaises(ValueError):
            self.verify(native_scorer_archive=self.archive)

    def test_archive_manifest_is_rechecked_after_loading_the_object(self):
        path = Path(self.archive.manifest_proof['path'])
        original = path.read_bytes()
        for changed in (original + b' ', None):
            if changed is None:
                path.unlink()
            else:
                path.write_bytes(changed)
            with self.subTest(removed=changed is None), self.assertRaises((ValueError, OSError)):
                self.verify(native_scorer_archive=self.archive)

    def test_other_frozen_proofs_remain_exact(self):
        Path(self.manifest['grouping_code']['path']).write_bytes(b'changed grouping')
        with self.assertRaises(ValueError):
            self.verify(native_scorer_archive=self.archive)


if __name__ == '__main__':
    unittest.main()
