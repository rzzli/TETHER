"""Replay the frozen A04 retrieval experiment from its original article collection."""
import argparse
from pathlib import Path
from tempfile import TemporaryDirectory

from tether_engine.serde import canonical, parse_json

from . import pilot


def check_rankings(recorded, replayed):
    """Require the entire ordered schedule. Wall times can differ on replay."""
    if recorded.keys() != replayed.keys() or recorded['protocol'] != replayed['protocol']:
        raise ValueError('Ranking protocol or fields differ')
    if len(recorded['rows']) != len(replayed['rows']):
        raise ValueError('Ranking count differs from the replayed schedule')
    for saved, fresh in zip(recorded['rows'], replayed['rows'], strict=True):
        elapsed = saved.get('elapsed_ns')
        if type(elapsed) is not int or elapsed < 0:
            raise ValueError('Invalid recorded ranking duration')
        if canonical(saved) != canonical(dict(fresh, elapsed_ns=elapsed)):
            raise ValueError('Ranking differs from replay for ' + fresh['id'])


def verify(run, collection):
    with TemporaryDirectory() as temporary:
        work = Path(temporary)
        prepared = work / 'replay'
        pilot.prepare(collection, prepared)
        for name in ('protocol.json', 'actor.json', 'evaluator.json'):
            if (run / name).read_bytes() != (prepared / name).read_bytes():
                raise ValueError('Original-source reconstruction differs for ' + name)
        pilot.rank(prepared)
        captured = (run / 'rankings.json').read_bytes()
        recorded = parse_json(captured)
        check_rankings(recorded, pilot.read(prepared / 'rankings.json'))

        # Score the verified bytes, preserving the original durations and file digest.
        scoring = work / 'score'
        scoring.mkdir()
        for name in ('protocol.json', 'evaluator.json'):
            (scoring / name).write_bytes((prepared / name).read_bytes())
        (scoring / 'rankings.json').write_bytes(captured)
        pilot.evaluate(scoring)
        if (run / 'evaluation.json').read_bytes() != (scoring / 'evaluation.json').read_bytes():
            raise ValueError('Published evaluation differs from the verified rankings')
        return len(recorded['rows'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    parser.add_argument('collection', type=Path)
    args = parser.parse_args()
    print(f'{verify(args.run, args.collection)} rankings and the evaluation reproduced')
