"""Independent archived-source numerical controls, with fictional tiny weights."""
import copy
from pathlib import Path, PureWindowsPath
import hashlib
import json
import unittest

import torch

from experiments.scifact_multivers.model import MultiVerS, decode, load_state_strict
from experiments.scifact_multivers.reference import build_reference, RECEIPTS
from tools.history import read_checkpoint
from experiments.scifact_multivers.tests.test_model import tiny_config


class ReferenceTests(unittest.TestCase):
    def test_full_original_encoder_and_both_heads_agree_on_padded_global_context(self):
        # Re-read exact upstream bytes from immutable history. This preserves
        # source-math comparison without pretending old absolute paths moved.
        prefix = 'planning/review-assets/tether-semantic-20261106/solver-feasibility'
        sources = {}
        for name, expected in RECEIPTS.items():
            raw = read_checkpoint(prefix+'/'+name)
            self.assertEqual(hashlib.sha256(raw).hexdigest(), expected)
            for row in json.loads(raw)['files']:
                parts = PureWindowsPath(row.get('local_path', row['path'])).parts
                marker = tuple((prefix+'/source').split('/'))
                matches = [i for i in range(len(parts)) if tuple(parts[i:i+len(marker)]) == marker]
                self.assertEqual(len(matches), 1)
                relative = '/'.join(parts[matches[0]+len(marker):])
                content = read_checkpoint(prefix+'/source/'+relative)
                self.assertEqual(len(content), row['bytes'])
                self.assertEqual(hashlib.sha256(content).hexdigest(), row['sha256'])
                sources[relative] = content.decode('utf-8')
        torch.manual_seed(76)
        config = tiny_config()
        modern = MultiVerS(config).eval()
        reference, reference_decode = build_reference(copy.deepcopy(config), sources)
        load_state_strict(reference, modern.state_dict())
        reference.eval()
        batch = {'tokenized': {'input_ids': torch.tensor([[0, 9, 2, 10, 2, 11, 12, 2, 13, 2, 1],
                                                        [0, 9, 10, 2, 11, 2, 1, 1, 1, 1, 1]]),
                               'attention_mask': torch.tensor([[1]*10+[0], [1]*6+[0]*5]),
                               'global_attention_mask': torch.tensor([[1,1,1,0,1,0,0,1,0,1,0],
                                                                       [1,1,1,1,0,1,0,0,0,0,0]])},
                 'abstract_sent_idx': torch.tensor([[7,9], [5,0]]),
                 'claim_id': torch.tensor([1,2]), 'abstract_id': torch.tensor([10,11])}
        with torch.inference_mode():
            a = modern(batch['tokenized'], batch['abstract_sent_idx'])
            b = reference(batch['tokenized'], batch['abstract_sent_idx'])
        for key in ('label_logits', 'rationale_logits', 'label_probs', 'rationale_probs'):
            torch.testing.assert_close(a[key], b[key], atol=1e-5, rtol=1e-4)
        actual = decode(a, batch)
        original = reference_decode(b, batch)
        for x,y in zip(actual,original):
            for key in ('claim_id','abstract_id','predicted_label','predicted_rationale'):
                self.assertEqual(x[key],y[key])


if __name__ == '__main__':
    unittest.main()
