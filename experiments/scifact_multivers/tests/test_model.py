"""Fictional tensor/state tests; run only in the qualified isolated runtime."""
import argparse
import hashlib
import tempfile
from pathlib import Path
import unittest

import torch
from transformers import LongformerConfig

from experiments.scifact_multivers.contracts import ContractError
from experiments.scifact_multivers.model import MultiVerS, decode, load_state_strict
from experiments.scifact_multivers.checkpoint import load_checkpoint_state


def tiny_config():
    return LongformerConfig(vocab_size=31, hidden_size=16, num_hidden_layers=1,
                            num_attention_heads=4, intermediate_size=32,
                            max_position_embeddings=66, attention_window=[8],
                            hidden_dropout_prob=0.1, attention_probs_dropout_prob=0.1)


def temporary_directory():
    scratch = Path(__file__).resolve().parents[3] / 'data/cache/scifact-multivers-unit-temp'
    scratch.mkdir(parents=True, exist_ok=True)
    return tempfile.TemporaryDirectory(dir=scratch)


class ModelTests(unittest.TestCase):
    def test_native_keys_and_strict_missing_extra_and_shape_checks(self):
        model = MultiVerS(tiny_config()).eval()
        state = model.state_dict()
        self.assertEqual(state['label_classifier._linear_layers.1.weight'].shape, (3, 16))
        self.assertEqual(state['rationale_classifier._linear_layers.0.weight'].shape, (16, 32))
        self.assertIn('encoder.embeddings.position_ids', state)
        load_state_strict(model, state)
        for mutate in ('missing', 'extra', 'shape', 'nan', 'positions'):
            changed = {k: v.clone() for k, v in state.items()}
            if mutate == 'missing': del changed['encoder.pooler.dense.weight']
            elif mutate == 'extra': changed['unexpected.weight'] = torch.ones(1)
            elif mutate == 'shape': changed['label_classifier._linear_layers.1.weight'] = torch.ones(4, 16)
            elif mutate == 'nan': changed['encoder.pooler.dense.weight'][0, 0] = float('nan')
            else: changed['encoder.embeddings.position_ids'][0, 1] = 99
            with self.subTest(mutate=mutate), self.assertRaises(ContractError):
                load_state_strict(model, changed)

    def test_forward_joint_logits_shapes_and_full_input(self):
        torch.manual_seed(76)
        model = MultiVerS(tiny_config()).eval()
        ids = torch.tensor([[0, 9, 2, 10, 2, 11, 12, 2]])
        inputs = {'input_ids': ids, 'attention_mask': torch.ones_like(ids),
                  'global_attention_mask': torch.tensor([[1, 1, 1, 0, 1, 0, 0, 1]])}
        with torch.inference_mode():
            output = model(inputs, torch.tensor([[4, 7]]))
        self.assertEqual(output['label_logits'].shape, (1, 3))
        self.assertEqual(output['rationale_logits'].shape, (1, 2))
        self.assertTrue(torch.isfinite(output['label_logits']).all())

    def test_release_empty_rationale_threshold_equality_and_sentence_order(self):
        batch = {'claim_id': torch.tensor([1, 2, 3]), 'abstract_id': torch.tensor([10, 11, 12]),
                 'abstract_sent_idx': torch.tensor([[3, 6, 8], [3, 6, 0], [3, 6, 0]])}
        output = {'predicted_labels': torch.tensor([2, 0, 1]),
                  'predicted_rationales': torch.tensor([[0, 0, 0], [1, 1, 1], [1, 0, 0]]),
                  'rationale_probs': torch.tensor([[.1, .2, .3], [.5, .9, 1.], [.9, .1, 1.]]),
                  'label_probs': torch.tensor([[.1, .1, .8], [.8, .1, .1], [.1, .8, .1]])}
        rows = decode(output, batch)
        self.assertEqual(rows[0]['predicted_rationale'], [])
        self.assertEqual(rows[1]['predicted_rationale'], [0, 1])
        self.assertEqual(rows[2]['predicted_label'], 'NEI')
        forced = decode(output, batch, force_rationale=True)
        self.assertEqual(forced[0]['predicted_rationale'], [2])

    def test_forward_includes_rationale_at_exact_half_probability(self):
        model = MultiVerS(tiny_config()).eval()
        with torch.no_grad():
            for parameter in model.rationale_classifier.parameters():
                parameter.zero_()
        ids = torch.tensor([[0, 9, 2, 10, 2, 11, 12, 2]])
        inputs = {'input_ids': ids, 'attention_mask': torch.ones_like(ids),
                  'global_attention_mask': torch.tensor([[1, 1, 1, 0, 1, 0, 0, 1]])}
        with torch.inference_mode():
            output = model(inputs, torch.tensor([[4, 7]]))
        self.assertEqual(output['rationale_probs'].tolist(), [[0.5, 0.5]])
        self.assertEqual(output['predicted_rationales'].tolist(), [[1, 1]])

    def test_checkpoint_safe_namespace_and_optimizer_omission(self):
        with temporary_directory() as name:
            path = Path(name)/'fictional.ckpt'
            state = MultiVerS(tiny_config()).state_dict()
            torch.save({'state_dict': state, 'hyper_parameters': {'hparams': argparse.Namespace(num_labels=3)},
                        'optimizer_states': [{'state': {'fictional': torch.ones(7)}}]}, path)
            raw = path.read_bytes()
            got, metadata = load_checkpoint_state(path, expected_sha256=hashlib.sha256(raw).hexdigest(), expected_bytes=len(raw))
            self.assertEqual(set(got), set(state))
            self.assertEqual(metadata['hparams']['num_labels'], 3)
            self.assertNotIn('optimizer_states', got)
            with self.assertRaises(ContractError):
                load_checkpoint_state(path, expected_sha256='0'*64, expected_bytes=len(raw))

    def test_checkpoint_unknown_global_rejected_without_fallback(self):
        with temporary_directory() as name:
            path = Path(name)/'fictional.ckpt'
            torch.save({'state_dict': {}, 'unexpected': Path('fictional')}, path)
            raw = path.read_bytes()
            with self.assertRaisesRegex(ContractError, 'global'):
                load_checkpoint_state(path, expected_sha256=hashlib.sha256(raw).hexdigest(), expected_bytes=len(raw))


if __name__ == '__main__':
    unittest.main()
