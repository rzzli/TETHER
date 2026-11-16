"""Public wire-format controls, constructed without the production serializer."""
import hashlib
import json
import unittest

from tether_engine.journal import parse_chain
from tether_engine.serde import ContractError


def wire(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def one_event(sequence=0):
    record = dict(sequence=sequence, event='plan', details={}, previous_sha256=None)
    record['sha256'] = hashlib.sha256(wire(record)).hexdigest()
    return wire(record) + b'\n'


class JournalWireConformanceTests(unittest.TestCase):
    def test_integer_sequence_positive_control(self):
        events = parse_chain(one_event())
        self.assertEqual(len(events), 1)
        self.assertIs(type(events[0]['sequence']), int)

    def test_boolean_sequence_is_not_an_integer_counter(self):
        with self.assertRaisesRegex(ContractError, 'hash-chain'):
            parse_chain(one_event(False))

    def test_integral_float_sequence_is_not_an_integer_counter(self):
        with self.assertRaisesRegex(ContractError, 'hash-chain'):
            parse_chain(one_event(0.0))


if __name__ == '__main__':
    unittest.main()
