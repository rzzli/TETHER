"""Archive explicitly selected public HTTP sources with bounded reads and receipts."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import argparse
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


def is_challenge(body):
    lower = body[:200000].lower()
    return any(marker in lower for marker in (
        b'<title>checking your browser', b'<title>access denied', b'<title>just a moment',
        b'const challengeid =', b'id="cookie-required"', b'checking your browser - recaptcha',
        b'const pow_challenge =', b'cloudpmc-viewer-pow'))


def retain(entries, out):
    ids = [e['source_id'] for e in entries]
    if len(ids) != len(set(ids)) or not all(re.fullmatch(r'[A-Za-z0-9_-]+', x) for x in ids):
        raise ValueError('Unique safe source IDs required')
    for entry in entries:
        url = urlsplit(entry['url'])
        if url.scheme != 'https' or not url.hostname or url.username or url.password:
            raise ValueError('Public HTTPS sources only')
    out.mkdir(exist_ok=False)
    def fetch(entry):
        row = {**entry, 'retrieved_at_utc': datetime.now(timezone.utc).isoformat(), 'role': 'evaluation_only'}
        try:
            with urlopen(Request(entry['url'], headers={'User-Agent': 'AsOf-development-research/0.2'}), timeout=45) as response:
                body = response.read(32 * 1024 * 1024 + 1)
                if len(body) > 32 * 1024 * 1024:
                    raise ValueError('Source exceeds 32 MiB archival bound')
                row.update(http_status=response.status, final_url=response.url,
                           content_type=response.headers.get('Content-Type'))
            (out / (entry['source_id'] + '.body')).write_bytes(body)
            challenge = is_challenge(body)
            row.update(status='challenge_page' if challenge else 'retrieved_unreviewed', bytes=len(body),
                       sha256=hashlib.sha256(body).hexdigest())
        except Exception as exc:
            row.update(status='failed', error=repr(exc))
        (out / (entry['source_id'] + '.receipt.json')).write_text(json.dumps(row, indent=2) + '\n', encoding='utf-8')
        print(json.dumps({'source_id': entry['source_id'], 'status': row['status']}), flush=True)
        return row
    with ThreadPoolExecutor(max_workers=2) as pool:
        receipts = list(pool.map(fetch, entries))
    (out / 'index.json').write_text(json.dumps(receipts, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sources', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    retain(json.loads(args.sources.read_text(encoding='utf-8')), args.output)
