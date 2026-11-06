"""Native full MultiVerS inference math on a current PyTorch/Longformer runtime.

Adapted from MIT-licensed dwadden/multivers a6ce033f: original learned key names,
pooled label head, joint pooled/sentence rationale head, thresholds and decoding.
"""
from __future__ import annotations

import math
import torch
from torch import nn
from torch.nn import functional as F
from transformers import LongformerModel

from .contracts import need


class FeedForward(nn.Module):
    def __init__(self, input_dim, hidden_dim, output_dim, dropout):
        super().__init__()
        self._linear_layers = nn.ModuleList([nn.Linear(input_dim, hidden_dim), nn.Linear(hidden_dim, output_dim)])
        self._activations = nn.ModuleList([nn.GELU(), nn.Identity()])
        self._dropout = nn.ModuleList([nn.Dropout(dropout), nn.Dropout(0)])

    def forward(self, value):
        for layer, activation, dropout in zip(self._linear_layers, self._activations, self._dropout):
            value = dropout(activation(layer(value)))
        return value


class MultiVerS(nn.Module):
    def __init__(self, config, *, label_threshold=None, rationale_threshold=0.5):
        super().__init__()
        need(label_threshold is None or (type(label_threshold) in (int, float) and
             math.isfinite(label_threshold) and 0 <= label_threshold <= 1), 'Invalid label threshold')
        need(type(rationale_threshold) in (int, float) and math.isfinite(rationale_threshold) and
             0 <= rationale_threshold <= 1, 'Invalid rationale threshold')
        self.nei_label = 1
        self.label_threshold, self.rationale_threshold = label_threshold, rationale_threshold
        self.encoder = LongformerModel(config, add_pooling_layer=True)
        # Transformers removed this non-learned buffer after 4.2.2. Retain its
        # native key, verify its exact values, and then use strict=True loading.
        if 'position_ids' not in self.encoder.embeddings._buffers:
            self.encoder.embeddings.register_buffer('position_ids',
                torch.arange(config.max_position_embeddings).expand((1, -1)), persistent=True)
        self.dropout = nn.Dropout(config.hidden_dropout_prob)
        hidden = config.hidden_size
        self.label_classifier = FeedForward(hidden, hidden, 3, self.dropout.p)
        self.rationale_classifier = FeedForward(2*hidden, hidden, 1, self.dropout.p)

    def forward(self, tokenized, abstract_sent_idx):
        need(abstract_sent_idx.ndim == 2 and abstract_sent_idx.dtype == torch.long,
             'Sentence offsets must be an integer batch matrix')
        need(bool((abstract_sent_idx >= 0).all()) and
             bool((abstract_sent_idx < tokenized['input_ids'].shape[1]).all()), 'Sentence offset out of range')
        encoded = self.encoder(**tokenized, return_dict=True)
        pooled = self.dropout(encoded.pooler_output)
        label_logits = self.label_classifier(pooled)
        label_probs = F.softmax(label_logits, dim=1).detach()
        if self.label_threshold is None:
            labels = label_logits.argmax(dim=1)
        else:
            adjusted = label_probs.clone()
            adjusted[:, self.nei_label] = self.label_threshold
            labels = adjusted.argmax(dim=1)
        hidden = self.dropout(encoded.last_hidden_state).contiguous()
        indices = abstract_sent_idx.unsqueeze(-1).expand(-1, -1, hidden.shape[-1])
        sentence_states = torch.gather(hidden, 1, indices)
        pooled_rep = pooled.unsqueeze(1).expand_as(sentence_states)
        rationale_logits = self.rationale_classifier(torch.cat([pooled_rep, sentence_states], dim=2)).squeeze(2)
        rationale_probs = torch.sigmoid(rationale_logits).detach()
        return dict(label_logits=label_logits, rationale_logits=rationale_logits,
                    label_probs=label_probs, rationale_probs=rationale_probs,
                    predicted_labels=labels,
                    predicted_rationales=(rationale_probs >= self.rationale_threshold).to(torch.int64))


def load_state_strict(model, state):
    expected = model.state_dict()
    need(isinstance(state, dict), 'State must be a tensor dictionary')
    need(set(state) == set(expected),
         f'Checkpoint state keys differ: missing={sorted(set(expected)-set(state))[:10]}, '
         f'extra={sorted(set(state)-set(expected))[:10]}')
    for name, target in expected.items():
        value = state[name]
        need(type(value) is torch.Tensor and value.layout == torch.strided,
             'State value must be a dense tensor: ' + name)
        need(value.shape == target.shape and value.dtype == target.dtype,
             'State shape or dtype differs: ' + name)
        if value.is_floating_point():
            need(bool(torch.isfinite(value).all()), 'Non-finite state tensor: ' + name)
        else:
            need(name == 'encoder.embeddings.position_ids' and torch.equal(value.cpu(), target.cpu()),
                 'Unexpected or altered non-learned state buffer: ' + name)
    model.load_state_dict(state, strict=True)


def decode(output, batch, *, force_rationale=False):
    labels = ('CONTRADICT', 'NEI', 'SUPPORT')
    result = []
    for row in range(len(batch['claim_id'])):
        label = labels[int(output['predicted_labels'][row])]
        valid = batch['abstract_sent_idx'][row] > 0
        probabilities = output['rationale_probs'][row][valid]
        indicators = output['predicted_rationales'][row][valid]
        sentences = indicators.nonzero(as_tuple=True)[0].detach().cpu().tolist()
        if force_rationale and label != 'NEI' and not sentences:
            need(probabilities.numel() > 0, 'No eligible rationale sentence')
            sentences = [int(probabilities.argmax())]
        result.append(dict(claim_id=int(batch['claim_id'][row]), abstract_id=int(batch['abstract_id'][row]),
                           predicted_label=label, predicted_rationale=sentences,
                           label_probs=output['label_probs'][row].detach().cpu().tolist(),
                           rationale_probs=probabilities.detach().cpu().tolist()))
    return result
