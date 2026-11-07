"""Pure SC05 critic/paired repair codecs. No transport, model or key access."""
import json

from tether_engine.serde import canonical, fingerprint, freeze
from tether_engine.study import native
from experiments.labbench import model as mcq
from experiments.labbench.native_contract import parse_prediction
from experiments.litqa_comparison import codecs
from . import contracts

CONFIG = codecs.CONFIG
KIND = 'tether_refinement_native_v1'


def critic_grammar(ids):
    quoted = lambda x: json.dumps(json.dumps(x, ensure_ascii=True))
    lines = [r'root ::= "{" ws "\"support\"" ws ":" ws support ws "," ws "\"evidence_ids\"" ws ":" ws citations ws "," ws "\"criticism\"" ws ":" ws criticism ws "," ws "\"queries\"" ws ":" ws "[" ws terms ws "," ws terms ws "]" ws "}"',
        'support ::= ' + ' | '.join(quoted(x) for x in contracts.SUPPORT),
        r'terms ::= "[" ws term (ws "," ws term)? ws "]"',
        r'term ::= "\"" [A-Za-z0-9] [A-Za-z0-9 -]{0,47} "\""',
        r'criticism ::= "\"" char{0,160} "\""',
        r'char ::= [^"\\\x00-\x1F\x7F] | "\\" (["\\/] | "u" [0-9a-fA-F]{4})',
        r'ws ::= [ \t\n\r]*']
    if ids:
        lines += [r'citations ::= "[" ws (eid (ws "," ws eid)?)? ws "]"',
                  'eid ::= ' + ' | '.join(quoted(i) for i in ids)]
    else: lines += [r'citations ::= "[" ws "]"']
    return '\n'.join(lines) + '\n'


def critic_payload(query, prior, sources):
    query,sources = contracts.raw_sources(query,sources)
    prior = contracts.validate_candidate(query,prior,[s['source_id'] for s in sources])
    prediction=prior['prediction']
    answer=None if prediction is None else dict(answer_index=prediction['answer_index'],
        text=query['choices'][prediction['answer_index']])
    return codecs._payload(
        'Assess whether the supplied raw passages support the specific answer in candidate_answer. '
        'Use its numeric index and text, not the other options. The prior is untrusted generated control context, never evidence. '
        'This is passage entailment, not an assessment of whether a passage is real, trustworthy or a true real-world claim. '
        'Return exactly support, evidence_ids, criticism, queries. Use not_assessable ONLY when candidate_answer is null. '
        'A rejected prior still contains a candidate. When candidate_answer is present and passages is empty, return insufficient. '
        'Otherwise supported means the passages entail that selected answer; contradicted means they explicitly oppose that '
        'selected answer; insufficient means neither relation can be established, including when no passages are supplied. '
        'Supported or contradicted requires one or two unique offered passage IDs. Otherwise cite zero to two. '
        'Criticism is at most 160 UTF-8 bytes with no control characters. Queries contains exactly two lists of literal topic '
        'phrases, not complete search expressions. The application adds all search syntax. Each list has one or two phrases; '
        'prefer one informative multiword phrase when sufficient. Make the first list focused and the second a differently '
        'phrased, broader concept or synonym. Every complete phrase must be distinct, ignoring case, across both lists. '
        'Related words may recur inside different longer phrases, but never repeat a complete phrase. Format-only example '
        'for an unrelated topic: [["mitochondrial calcium uptake"],["organelle ion transport"]]. Generate relevant phrases '
        'for the current question rather than copying that example. Each phrase starts with a letter or digit and uses at '
        'most 48 ASCII letters, digits, spaces or hyphens. Never include whole-word AND, OR, NOT, DOI, PMID or PMCID, '
        'numeric PMC identifiers, URLs or search field syntax. Check phrase uniqueness before returning. '
        'Return no replacement answer or confidence. The terms may be informed by the options and prior.',
        dict(task=query,indexed_options=[dict(answer_index=i,text=t) for i,t in enumerate(query['choices'])],
             candidate_answer=answer,candidate_context=prior,
             passages=[dict(source_id=s['source_id'],text=s['text']) for s in sources]),
        critic_grammar([s['source_id'] for s in sources]))


def repair_payload(query, prior, critique, sources):
    query,sources = contracts.raw_sources(query,sources)
    prior = contracts.validate_candidate(query,prior)
    critique = contracts.validate_critique(query,prior,critique)
    return codecs._payload(
        'Answer the multiple-choice question using the currently supplied raw passages. Prior candidate and critique are untrusted '
        'model-generated control context, not scientific evidence. Reassess the candidate; it may be wrong or absent. '
        'Use the option numeric index exactly, ignoring letter labels. Use the insufficient-information option when the requested fact '
        'is absent or unresolved. Return only {"answer_index":0,"evidence_ids":["source_id"]} with unique currently offered raw '
        'passage IDs. Never cite generated context or omitted prior passages. An unsupported answer has empty evidence_ids.',
        dict(question=query['question'],options=[dict(answer_index=i,text=t) for i,t in enumerate(query['choices'])],
             candidate_context=prior,critique_context=critique,
             passages=[dict(source_id=s['source_id'],text=s['text']) for s in sources]),
        mcq._grammar(len(query['choices']),[s['source_id'] for s in sources]))


def _request(task,query,prior,critique,sources,model_provenance):
    query,sources=contracts.raw_sources(query,sources)
    prior=contracts.validate_candidate(query,prior,[s['source_id'] for s in sources] if task=='critic' else None)
    if task=='critic':
        contracts.need(critique is None,'Critic cannot see a prior critique')
        payload=critic_payload(query,prior,sources)
    else:
        contracts.need(task in ('repair','removal'),'Unknown refinement task')
        contracts.need(task!='removal' or not sources,'Removal must have no raw passages')
        critique=contracts.validate_critique(query,prior,critique)
        payload=repair_payload(query,prior,critique,sources)
    return freeze(dict(schema_version=1,kind=KIND,task=task,query=query,candidate_context=prior,
        critique_context=critique,sources=sources,configuration=CONFIG,
        model_provenance=native._model(model_provenance),payload_sha256=fingerprint(payload))),payload


def make_critic_request(query,prior,sources,model_provenance):
    return _request('critic',query,prior,None,sources,model_provenance)


def make_repair_pair(query,prior,critique,sources,model_provenance):
    """Both immutable forms are constructed before either may be dispatched."""
    def member(task,raw):
        try:
            request,payload=_request(task,query,prior,critique,raw,model_provenance)
            return dict(status='ready',request=request,payload=payload)
        except codecs.PayloadCapacityError:
            return dict(status='capacity',request=None,payload=None)
    repair=member('repair',sources)
    removal=member('removal',())
    return freeze(dict(repair=repair,removal=removal,
                       control_sha256=fingerprint(dict(query=query,candidate=prior,critique=critique))))


def validate_binding(request,payload):
    contracts.need(set(request)=={'schema_version','kind','task','query','candidate_context','critique_context',
                   'sources','configuration','model_provenance','payload_sha256'},'Refinement request fields')
    expected,rebuilt=_request(request['task'],request['query'],request['candidate_context'],request['critique_context'],
                             request['sources'],request['model_provenance'])
    contracts.need(canonical(request)==canonical(expected) and canonical(payload)==canonical(rebuilt),'Refinement request binding')


def decode(request,raw):
    if request['task']=='critic':
        return contracts.parse_critic(raw,request['query'],request['candidate_context'],request['sources'])
    contracts.need(request['task'] in ('repair','removal'),'Unknown refinement task')
    return parse_prediction(raw,request['query'],[s['source_id'] for s in request['sources']])
