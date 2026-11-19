"""Study-specific numerical reporting criterion for exposed A05 development."""
from dataclasses import dataclass
from decimal import Decimal
import operator
import re

from tether_engine.generated_claims import Support, SupportReview, assess_span_selection
from tether_engine.serde import fingerprint


@dataclass(frozen=True)
class Rule:
    series: str
    field: str
    passage: str
    text_digest: str
    pattern: str


# The digest authenticates the complete published paragraph; values are read
# from the citation, never copied from the evaluator's expected-answer table.
RULES = (
    Rule('PROMIS', 'participants', 'PMC13705837:body:p0009', 'a7811715255d06592e5a361bb5b35fcd0b423322b2a816c2bdea862833dbae7d', r'Among ([\d,]+) men who underwent'),
    Rule('MRI-FIRST', 'participants', 'PMC13705837:body:p0016', '54b1b4f4054395e3d807af5af2cfb4f4e209425543fbbbfaf036cb01d6d347fd', r'Among ([\d,]+) biopsy-naïve men'),
    Rule('HALO', 'minimum collagen percent', 'PMC13651953:body:p0005', '053e2650208efd717efa20e64b3160f597c8b4537521a9df082963484f7e4189', r'collagen fraction ranged from ([\d.]+)%'),
    Rule('HALO', 'maximum collagen percent', 'PMC13651953:body:p0005', '053e2650208efd717efa20e64b3160f597c8b4537521a9df082963484f7e4189', r'collagen fraction ranged from [\d.]+% to ([\d.]+)%'),
    Rule('Brazil cohort', 'admissions', 'PMC13398326:body:p0015', '3053061026ca242f514680e58e468f9c098e1a26089d0f9041c9865be06733d6', r'A total of ([\d,]+) obstetric admissions'),
    Rule('Brazil cohort', 'obesity admissions', 'PMC13398326:body:p0015', '3053061026ca242f514680e58e468f9c098e1a26089d0f9041c9865be06733d6', r'of which ([\d,]+) \(0\.6%\) corresponded to women with obesity'),
    Rule('CNS review', 'screened records', 'PMC13674201:body:p0026', 'a2068ebce8da5849c7920d7d9bcf023588d9992a73482d89ebafc6f0ed76b82b', r'([\d,]+) records were screened by title'),
    Rule('CNS review', 'included studies', 'PMC13674201:body:p0027', '719f10dba98e0f63092be9602d369e1aa31bfe6cf9b2c48342112d1192e40fcd', r'([\d,]+) studies were included'),
)
NUMBER = r'(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?'
CLAUSE = re.compile(rf'([\w -]+): ([\w -]+) (=|!=|<|>) ({NUMBER})\.?')
COMPARE = {'=':operator.eq, '!=':operator.ne, '<':operator.lt, '>':operator.gt}


def assess_content(proposal, rules=RULES):
    """Check every clause against material actually quoted in this proposal."""
    facts = {}
    for q in proposal.quotes:
        for rule in rules:
            if (q.observation_id, q.source_sha256) != (rule.passage, rule.text_digest):
                continue
            found = re.findall(rule.pattern, q.quote)
            if len(found) == 1:
                facts.setdefault((rule.series.casefold(), rule.field), set()).add(Decimal(found[0].replace(',', '')))
    outcomes = set()
    for clause in proposal.text.strip().split('; '):
        parsed = CLAUSE.fullmatch(clause)
        if not parsed:
            outcomes.add(Support.INSUFFICIENT)
            continue
        subject, field, op, raw = parsed.groups()
        values = facts.get((subject.casefold(), field.casefold()), ())
        if not values:
            outcomes.add(Support.INSUFFICIENT)
        else:
            for value in values:
                valid = COMPARE[op](value, Decimal(raw.replace(',', '')))
                outcomes.add(Support.SUPPORTED if valid else Support.CONTRADICTED)
    return next(iter(outcomes)) if len(outcomes) == 1 else Support.MIXED


def review(request, raw):
    initial = assess_span_selection(request, raw)
    reviews = tuple(SupportReview(initial.request_sha256, fingerprint(p.proposal),
        'research.study_numeric_reporting.v1', assess_content(p.proposal)) for p in initial.proposals
        if p.quote_status == 'valid')
    return assess_span_selection(request, raw, reviews=reviews)
