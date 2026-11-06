"""Source-level reference assembled from hash-pinned upstream inference code.

This runs archived math on the modern PyTorch runtime. It is not a historical
binary reproduction of torch 1.7.1/tokenizers 0.9.4. Only loading, initialization,
training-framework hooks, and documentation decorators are replaced.
"""
from __future__ import annotations

import ast
import copy
from dataclasses import dataclass
import hashlib
import inspect
import json
import logging
import math
from pathlib import Path
from types import SimpleNamespace

from .contracts import need

RECEIPTS = {
    'source-receipt.json': 'baf184f43706c38cdce48a2719c3f548854135c6881d1bc3579e474c0550356a',
    'source-reference-addendum.json': 'e06fb1b163c505a8c09d5d4fd8f5773098045d2b3f7c161f513f93c5a1d92f53',
}


def capture_reference_sources(root):
    root = Path(root).resolve()
    sources = {}
    for name, expected in RECEIPTS.items():
        raw = (root/name).read_bytes()
        need(hashlib.sha256(raw).hexdigest() == expected, 'Reference source receipt mismatch')
        for row in json.loads(raw)['files']:
            path = Path(row.get('local_path', row['path'])).resolve()
            need(path.is_relative_to(root/'source'), 'Reference source path escapes bundle')
            content = path.read_bytes()
            need(len(content) == row['bytes'] and hashlib.sha256(content).hexdigest() == row['sha256'],
                 'Reference source content mismatch: ' + path.name)
            sources[path.relative_to(root/'source').as_posix()] = content.decode('utf-8')
    return sources


def selected_nodes(text, names, *, class_methods=None):
    tree = ast.parse(text)
    selected = []
    for node in tree.body:
        if isinstance(node, (ast.ClassDef, ast.FunctionDef)) and node.name in names:
            selected.append(copy.deepcopy(node))
        if class_methods and isinstance(node, ast.ClassDef):
            for function in node.body:
                if isinstance(function, ast.FunctionDef) and (node.name, function.name) in class_methods:
                    selected.append(copy.deepcopy(function))
    return selected


def execute_nodes(nodes, namespace, filename):
    """Strip doc decorators only; staticmethod/dataclass retain their semantics."""
    for node in nodes:
        for child in ast.walk(node):
            if isinstance(child, (ast.ClassDef, ast.FunctionDef)):
                child.decorator_list = [d for d in child.decorator_list if isinstance(d, ast.Name) and
                                        d.id in ('staticmethod', 'classmethod', 'property', 'dataclass')]
    module = ast.Module(body=[ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0), *nodes], type_ignores=[])
    exec(compile(ast.fix_missing_locations(module), filename, 'exec'), namespace)


def build_reference(config, sources, *, label_threshold=None, rationale_threshold=0.5):
    import numpy as np
    import torch
    from torch import nn
    from torch.nn import functional as F
    from transformers.utils import ModelOutput

    namespace = dict(torch=torch, nn=nn, F=F, math=math, inspect=inspect, dataclass=dataclass,
                     ModelOutput=ModelOutput, logger=logging.getLogger('multivers.legacy_reference'),
                     __name__=__name__, ACT2FN={'gelu': F.gelu})
    # Both torch1.7.1 and current torch take the F.gelu branch in archived activations.py.
    need(config.hidden_act == 'gelu', 'Reference supports the released GELU configuration only')
    utility_nodes = selected_nodes(sources['reference-transformers-4.2.2/modeling_utils.py'],
                                  {'apply_chunking_to_forward'},
                                  class_methods={('ModuleUtilsMixin', 'get_extended_attention_mask')})
    need(len(utility_nodes) == 2, 'Archived mask/chunk helpers missing')
    execute_nodes(utility_nodes, namespace, 'archived-transformers-modeling-utils')

    class LegacyBase(nn.Module):
        def __init__(self, model_config):
            super().__init__()
            self.config = model_config

        @property
        def dtype(self):
            return next(self.parameters()).dtype

        def init_weights(self):
            # Every tensor is overwritten by a subsequent strict load. No
            # from_pretrained/network lookup or training framework is needed.
            pass

    LegacyBase.get_extended_attention_mask = namespace['get_extended_attention_mask']
    namespace['LongformerPreTrainedModel'] = LegacyBase
    class_names = {'LongformerBaseModelOutput', 'LongformerBaseModelOutputWithPooling',
                   'LongformerEmbeddings', 'LongformerSelfAttention', 'LongformerSelfOutput',
                   'LongformerAttention', 'LongformerIntermediate', 'LongformerOutput',
                   'LongformerLayer', 'LongformerEncoder', 'LongformerPooler', 'LongformerModel',
                   'create_position_ids_from_input_ids'}
    legacy_nodes = selected_nodes(sources['reference-transformers-4.2.2/modeling_longformer.py'], class_names)
    need(len(legacy_nodes) == len(class_names), 'Archived Longformer inference definitions missing')
    execute_nodes(legacy_nodes, namespace, 'archived-transformers-longformer')

    native = dict(torch=torch, nn=nn, F=F, np=np, numpy=np, __name__=__name__)
    helper_names = {'ConfigurationError', 'get_device_of', 'get_range_vector',
                    'flatten_and_batch_shift_indices', 'batched_index_select'}
    execute_nodes(selected_nodes(sources['multivers/allennlp_nn_util.py'], helper_names), native, 'archived-batched-index-select')
    execute_nodes(selected_nodes(sources['multivers/allennlp_feedforward.py'], {'FeedForward'}), native, 'archived-feedforward')
    execute_nodes(selected_nodes(sources['multivers/util.py'], {'unbatch', 'flatten'}), native, 'archived-util')
    native['util'] = SimpleNamespace(unbatch=native['unbatch'], flatten=native['flatten'])
    methods = selected_nodes(sources['multivers/model.py'], set(),
                             class_methods={('MultiVerSModel', 'forward'), ('MultiVerSModel', 'decode')})
    # Extracted decode was a static method within its class; top-level binding
    # should be an ordinary callable with the original (output,batch,flag) signature.
    for node in methods:
        node.decorator_list = []
    execute_nodes(methods, native, 'archived-multivers-inference-math')

    class ReferenceMultiVerS(nn.Module):
        def __init__(self):
            super().__init__()
            self.nei_label = 1
            self.label_threshold = label_threshold
            self.rationale_threshold = rationale_threshold
            ref_config = copy.deepcopy(config)
            ref_config.gradient_checkpointing = False
            self.encoder = namespace['LongformerModel'](ref_config)
            self.dropout = nn.Dropout(config.hidden_dropout_prob)
            hidden = config.hidden_size
            self.label_classifier = native['FeedForward'](hidden, 2, [hidden, 3], [nn.GELU(), nn.Identity()], [self.dropout.p, 0])
            self.rationale_classifier = native['FeedForward'](2*hidden, 2, [hidden, 1], [nn.GELU(), nn.Identity()], [self.dropout.p, 0])

        forward = native['forward']

    return ReferenceMultiVerS(), native['decode']


def reference_tensorizer(tokenizer, sources):
    import numpy as np
    import torch
    from transformers import BatchEncoding
    namespace = dict(torch=torch, np=np, BatchEncoding=BatchEncoding,
                     Dataset=torch.utils.data.Dataset, util=SimpleNamespace(flatten=lambda values: [x for row in values for x in row]))
    execute_nodes(selected_nodes(sources['multivers/data.py'], {'MultiVerSDataset'}), namespace,
                  'archived-multivers-data')
    return namespace['MultiVerSDataset']([], tokenizer)
