"""Offline, exposed real-text retrieval pilot. Run as a module from the checkout."""
import argparse
from collections import Counter
from dataclasses import replace
from datetime import date, datetime, timezone
from hashlib import sha256
from importlib.resources import files
from pathlib import Path
from time import perf_counter_ns

from experiments.labbench.retrieval import BASE, parse_article
from tether_engine import retrieval
from tether_engine.contracts import Case, Category, Citation
from tether_engine.generated_claims import ClaimSource, GeneratedRequest
from tether_engine.serde import canonical, decode, parse_json

HERE = Path(__file__).resolve().parent
ARMS = (retrieval.QUESTION_BM25, retrieval.QUESTION_THREE_TERM_OVERLAP)
POLICY = retrieval.RetrievalPolicy(max_records=2, max_request_bytes=12000)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return sha256(data).hexdigest()


def read(path):
    return parse_json(path.read_bytes())


def save(path, obj):
    with path.open('xb') as stream:
        stream.write(canonical(obj) + b'\n')


def received(folder, number):
    name = f'requests/{number:03}'
    receipt = read(folder / (name + '.receipt.json'))
    data = (folder / (name + '.body')).read_bytes()
    require(receipt['relative_path'] == name + '.body' and receipt['http_status'] == 200
            and digest(data) == receipt['sha256'] and len(data) == receipt['bytes'], 'Receipt mismatch')
    return data, receipt


def prepare(collection, output):
    output.mkdir(parents=True, exist_ok=False)
    docs, articles = [], []
    for row in read(HERE / 'roster.json'):
        key = row['pmcid']
        folder = collection / 'cases' / row['case_id'] / 'retrieval'
        xml, receipt = received(folder, row['xml'])
        metadata, search = received(folder, row['metadata'])
        require(digest(xml) == row['sha256'] and receipt['final_url'] == BASE + key + '/fullTextXML'
                and search['final_url'].startswith(BASE + 'search?'), 'Original identity mismatch')
        candidates = [x for x in parse_json(metadata)['resultList']['result'] if x.get('pmcid') == key]
        require(len(candidates) == 1, 'Missing or ambiguous article metadata')
        item = candidates[0]
        require(item['isOpenAccess'] == 'Y' and item['license'] in ('cc by', 'cc0'), 'Unapproved rights')
        article = parse_article(xml, item)
        body = [s for s in article['spans'] if s['locator']['xml_path'] == './/body//p']
        eligible = [s for s in body if s['locator']['paragraph_index'] < 40]
        articles.append(dict(pmcid=key, doi=item['doi'], title=item['title'], authors=item.get('authorString'),
            license=item['license'], xml_sha256=digest(xml), metadata_sha256=digest(metadata),
            xml_license=article['xml_license'], body_paragraphs=len(body), selected_paragraphs=len(eligible),
            excluded_by_index=len(body)-len(eligible), url=receipt['final_url']))
        for s in eligible:
            docs.append(dict(id=s['evidence_id'], article=key, text=s['text'], locator=s['locator'],
                             text_sha256=s['text_sha256'], original_sha256=digest(xml), url=receipt['final_url']))
    questions = read(HERE / 'questions.json')
    refs = read(HERE / 'reference.json')
    ids = {d['id']: d for d in docs}
    require(len(ids) == len(docs) and len(questions) == len(refs) == 30, 'Incomplete development inventory')
    gold = {}
    for query, ref in zip(questions, refs, strict=True):
        require(query['id'] == ref['id'] and query['id'] not in gold, 'Schedule IDs disagree')
        spans = []
        for k in ref['required']:
            d = ids[k]
            require(d['article'] in query['articles'], 'Reference outside candidate pool')
            spans.append(dict(id=k, start_byte=0, end_byte=len(d['text'].encode()), sha256=d['text_sha256']))
        gold[query['id']] = dict(group=ref['group'], spans=spans)
    save(output/'actor.json', dict(documents=docs, questions=questions))
    save(output/'evaluator.json', gold)
    save(output/'protocol.json', dict(articles=articles, arms=ARMS, policy=POLICY,
        actor=digest((output/'actor.json').read_bytes()), evaluator=digest((output/'evaluator.json').read_bytes()),
        ranker=digest(Path(retrieval.__file__).read_bytes()), driver=digest(Path(__file__).read_bytes()),
        acquisition_failures=0, unavailable_rights=0, source_scope='four deliberately selected cached licensed articles',
        frozen_inputs={f:digest((HERE/f).read_bytes()) for f in ('questions.json','reference.json','roster.json')},
        options_visible=False, queries_per_case=1, fallback=False, model_calls=0,
        qualification='30 paired replayable queries, positives retrieved for all four articles, '
                      'at least 12 of 24 fully retrieved by BM25 and at least one complete cross-article pair. '
                      'No-answer offers reported separately; ranker does not answer or abstain on clinical claims.'))


def bound(path, expected):
    data = path.read_bytes()
    require(digest(data) == expected, f'Frozen file changed: {path.name}')
    return parse_json(data)


