"""Invented protocol inputs for portable unit tests, never historical proofs.

No model, dataset, scientific registration or completed run is represented by
these values. Each call returns a fresh nested object for mutation tests.
"""


def chronology_protocol():
    return {
        'schema_version': 1, 'provider_spend_usd': 0,
        'frozen_at_utc': '2026-01-01T00:00:00Z',
        'clinical': {
            'origin_at': '2025-01-01T00:00:00Z',
            'endpoint_at': '2026-01-01T00:00:00Z', 'horizon_months': 12,
            'lock_status': 'not_locked', 'qualified_label_count': None,
            'predictor_sources': [{
                'role': 'agent_visible', 'evaluator_only': False,
                'released_at_upper_bound': '2024-12-01T00:00:00Z',
                'current_version_fallback': False}],
            'activation_gates': {name: False for name in (
                'origin_selection_sealed', 'historical_inputs_qualified',
                'independent_labels', 'dependence_and_power',
                'predictions_sealed_before_label_join', 'model_runtime_hashes',
                'registration_decision')},
        },
        'registration': {'publicly_registered': False, 'local_only': True},
        'models': [{
            'revision': 'a' * 40, 'released_at_upper_bound': '2024-12-01T00:00:00Z',
            'later_finetune_permitted': False,
            'roles': ['specialist', 'reviewer', 'chief_of_staff'],
            'files': [{'sha256': 'b' * 64, 'bytes': 1}],
        }],
        'comparison': {'virtual_biotech_adapted': True},
        'development': {'probabilities_withheld': True},
    }


def development_protocol():
    return {
        'schema_version': 1, 'purpose': 'exposed_t6_selection_diagnostics',
        'selection_cap': 3,
        'limitations': ['Fictional unit-test records; no scientific qualification.'],
        'baselines': ['extractive_all', 'lexical_top_k', 'provider_score_top_k'],
        'new_model_calls': 0, 'provider_spend_usd': 0, 'clinical_labels_read': False,
        'pilots': [{'id': 'fictional_pilot', 'path': 'fictional-unused-pilot',
                    'case_count': 1, 'seal_sha256': 'c' * 64}],
    }
