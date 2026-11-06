"""Descriptive evidence-intervention responses; no changed-answer correctness label."""
from experiments.scifact_comparison.inputs import map_rationale, need

LABELS = ['CONTRADICT','NEI','SUPPORT']


def compare_condition(primary, changed, lineages):
    rows = []
    for lineage in lineages:
        cid = lineage['id']
        old = {p['abstract_id']:p for p in primary[cid]}
        new = {p['abstract_id']:p for p in changed[cid]}
        need(set(old) == set(new) == {d['doc_id'] for d in lineage['documents']},'Diagnostic pair membership differs')
        for document in lineage['documents']:
            did = document['doc_id']
            a,b = old[did],new[did]
            applicable = document['annotated_rationale_applicable']
            both = a['status'] == b['status'] == 'completed'
            row = dict(claim_id=cid,doc_id=did,condition=lineage['condition'],
                primary_status=a['status'],condition_status=b['status'],both_observed=both,
                reference_mask_applicable=applicable,
                input_changed=document['input_document_sha256'] != document['source_document_sha256'])
            if both:
                pa,pb = a['prediction'],b['prediction']
                mapped = map_rationale(pb,document)
                original = set(pa['predicted_rationale'])
                transformed = set(mapped['original_sentence_indices'])
                selected = LABELS.index(pa['predicted_label'])
                row.update(primary_label=pa['predicted_label'],condition_label=pb['predicted_label'],
                    label_changed=pa['predicted_label'] != pb['predicted_label'],
                    primary_class_probability_change=pb['label_probs'][selected]-pa['label_probs'][selected],
                    primary_rationale_indices=sorted(original),condition_source_rationale_indices=sorted(transformed),
                    rationale_jaccard=len(original & transformed)/len(original | transformed) if original | transformed else None,
                    synthetic_selections=mapped['synthetic_selections'],
                    synthetic_sentences_selected=len(mapped['synthetic_selections']))
            rows.append(row)
    selected = [r for r in rows if r['both_observed'] and r['reference_mask_applicable'] is not False]
    return dict(scheduled_pairs=len(rows),both_observed_pairs=sum(r['both_observed'] for r in rows),
        applicable_observed_pairs=len(selected),changed_labels=sum(r['label_changed'] for r in selected),
        mean_primary_class_probability_change=sum(r['primary_class_probability_change'] for r in selected)/len(selected) if selected else None,
        synthetic_sentences_selected=sum(r['synthetic_sentences_selected'] for r in selected),
        probability_change_direction='condition_minus_primary_for_primary_predicted_class',
        scope='Reference-informed/synthetic diagnostics; a changed answer is not automatically wrong.',rows=rows)
