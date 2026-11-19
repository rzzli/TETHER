"""Deterministic numerical extractor using the same question and spans as the model."""
from collections import defaultdict
from decimal import Decimal
import re

from tether_engine.generated_claims import make_span_catalog


NUMBER = r'(?:[0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)(?:\.[0-9]+)?'
QUESTION = re.compile(
    r'^What was the reported (count|percentage) for (.+?)\? '
    r'Field: ([^.]+)\. Context: ([^.]+)\. '
)
ANSWER = re.compile(rf'^Reported value:\s*({NUMBER})\s*(%)?\.?$', re.I)
WORDS = re.compile(r'[^\W_]+', re.UNICODE)
SENTENCES = re.compile(r'(?<=[.!?])\s+(?=[A-Z])')
COUNTS = re.compile(rf'(?<![\d\w.,/−+-])({NUMBER})(?![\d\w]|[.,]\d|\s*[%/])')
PERCENTAGES = re.compile(rf'(?<![\d\w.,/−+-])({NUMBER})\s*%')
STOP = frozenset('a an and as at by for from in of on or the to was were with'.split())


def number(raw):
    return Decimal(raw.replace(',', ''))


def parse_answer(text, unit):
    parsed = ANSWER.fullmatch(text.strip())
    if parsed is None or (parsed[2] and unit != 'percentage'):
        return None
    return number(parsed[1])


def _terms(text):
    return {word for word in WORDS.findall(text.casefold()) if word not in STOP}


def extract(request):
    """Return one candidate value and cite its offered span, or abstain on ambiguity."""
    match = QUESTION.match(request.question or '')
    if match is None:
        raise ValueError('Question does not match the frozen format')
    unit, _, field, context = match.groups()
    unit_pattern = COUNTS if unit == 'count' else PERCENTAGES
    field_terms = _terms(field)
    context_terms = _terms(context)
    candidates = defaultdict(set)
    for offer in make_span_catalog(request).offers:
        source = request.sources[offer.source_index]
        text = source.text.encode()[offer.start_byte:offer.end_byte].decode()
        passage_terms = _terms(text)
        if not context_terms <= passage_terms:
            continue
        for sentence in SENTENCES.split(text):
            for value in unit_pattern.finditer(sentence):
                left = WORDS.findall(sentence[:value.start()].casefold())[-5:]
                right = WORDS.findall(sentence[value.end():].casefold())[:5]
                if field_terms <= set(left + right):
                    candidates[number(value[1])].add(source.observation_id)
    if len(candidates) != 1:
        return None
    value, sources = next(iter(candidates.items()))
    if len(sources) != 1:
        return None
    return value, next(iter(sources))
