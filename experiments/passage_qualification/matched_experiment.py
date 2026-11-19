"""Freeze, execute and replay the source-disjoint matched-extraction comparison."""
import argparse
from collections import Counter, defaultdict
from pathlib import Path
import random

from experiments.labbench.retrieval import BASE, parse_article
from tether_engine import generated_chat as chat
from tether_engine.contracts import Category, Citation
from tether_engine.generated_claims import ClaimSource, GeneratedRequest, assess_span_selection
from tether_engine.serde import canonical, decode, fingerprint

from . import matched_extractor, model_batch, pilot, preflight


ROSTER = Path(__file__).with_name('matched_roster.json')
SCHEDULE = 24


def frozen_code():
    paths = [Path(__file__), Path(matched_extractor.__file__), Path(pilot.__file__),
             Path(preflight.__file__), ROSTER, *model_batch.method_files()]
    return {path.name: pilot.digest(path.read_bytes()) for path in paths}


def article(collection, item):
    folder = collection / 'cases' / item['case'] / 'retrieval'
    xml, receipt = pilot.received(folder, item['xml'])
    raw_meta, meta_receipt = pilot.received(folder, item['metadata'])
    key = item['pmcid']
    pilot.require(pilot.digest(xml) == item['sha256']
                  and receipt['final_url'] == BASE + key + '/fullTextXML'
                  and meta_receipt['final_url'].startswith(BASE + 'search?'), 'Original source identity differs')
    matches = [
        row for row in pilot.parse_json(raw_meta)['resultList']['result']
        if row.get('pmcid') == key and row.get('isOpenAccess') == 'Y' and row.get('license') == 'cc by'
    ]
    pilot.require(len(matches) == 1, 'Source was not uniquely identified with CC BY metadata')
    parsed = parse_article(xml, matches[0])
    source = Citation(key, 'europepmc_fulltext', 'cached-xml', item['sha256'], receipt['final_url'])
    body = {
        span['locator']['paragraph_index']: ClaimSource(span['evidence_id'], span['text'], span['text_sha256'], source)
        for span in parsed['spans'] if span['locator']['xml_path'] == './/body//p'
    }
    return parsed, body, pilot.digest(raw_meta)


def design(collection):
    schedule = []
    sources = []
    rng = random.Random(20261119)
    for item in pilot.read(ROSTER):
        parsed, body, meta_hash = article(collection, item)
        background = item['background']
        windows = set(background)
        for index, slot in enumerate(item['slots']):
            unit, subject, field, context, loc, expected, witness = slot
            windows.add(loc)
            pilot.require(witness in body[loc].text and expected in witness.replace(',', ''), 'Missing original measurement')
            question = (
                f'What was the reported {unit} for {subject}? Field: {field}. Context: {context}. '
                'Use only the offered excerpts. Answer with exactly one claim in the form '
                '"Reported value: NUMBER." and cite the excerpt that reports the requested value. '
                'For a percentage give percentage points as printed, without dividing by 100. '
                'For example a printed 42% is 42. If the requested value and context are unavailable, '
                'return an empty claims array. Do not infer values from a different group or field.'
            )
            other = next(i for i in background if i != loc)
            cases = [(loc, other, True)]
            if item['withhold'] == index:
                pilot.require(all(i != loc and witness not in body[i].text for i in background),
                              'Withheld evidence remains available')
                cases.append((*background, False))
            for first, second, answerable in cases:
                contexts = [body[first], body[second]]
                rng.shuffle(contexts)
                schedule.append((
                    question, contexts,
                    dict(pmcid=item['pmcid'], pair=f"{item['pmcid']}/{index+1}",
                         unit=unit, expected=expected if answerable else None,
                         source_id=body[loc].observation_id if answerable else None,
                         witness=witness if answerable else None),
                ))
        sources.append(dict(pmcid=item['pmcid'], doi=parsed['doi'], title=parsed['title'],
                            release_date=parsed['publication_date'], xml_license=parsed['xml_license'],
                            sha256=item['sha256'], metadata_sha256=meta_hash,
                            passages={i: body[i].text_sha256 for i in sorted(windows)}))
    rng.shuffle(schedule)
    actor, gold = [], []
    for i, (question, offered, row) in enumerate(schedule, 1):
        request = GeneratedRequest(2, pilot.study_case(f'matched-{i:02}'), Category.LITERATURE, tuple(offered), question)
        request.validate()
        pilot.require(len(matched_extractor.make_span_catalog(request).offers) == 2, 'Both passages must be offerable')
        actor.append(request)
        gold.append(dict(case_id=request.case.case_id, **row))
    pilot.require(len(actor) == SCHEDULE and len(sources) == len({s['pmcid'] for s in sources}) == 8
                  and sum(row['expected'] is None for row in gold) == 8, 'Wrong design size')
    return actor, gold, sources