def study_case(case_id):
    base = decode(Case, parse_json(files('tether_engine').joinpath('demo/v2/case.json').read_bytes()))
    origin = date(2026, 11, 19)
    hypothesis = replace(base.hypothesis, target_id='QUAL:STUDY', indication_id='QUAL:REPORT',
        target_namespace_version='research-v1', indication_namespace_version='research-v1',
        intended_action='report', modality='unspecified', tissue=None)
    return replace(base, case_id=case_id, task='T6', origin=origin,
                   origin_at=datetime(2026,11,19,tzinfo=timezone.utc), program=None, endpoint=None,
                   hypothesis=hypothesis)


def rank(output):
    protocol = read(output/'protocol.json')
    require(protocol['driver'] == digest(Path(__file__).read_bytes())
            and protocol['ranker'] == digest(Path(retrieval.__file__).read_bytes())
            and protocol['policy'] == parse_json(canonical(POLICY)) and protocol['arms'] == list(ARMS),
            'Frozen method changed')
    actor = bound(output/'actor.json', protocol['actor'])
    sources = [(d['article'], ClaimSource(d['id'], d['text'], d['text_sha256'],
                Citation(d['article'], 'europepmc_fulltext', 'cached-xml', d['original_sha256'], d['url'])))
               for d in actor['documents']]
    rows = []
    for q in actor['questions']:
        request = GeneratedRequest(2, study_case(q['id']), Category.LITERATURE,
            tuple(s for paper,s in sources if paper in q['articles']), q['question'])
        for arm in ARMS:
            start = perf_counter_ns()
            selected, audit = retrieval.bounded_question_request(request, POLICY, strategy=arm)
            elapsed = perf_counter_ns()-start
            replay = retrieval.bounded_question_request(request, POLICY, strategy=arm)
            require(replay == (selected,audit) and len(canonical(selected)) == audit['request_bytes'],
                    'Replay or size mismatch')
            rows.append(dict(id=q['id'], arm=arm, audit=audit, elapsed_ns=elapsed,
                offered={s.observation_id:dict(sha256=s.text_sha256, start_byte=0,
                    end_byte=len(s.text.encode())) for s in selected.sources}))
    save(output/'rankings.json', dict(protocol=digest((output/'protocol.json').read_bytes()), rows=rows))


def evaluate(output):
    protocol = read(output/'protocol.json')
    gold = bound(output/'evaluator.json', protocol['evaluator'])
    ranks = read(output/'rankings.json')
    require(ranks['protocol'] == digest((output/'protocol.json').read_bytes()), 'Wrong protocol')
    results = {}
    for arm in ARMS:
        rows = [row for row in ranks['rows'] if row['arm'] == arm]
        require(len(rows) == len(gold) and {r['id'] for r in rows} == gold.keys(), 'Incomplete schedule')
        totals, exclusions, hit_articles, decisions = Counter(), Counter(), set(), []
        for r in rows:
            ref = gold[r['id']]
            spans = ref['spans']
            audit = r['audit']
            require(audit['query_count'] == 1 and audit['request_bytes'] <= POLICY.max_request_bytes
                    and len(audit['selected_ids']) == len(r['offered']) <= POLICY.max_records
                    and set(audit['selected_ids']) == set(r['offered']), 'Invalid selected set or budget')
            hits = [s['id'] for s in spans if r['offered'].get(s['id']) == {k:v for k,v in s.items() if k!='id'}]
            hit_articles.update(k.split(':')[0] for k in hits)
            exclusions.update(e['reason'] for e in audit['excluded'])
            reasons = {e['observation_id']:e['reason'] for e in audit['excluded']}
            decisions.append(dict(id=r['id'], group=ref['group'], hits=hits,
                misses={s['id']:reasons.get(s['id'],'incorrect_span') for s in spans if s['id'] not in hits},
                selected=audit['selected_ids'], offerable=audit['offerable_records'], request_bytes=audit['request_bytes']))
            totals.update(queries=1, request_bytes=audit['request_bytes'], selected=len(r['offered']),
                          ranking_ns=r['elapsed_ns'], required_spans=len(spans), hit_spans=len(hits))
            if spans:
                totals.update(answerable=1, any_hit=int(bool(hits)), full=int(len(hits)==len(spans)),
                              cross_full=int(ref['group']=='cross_article' and len(hits)==len(spans)))
            else:
                totals.update(no_answer=1, nonempty_pool=int(audit['offerable_records']>0),
                              distractor_offered=int(bool(r['offered'])))
        results[arm] = dict(totals=totals, exclusions=exclusions, hit_articles=sorted(hit_articles), cases=decisions)
    bm = results[ARMS[0]]
    passed = bm['totals']['full'] >= 12 and bm['totals']['cross_full'] >= 1 and len(bm['hit_articles']) == 4
    save(output/'evaluation.json', dict(qualified=passed, results=results, rankings_sha256=digest((output/'rankings.json').read_bytes()),
        scope='exposed full-paragraph retrieval only', answers_scored=0, model_calls=0, provider_usd=0))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=('prepare','rank','evaluate'))
    parser.add_argument('output', type=Path)
    parser.add_argument('--collection', type=Path)
    args = parser.parse_args()
    if args.stage == 'prepare':
        if args.collection is None:
            parser.error('prepare requires --collection')
        prepare(args.collection, args.output)
    elif args.stage == 'rank':
        rank(args.output)
    else:
        evaluate(args.output)
