"""Released MultiVerS concatenation and sentence indexing, without truncation.

Adapted from David Wadden's MIT-licensed MultiVerS data.py at a6ce033f.
The original notice is retained in THIRD_PARTY_NOTICES.md and the source bundle.
"""
from __future__ import annotations

import json
from .contracts import need

EXTRA_TOKENS = ('<|sec|>', '</|sec|>', '<|sec-title|>', '</|sec-title|>',
                '<|abs|>', '</|abs|>', '<|title|>', '</|title|>', '<|sent|>', '<|par|>')
ASSET_NAMES = ('config.json', 'vocab.json', 'merges.txt', 'tokenizer.json')


def build_tokenizer(captured):
    """Build from already hash-verified memory, with no path or network fallback."""
    from tokenizers import Tokenizer
    from transformers import LongformerTokenizerFast
    need(set(captured) == set(ASSET_NAMES), 'Exact four tokenizer/config assets required')
    backend = Tokenizer.from_str(captured['tokenizer.json'].decode('utf-8'))
    tokenizer = LongformerTokenizerFast(
        tokenizer_object=backend, bos_token='<s>', eos_token='</s>', unk_token='<unk>',
        sep_token='</s>', cls_token='<s>', pad_token='<pad>', mask_token='<mask>',
        add_prefix_space=False, trim_offsets=True, model_max_length=4096)
    need(tokenizer.bos_token_id == 0 and tokenizer.pad_token_id == 1 and tokenizer.eos_token_id == 2,
         'Unexpected base special token IDs')
    vocabulary = json.loads(captured['vocab.json'])
    need(tokenizer.get_vocab() == vocabulary, 'Tokenizer JSON and vocabulary differ')
    # This is add_tokens, exactly as released; these are not all_special_tokens.
    need(tokenizer.add_tokens(list(EXTRA_TOKENS)) == 10, 'Expected ten new science tokens')
    need([tokenizer.convert_tokens_to_ids(x) for x in EXTRA_TOKENS] == list(range(50265, 50275)),
         'Unexpected science-token ordering or IDs')
    need(len(tokenizer) == 50275, 'Unexpected finalized vocabulary size')
    return tokenizer


def tensorize_pair(tokenizer, claim, sentences, title=None, *, max_tokens=4096):
    need(isinstance(claim, str) and claim.strip(), 'Invalid claim')
    need(isinstance(sentences, (list, tuple)) and sentences and
         all(isinstance(x, str) and x.strip() for x in sentences), 'Invalid sentence list')
    need(title is None or isinstance(title, str), 'Invalid title')
    cited_text = tokenizer.eos_token.join(sentences)
    if title is not None:
        cited_text = title + tokenizer.eos_token + cited_text
    encoded = tokenizer(claim + tokenizer.eos_token + cited_text)
    ids = list(encoded['input_ids'])
    need(len(ids) <= max_tokens, f'Input exceeds {max_tokens} tokens; no truncation is permitted')
    eos = [i for i, token in enumerate(ids) if token == tokenizer.eos_token_id]
    need(eos, 'Missing claim separator')
    offsets = eos[1 if title is None else 2:]
    need(len(offsets) == len(sentences), 'Sentence separator count differs from abstract sentence count')
    global_mask = [int(token in (tokenizer.bos_token_id, tokenizer.eos_token_id) or i < eos[0])
                   for i, token in enumerate(ids)]
    return {'tokenized': {'input_ids': ids, 'attention_mask': list(encoded['attention_mask']),
                          'global_attention_mask': global_mask}, 'abstract_sent_idx': offsets}


def collate(entries, tokenizer):
    import torch
    need(entries, 'Cannot collate an empty batch')
    max_tokens = max(len(x['tokenized']['input_ids']) for x in entries)
    max_sentences = max(len(x['abstract_sent_idx']) for x in entries)
    tokenized = {}
    for field, pad in (('input_ids', tokenizer.pad_token_id), ('attention_mask', 0), ('global_attention_mask', 0)):
        tokenized[field] = torch.tensor([x['tokenized'][field] + [pad] * (max_tokens-len(x['tokenized'][field]))
                                        for x in entries], dtype=torch.long)
    return {'tokenized': tokenized,
            'abstract_sent_idx': torch.tensor([x['abstract_sent_idx'] + [0] * (max_sentences-len(x['abstract_sent_idx']))
                                               for x in entries], dtype=torch.long),
            'claim_id': torch.tensor([x['claim_id'] for x in entries], dtype=torch.long),
            'abstract_id': torch.tensor([x['abstract_id'] for x in entries], dtype=torch.long)}
