"""Retain public primary-page response bytes for evaluator provenance.

An HTTP response is not proof of full-text access or scientific correctness. The
original reviewers' access-depth declarations remain distinct from these captures.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen

from asof.serde import read_json, sha256_file, write_json


def capture(url, root):
    key = hashlib.sha256(url.encode()).hexdigest()
    record = {'requested_url': url, 'retrieved_at_utc': datetime.now(timezone.utc).isoformat(),
              'capture_kind': 'uninterpreted_http_response', 'reviewer_access_depth': 'not_inferred'}
    try:
        if not url.startswith('https://'):
            raise ValueError('Public source capture requires HTTPS')
        request = Request(url, headers={'User-Agent': 'AsOfResearch/0.2 (public scientific source archiving)'})
        with urlopen(request, timeout=25) as response:
            if not response.url.startswith('https://'):
                raise ValueError('Source redirected outside HTTPS')
            data = response.read(16 * 1024 * 1024 + 1)
            if len(data) > 16 * 1024 * 1024:
                raise ValueError('Primary page exceeded capture size limit')
            path = root / (key + '.bin')
            with path.open('xb') as stream:
                stream.write(data)
            record.update(status='captured', http_status=response.status, final_url=response.url,
                          content_type=response.headers.get('Content-Type'), path=path.name,
                          bytes=len(data), sha256=sha256_file(path))
    except Exception as error:
        record.update(status='capture_failed', error_type=type(error).__name__, error=str(error))
    # Every attempt is retained, including access failures. Never retry invisibly.
    write_json(root / (key + '.json'), record)
    return record


def archive(panel_paths, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    panels = [read_json(p) for p in panel_paths]
    urls = sorted({s['url'] for p in panels for c in p['cases'] for s in c['primary_sources']})
    write_json(output / 'request.json', {'panels': [{'path':str(p), 'sha256':sha256_file(p)} for p in panel_paths],
                                      'urls': urls, 'max_workers':4, 'retry_count':0})
    with ThreadPoolExecutor(max_workers=4) as pool:
        rows = list(pool.map(lambda url: capture(url, output), urls))
    report = {'schema_version':1, 'role':'evaluation_only', 'captures':rows,
              'captured':sum(r['status']=='captured' for r in rows),
              'failed':sum(r['status']=='capture_failed' for r in rows),
              'scientific_validation':'not_established_by_http_success'}
    write_json(output / 'report.json', report)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--panels', nargs='+', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    result = archive(args.panels, args.output)
    print(json.dumps({'captured':result['captured'], 'failed':result['failed']}))