def prepare(collection, prior, exposure, output):
    actor, gold, sources = design(collection)
    checked = pilot.read(exposure)
    pilot.require(checked['hits'] == [] and set(checked['pmcids']) == {s['pmcid'] for s in sources},
                  'Paper exposure review is missing or mismatched')
    native = pilot.read(prior)
    pins = {key: native[key] for key in ('native_runtime', 'weights', 'limits', 'wall_seconds',
                                        'startup_seconds', 'cleanup_seconds')}
    output.mkdir(parents=True)
    documents = {'actor': actor, 'reference': gold, 'sources': sources, 'prior_exposure': checked}
    for name, data in documents.items():
        pilot.save(output / f'{name}.json', data)
    hashes = {name: pilot.digest((output / f'{name}.json').read_bytes()) for name in documents}
    pilot.save(output / 'protocol.json', dict(
        **hashes, **pins, method={p.name: pilot.digest(p.read_bytes()) for p in model_batch.method_files()},
        comparison_code=frozen_code(), parent_protocol=pilot.digest(prior.read_bytes()),
        schedule=SCHEDULE, answerable=16, source_withheld=8, retries=0, provider_usd=0,
        max_input_tokens=98304, max_output_tokens=9216, source_acquisition_bytes=0,
        scoring='One valid proposal with the expected numeric value and exact supporting source earns a supported answer. '
        'A valid empty response earns abstention only on a source-withheld case. Wrong, unsupported and failed responses '
        'retain their scheduled denominator. Both arms receive the same request. Report paired differences and paper counts.',
    ))


def verify_freeze(freeze, anchor, collection=None):
    protocol = pilot.bound(freeze / 'protocol.json', anchor)
    pilot.require(protocol['comparison_code'] == frozen_code(), 'Comparison implementation changed')
    for name in ('actor', 'reference', 'sources', 'prior_exposure'):
        pilot.bound(freeze / f'{name}.json', protocol[name])
    if collection is not None:
        rebuilt = design(collection)
        for name, data in zip(('actor', 'reference', 'sources'), rebuilt, strict=True):
            pilot.require((freeze / f'{name}.json').read_bytes() == canonical(data) + b'\n',
                          f'{name} differs on original-source reconstruction')
    return protocol


def score_response(assessment, reference):
    if assessment is None or assessment.envelope_error:
        return 'failure'
    if not assessment.proposals:
        return 'warranted_abstention' if reference['expected'] is None else 'missed_answer'
    if reference['expected'] is None or len(assessment.proposals) != 1:
        return 'unsupported_answer'
    result = assessment.proposals[0]
    if result.proposal is None or result.quote_status != 'valid':
        return 'unsupported_answer'
    proposal = result.proposal
    expected = matched_extractor.number(reference['expected'])
    value = matched_extractor.parse_answer(proposal.text, reference['unit'])
    licensed_quote = any(q.observation_id == reference['source_id'] and reference['witness'] in q.quote
                         for q in proposal.quotes)
    if value != expected:
        return 'wrong_value'
    return 'supported_answer' if licensed_quote else 'unsupported_answer'


