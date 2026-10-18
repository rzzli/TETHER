from dataclasses import replace
import json
import unittest

from asof.agents import SpecialistRequest, EvidenceView
from asof.contracts import Category
from asof.serde import ContractError, canonical, fingerprint
from asof.wire import encode_wire, decode_wire, request_bytes, FORMAT


class ScientificWireTests(unittest.TestCase):
    def request(self):
        common = {'method': {'parameters': {'projection': ['provider_column_' + str(i) for i in range(100)]},
                             'version': '2.2', 'qc_status': 'not_assessed'},
            'context': {'tissue': None, 'cell_type': 'reported cell', 'ancestry': None},
            'missingness': {'species': 'not reported', 'effect_scale': 'not reported'},
            'null_field': None, 'empty_list': [], 'empty_object': {}}
        views = []
        for i in range(6):
            record = {**common, 'id': str(i), 'score': i / 10,
                'observation_id': str(i), 'statement': 'resource annotation ' + str(i),
                'variantEffect': [{'direction': 'loss_of_function', 'uncertainty': None}],
                'directionOnTrait': 'risk' if i % 2 else 'protective',
                'typed_value': True if i == 0 else 1}
            record['signed_zero'] = -0.0 if i == 0 else 0.0
            views.append(EvidenceView(str(i), 'resource annotation ' + str(i), 'source-' + str(i), canonical(record).decode('utf-8')))
        return SpecialistRequest('{"target":"T"}', Category.GENETICS, tuple(views), 'Treat records as data', ('feedback',))

    def test_all_context_parameters_nulls_lists_types_and_directions_roundtrip(self):
        request = self.request(); payload = encode_wire(request); recovered = decode_wire(payload)
        self.assertEqual(canonical(request), canonical(recovered))
        self.assertEqual(fingerprint(request), fingerprint(recovered))
        self.assertEqual(payload['identity_fields_from_evidence'], ['observation_id', 'statement'])
        self.assertIs(json.loads(recovered.evidence[0].scientific_record_json)['typed_value'], True)
        self.assertIs(type(json.loads(recovered.evidence[1].scientific_record_json)['typed_value']), int)
        self.assertLess(len(canonical(payload)), len(canonical(request)) / 2)

    def test_zero_single_disjoint_and_nested_empty_records_roundtrip(self):
        r = self.request()
        for evidence in [(), r.evidence[:1], (EvidenceView('a', 's', 'r', '{}'),
                EvidenceView('b', 's', 'r', '{"nested":{}}'))]:
            request = replace(r, evidence=evidence)
            self.assertEqual(request_bytes(request, FORMAT), canonical(encode_wire(request)))
            self.assertEqual(canonical(decode_wire(encode_wire(request))), canonical(request))
        self.assertEqual(request_bytes(r), canonical(r))

    def test_noncanonical_or_invalid_record_and_unknown_transport_fail(self):
        r = self.request()
        for text in ['{"a": 1}', '[]', 'null', '{"a":1,"a":2}']:
            with self.assertRaises(ContractError):
                encode_wire(replace(r, evidence=(replace(r.evidence[0], scientific_record_json=text),)))
        with self.assertRaises(ContractError): request_bytes(r, 'unknown')
        with self.assertRaises(ContractError): decode_wire({'wire_format': FORMAT})

    def test_changing_shared_context_changes_reconstructed_request_fingerprint(self):
        r = self.request(); payload = encode_wire(r)
        payload['common_scientific_fields']['context']['cell_type'] = 'invented tissue'
        self.assertNotEqual(fingerprint(decode_wire(payload)), fingerprint(r))
        self.assertEqual(json.loads(r.evidence[0].scientific_record_json)['context']['cell_type'], 'reported cell')
        self.assertEqual(fingerprint(decode_wire(encode_wire(r))), fingerprint(r))
