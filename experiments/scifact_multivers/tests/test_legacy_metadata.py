"""Restricted loading of inert legacy trainer metadata; no Lightning import."""
import argparse
import contextlib
import hashlib
from pathlib import Path
import sys
import types
import unittest
import torch
from experiments.scifact_multivers.checkpoint import load_checkpoint_state
from experiments.scifact_multivers.contracts import ContractError
from experiments.scifact_multivers.tests.test_model import temporary_directory


@contextlib.contextmanager
def legacy_globals():
    names = ['pytorch_lightning', 'pytorch_lightning.callbacks',
             'pytorch_lightning.callbacks.model_checkpoint', 'pytorch_lightning.utilities',
             'pytorch_lightning.utilities.argparse']
    previous = {name: sys.modules.get(name) for name in names}
    for name in names:
        sys.modules[name] = types.ModuleType(name)
    callback = type('ModelCheckpoint', (), {'__module__': names[2]})
    sys.modules[names[2]].ModelCheckpoint = callback
    def default():
        raise AssertionError('Original trainer function must never execute')
    default.__name__ = default.__qualname__ = '_gpus_arg_default'
    default.__module__ = names[4]
    sys.modules[names[4]]._gpus_arg_default = default
    try:
        yield callback, default
    finally:
        for name, old in previous.items():
            if old is None: sys.modules.pop(name, None)
            else: sys.modules[name] = old


class LegacyMetadataTests(unittest.TestCase):
    def fixture(self, path, *, invoke=False, invoke_callback=False, field='tpu_cores'):
        with legacy_globals() as (callback, default):
            class Invocation:
                def __reduce__(self): return default, ()
            value = callback() if invoke_callback else Invocation() if invoke else default
            torch.save({'state_dict': {'weight': torch.ones(2)},
                        'callbacks': {callback: {'monitor': 'fictional'}},
                        'hyper_parameters': {'hparams': argparse.Namespace(**{field: value})}}, path)
        raw = path.read_bytes()
        return dict(expected_sha256=hashlib.sha256(raw).hexdigest(), expected_bytes=len(raw))

    def test_legacy_markers_are_inert_and_explicitly_recorded(self):
        with temporary_directory() as directory:
            path = Path(directory)/'legacy.pt'; pins = self.fixture(path)
            with self.assertRaises(ContractError): load_checkpoint_state(path, **pins)
            state, report = load_checkpoint_state(path, **pins, allow_legacy_training_metadata=True)
            self.assertEqual(state['weight'].tolist(), [1., 1.])
            self.assertIsNone(report['hparams']['tpu_cores'])
            self.assertIn('tpu_cores', report['ignored_training_metadata'])
            self.assertNotIn('pytorch_lightning', sys.modules)

    def test_metadata_function_cannot_execute_as_reducer(self):
        with temporary_directory() as directory:
            path=Path(directory)/'invoke.pt'; pins=self.fixture(path, invoke=True)
            with self.assertRaises(ContractError):
                load_checkpoint_state(path, **pins, allow_legacy_training_metadata=True)

    def test_marker_in_inference_parameter_is_rejected(self):
        with temporary_directory() as directory:
            path=Path(directory)/'wrong-field.pt'; pins=self.fixture(path, field='num_labels')
            with self.assertRaises(ContractError):
                load_checkpoint_state(path, **pins, allow_legacy_training_metadata=True)

    def test_metadata_callback_cannot_be_constructed(self):
        with temporary_directory() as directory:
            path=Path(directory)/'construct.pt'; pins=self.fixture(path, invoke_callback=True)
            with self.assertRaises(ContractError):
                load_checkpoint_state(path, **pins, allow_legacy_training_metadata=True)