def score(freeze, anchor, collection, output):
    protocol = verify_freeze(freeze, anchor, collection)
    model = pilot.read(freeze / 'attempts' / 'report.json')
    pilot.require(model['protocol'] == anchor and model['server_reaped'] and not model['errors']
                  and model['attempts'] == model['scheduled'] == len(model['completed']) == SCHEDULE,
                  'Model batch is incomplete')
    totals = defaultdict(Counter)
    paired = defaultdict(Counter)
    usage = Counter()
    records = []
    actor = pilot.bound(freeze / 'actor.json', protocol['actor'])
    gold = pilot.bound(freeze / 'reference.json', protocol['reference'])
    for i, (raw, ref, completion) in enumerate(zip(actor, gold, model['completed'], strict=True), 1):
        req = decode(GeneratedRequest, raw)
        attempt = freeze / 'attempts' / f'case-{i:02}'
        state = chat.inspect_chat_attempt(attempt)
        saved = pilot.read(attempt / 'generated-request.json')
        pilot.require(req.case.case_id == ref['case_id'] and saved['request'] == raw
                      and state['state'] == 'completed' and state['dispatch_started'], 'Request or journal mismatch')
        caps = decode(chat.ChatCapabilities, saved['capabilities'])
        limits = decode(chat.ChatLimits, saved['limits'])
        result = chat.replay_chat(attempt / 'chat-exchange.json', req, caps, limits)
        pilot.require(canonical(completion) == canonical(dict(case=i, state=state, disposition=result.disposition,
            usage=result.accounted_usage, usage_basis=result.usage_basis)), 'Per-case reported execution differs')
        pilot.require(result.usage_basis == 'adapter_reported' and result.accounted_usage.cost_usd == 0,
                      'Unexpected usage basis or cost')
        usage.update(input_tokens=result.accounted_usage.input_tokens, output_tokens=result.accounted_usage.output_tokens)
        literal = matched_extractor.extract(req)
        text, source = (f'Reported value: {literal[0]}.', literal[1]) if literal else ('', None)
        baseline = assess_span_selection(req, preflight.envelope(req, text, source))
        observed = dict(model=score_response(result.assessment, ref), deterministic=score_response(baseline, ref))
        stratum = 'source_withheld' if ref['expected'] is None else 'answerable'
        success = 'warranted_abstention' if ref['expected'] is None else 'supported_answer'
        for name, outcome in observed.items():
            totals[f'{name}/{stratum}'][outcome] += 1
        wins = [name for name, outcome in observed.items() if outcome == success]
        paired[stratum]['both' if len(wins) == 2 else wins[0] + '_only' if wins else 'neither'] += 1
        records.append(dict(case_id=ref['case_id'], pmcid=ref['pmcid'], pair=ref['pair'],
                            stratum=stratum, expected=ref['expected'], request_sha256=fingerprint(req),
                            model_disposition=result.disposition, deterministic_proposal=text or None,
                            deterministic_source=source, outcomes=observed))
    pilot.require(usage['input_tokens'] <= protocol['max_input_tokens']
                  and usage['output_tokens'] <= protocol['max_output_tokens'], 'Usage exceeds frozen budget')
    pilot.save(output, dict(protocol=anchor, paper_count=8, scheduled=SCHEDULE, totals=totals,
                           paired=paired, rows=records, usage=usage, provider_usd=0, retries=0))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='stage', required=True)
    for stage, paths, with_anchor in (
        ('prepare', ('collection', 'prior', 'exposure', 'output'), False),
        ('verify', ('freeze', 'collection'), True),
        ('execute', ('freeze', 'collection', 'model'), True),
        ('score', ('freeze', 'collection', 'output'), True),
    ):
        command = commands.add_parser(stage)
        for path in paths:
            command.add_argument(path, type=Path)
        if with_anchor:
            command.add_argument('--sha256', required=True)
    args = parser.parse_args()
    if args.stage == 'prepare':
        prepare(args.collection, args.prior, args.exposure, args.output)
        print(pilot.digest((args.output / 'protocol.json').read_bytes()))
    elif args.stage == 'score':
        score(args.freeze, args.sha256, args.collection, args.output)
    else:
        verify_freeze(args.freeze, args.sha256, args.collection)
        if args.stage == 'execute':
            model_batch.execute(args.freeze, args.model, args.sha256)


if __name__ == '__main__':
    main()
