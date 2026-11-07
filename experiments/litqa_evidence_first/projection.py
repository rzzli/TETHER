"""Complete paired requests and minimal single-member actor grants.

The trusted preparer supplies source-verified contexts. This projection alone
does not grant source eligibility and cannot turn an arbitrary file into an
admitted scientific source.
"""
from tether_engine.serde import canonical, fingerprint, freeze
from experiments.litqa_refinement import pipeline
from . import contracts as c, model


def actor_input(task, query, prior, critic, sources, provenance, member, control):
    c.need(task in c.PHASES, 'Unknown actor task')
    c.need(task != 'removal' or not sources, 'Removal actor cannot receive raw passages')
    c.need(control == fingerprint(dict(query=query, candidate=prior, critique=critic)),
           'Actor common control identity differs')
    # No pair root, context proof, other member or prior repair output is granted.
    return freeze(dict(task=task, query=query, candidate_context=prior,
                       critique_context=critic, sources=sources, model_provenance=provenance,
                       prepared_member=member, control_sha256=control))


def actor_member(pair, task):
    c.need(task in c.PHASES, 'Unknown pair member')
    return actor_input(task, pair['query'], pair['prior'], pair['critic'],
                       pair['sources'] if task == 'repair' else (),
                       pair['model_provenance'], pair['members'][task], pair['control_sha256'])


def from_verified_context(query, prior, critic, sources, model_provenance, *, cutoff, context):
    """Pure construction; caller must bind its independent source capability."""
    c.need(isinstance(cutoff, str) and context['cutoff'] == cutoff,
           'Original information cutoff differs')
    members = model.make_pair(query, prior, critic, sources, model_provenance)
    return freeze(dict(query=query, prior=prior, critic=critic, sources=sources,
                       model_provenance=model_provenance, cutoff=cutoff, context=context,
                       members={task: members[task] for task in c.PHASES},
                       control_sha256=members['control_sha256'], method_sha256=members['method_sha256']))


def prepare_pair(product, case, model_provenance, *, cutoff, deadline):
    """Reverify old source-rich preparation without admitting old repair output."""
    c.need(product['cutoff'] == cutoff, 'Fixed original cutoff required')
    query, prior, critic, context, _ = pipeline._pair_inputs(product, case, model_provenance, deadline)
    result = from_verified_context(query, prior, critic, context.sources, model_provenance,
                                   cutoff=cutoff, context=context.report)
    c.need(canonical(context.report) == canonical(result['context']), 'Source context projection differs')
    return result
