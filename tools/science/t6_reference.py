"""Evaluator-only sealed source-bounded AI references for the top-one challenge."""
from pathlib import Path

from tether_engine.serde import ContractError, canonical, read_json
from tools.science.run_comparison import check_pin, pin


def require(value, message):
    if not value:
        raise ContractError(message)


def validate_review(review, tasks):
    require(review.get('schema_version') == 1 and isinstance(review.get('reviewer_id'), str)
            and review['reviewer_id'].strip(), 'Reference needs an identified reviewer')
    expected = {task['task_id']: task for task in tasks['tasks']}
    rows = review.get('tasks')
    require(isinstance(rows, list) and len(rows) == len(expected), 'Reference task coverage differs')
    require([r.get('task_id') for r in rows] == list(expected), 'Reference task order or identities differ')
    for row in rows:
        ids = expected[row['task_id']]['offered_candidate_ids']
        candidates = row.get('candidates')
        require(isinstance(candidates, list) and [c.get('observation_id') for c in candidates] == ids,
                'Reference must review every offered candidate exactly once in frozen order')
        for candidate in candidates:
            require(candidate.get('relevance') in ('direct', 'indirect', 'not_relevant', 'uncertain'),
                    'Invalid relevance rating')
            require(candidate.get('applicability') in ('applicable', 'context_mismatch', 'uncertain'),
                    'Invalid applicability rating')
            require(candidate.get('uncertainty') in ('low', 'moderate', 'high'), 'Invalid uncertainty rating')
            require(isinstance(candidate.get('reason'), str) and candidate['reason'].strip(),
                    'Every rating needs a source-grounded reason')
        best = row.get('admissible_best_ids')
        require(isinstance(best, list) and all(isinstance(x, str) for x in best)
                and len(best) == len(set(best)) and not set(best) - set(ids), 'Invalid admissible best set')
        require(type(row.get('none_sufficient')) is bool and row['none_sufficient'] == (not best),
                'None-sufficient answer and best set contradict')
        require(row.get('reference_uncertainty') in ('low', 'moderate', 'high'), 'Invalid task uncertainty')
        require(isinstance(row.get('reason'), str) and row['reason'].strip(), 'Task answer needs a reason')
    return review


def seal_references(task_manifest, reviews, adjudication, output):
    """Seal completed independent reviews and reconciliation; never infer answers."""
    tasks = read_json(check_pin(task_manifest))
    require(len(reviews) == 2, 'Exactly two independent source reviews required')
    documents = [validate_review(read_json(check_pin(proof)), tasks) for proof in reviews]
    require(all(document.get('task_manifest') == task_manifest for document in documents),
            'Review must bind the exact frozen task manifest')
    require(reviews[0]['sha256'] != reviews[1]['sha256'] and
            documents[0]['reviewer_id'] != documents[1]['reviewer_id'], 'Reviews must be distinct')
    resolved = validate_review(read_json(check_pin(adjudication)), tasks)
    require(resolved.get('task_manifest') == task_manifest and resolved.get('reviews') == reviews,
            'Reconciliation must bind exact tasks and both sealed reviews')
    require(resolved['reviewer_id'] not in {r['reviewer_id'] for r in documents},
            'Reconciliation needs a third reviewer identity')
    # The comparison executor checks this envelope without opening answer bodies.
    from datetime import datetime, timezone
    result = {'schema_version': 1, 'role': 'evaluation_only',
              'status': 'sealed_source_only_AI_reference', 'task_manifest': task_manifest,
              'reviews': reviews, 'adjudication': adjudication,
              'created_at_utc': datetime.now(timezone.utc).isoformat(),
              'best_set_disagreement_tasks': [a['task_id'] for a, b in
                  zip(documents[0]['tasks'], documents[1]['tasks'])
                  if set(a['admissible_best_ids']) != set(b['admissible_best_ids'])],
              'limitations': 'Independent contexts, shared AI biases; exposed development source references, not clinical or human-expert truth.'}
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('xb') as stream:
        stream.write(canonical(result))
    return pin(output)
