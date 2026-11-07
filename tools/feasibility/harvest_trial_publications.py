"""Retain exact-NCT Europe PMC discovery results; relevance/outcomes need review."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import argparse
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def harvest(selected, output):
    output.mkdir(exist_ok=False)
    identifiers = [x['origin_record']['nct_id'] for x in selected]
    if len(identifiers) != len(set(identifiers)) or not all(re.fullmatch(r'NCT\d{8}', x) for x in identifiers):
        raise ValueError('Unique canonical NCT IDs required')
    def fetch(nct):
        query = '"' + nct + '"'
        url = 'https://www.ebi.ac.uk/europepmc/webservices/rest/search?' + urlencode(
            {'query': query, 'format': 'json', 'resultType': 'core', 'pageSize': 1000})
        receipt = {'nct_id': nct, 'url': url, 'query': query, 'retrieved_at_utc': datetime.now(timezone.utc).isoformat(),
                   'role': 'evaluation_only', 'relevance': 'unreviewed_exact_identifier_search_not_trial_result_validation'}
        try:
            with urlopen(Request(url, headers={'User-Agent': 'TETHER-research/0.2'}), timeout=45) as response:
                body = response.read(32 * 1024 * 1024 + 1)
                if len(body) > 32 * 1024 * 1024:
                    raise ValueError('Response exceeds bounded discovery limit')
                receipt.update(http_status=response.status, final_url=response.url)
            value = json.loads(body)
            (output / (nct + '.json')).write_bytes(body)
            rows = value.get('resultList', {}).get('result', [])
            receipt.update(status='retrieved', bytes=len(body), sha256=hashlib.sha256(body).hexdigest(),
                           hit_count=value['hitCount'], retained_hits=len(rows),
                           complete_page=value['hitCount'] <= len(rows))
        except Exception as exc:
            receipt.update(status='failed', error=repr(exc))
        (output / (nct + '.receipt.json')).write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
        print(json.dumps({k: receipt.get(k) for k in ('nct_id', 'status', 'hit_count', 'retained_hits')}), flush=True)
        return receipt
    with ThreadPoolExecutor(max_workers=2) as pool:
        receipts = list(pool.map(fetch, identifiers))
    (output / 'index.json').write_text(json.dumps(receipts, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--selected', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    harvest(json.loads(args.selected.read_text()), args.output)
