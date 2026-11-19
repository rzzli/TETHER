from dataclasses import replace
import unittest

from tether_engine.contracts import Category, Citation
from tether_engine.generated_claims import ClaimSource, GeneratedRequest, Support

from .excerpts import content_review
from .pilot import digest, study_case
from .preflight import envelope
from .support import Rule


class NumericReportingTests(unittest.TestCase):
    def setUp(self):
        text = 'The chart reports an observed share of 12.5 percent.'
        source = ClaimSource('sample', text, digest(text.encode()),
                             Citation('sample', 'fixture', '1', 'a'*64, 'https://example.invalid'))
        self.request = GeneratedRequest(2, study_case('test'), Category.LITERATURE, (source,), 'What share?')
        self.rule = Rule('Example', 'share percent', 'sample', source.text_sha256, r'share of ([\d.]+) percent')

    def check(self, text, request=None):
        req = request or self.request
        scored = content_review(req, envelope(req,text,'sample'), (self.rule,))
        return scored.proposals[0].support

    def test_equivalent_units_and_relations(self):
        for text,expected in (('Example: share percent = 12.50%.',Support.SUPPORTED),
                              ('Example: share percent > 12.',Support.SUPPORTED),
                              ('Example: share percent != 12.5.',Support.CONTRADICTED),
                              ('Example: share percent = 0.125.',Support.CONTRADICTED)):
            with self.subTest(text=text):
                self.assertEqual(self.check(text),expected)

    def test_rejects_extra_proposition_and_changed_units(self):
        self.assertEqual(self.check('Example: share percent = 12.5%; everybody recovered.'),Support.MIXED)
        self.assertEqual(self.check('Example: patient count = 12.5%.'),Support.INSUFFICIENT)

    def test_source_identity_alone_cannot_supply_a_fact(self):
        changed = 'The chart reports an observed share of 64 percent.'
        source = replace(self.request.sources[0],text=changed,text_sha256=digest(changed.encode()))
        self.assertEqual(self.check('Example: share percent = 64%.',replace(self.request,sources=(source,))),
                         Support.INSUFFICIENT)
