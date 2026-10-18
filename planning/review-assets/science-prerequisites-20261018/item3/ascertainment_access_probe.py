"""Unauthenticated source-access and local archive metadata only; never query study rows."""
import datetime as dt
import hashlib
import html
import json
from pathlib import Path
import re
import urllib.error
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[4]
STAMP = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
OUT = ROOT / 'data/derived/science-prerequisites-20261018' / ('ascertainment-access-' + STAMP)
OUT.mkdir(parents=True, exist_ok=False)


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


opener = urllib.request.build_opener(NoRedirect)
urls = {
    'aact-landing': 'https://aact.ctti-clinicaltrials.org/landing',
    'aact-snapshots': 'https://aact.ctti-clinicaltrials.org/snapshots',
    'aact-session': 'https://aact.ctti-clinicaltrials.org/session/new',
    'aact-legacy-2026-list': 'https://aact.ctti-clinicaltrials.org/downloads/snapshots?type=pgdump&year=2026',
    'aact-api-snapshots': 'https://aact.ctti-clinicaltrials.org/api/v1/snapshots',
    'ctgov-about-api': 'https://clinicaltrials.gov/data-api/about-api',
    'ctgov-api-docs': 'https://clinicaltrials.gov/data-api/api',
    'ctgov-version': 'https://clinicaltrials.gov/api/v2/version',
    'ctgov-openapi-probe': 'https://clinicaltrials.gov/api/v2/openapi.json',
}
receipts = []
for name, url in urls.items():
    checked = dt.datetime.now(dt.timezone.utc).isoformat()
    try:
        response = opener.open(urllib.request.Request(url, headers={'User-Agent': 'Project source-access qualification/1.0'}), timeout=30)
    except urllib.error.HTTPError as error:
        response = error
    except Exception as error:
        receipts.append({'name': name, 'source_url': url, 'checked_at_utc': checked, 'error': repr(error)})
        continue
    with response:
        body = response.read(2_000_001)
        assert len(body) <= 2_000_000, 'Metadata response exceeded bound'
        raw = body.decode('utf-8', errors='replace')
        # Public HTML forms contain ephemeral CSRF values. They are not access credentials,
        # but have no role in the evidence and are deliberately omitted from retention.
        redacted = re.sub(r'(<meta\s+name="csrf-token"\s+content=")[^"]*', r'\1[REDACTED]', raw)
        redacted = re.sub(r'(<input[^>]*name="authenticity_token"[^>]*value=")[^"]*', r'\1[REDACTED]', redacted)
        target = OUT / (name + '.response.txt')
        target.write_text(redacted, encoding='utf-8')
        receipts.append({
            'name': name, 'source_url': url, 'checked_at_utc': checked,
            'http_status': response.code,
            'headers': {k: response.headers[k] for k in ('Content-Type', 'Content-Length', 'Date', 'Last-Modified', 'Location') if response.headers.get(k)},
            'response_bytes': len(body), 'original_response_sha256': hashlib.sha256(body).hexdigest(),
            'retained_body': str(target.relative_to(ROOT)), 'retained_body_sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
            'retention_transform': 'UTF-8; public form CSRF values redacted; response headers omit cookies',
        })
write(OUT / 'http-receipts.json', receipts)

prior = json.loads((ROOT / 'planning/review-assets/claude-review-20261017/results/aact-archives.json').read_text())
by_path = {str(Path(row['path'])): row for row in prior['results']}
inventory = []
for archive in sorted(Path('E:/projects_data/drug_target_agents_data/raw/aact_snapshots').rglob('*.zip')):
    stat = archive.stat()
    with zipfile.ZipFile(archive) as z:
        members = [{'name': x.filename, 'uncompressed_bytes': x.file_size, 'compressed_bytes': x.compress_size,
                    'zip_created_local_unspecified_timezone': list(x.date_time), 'central_directory_crc32': f'{x.CRC:08x}'} for x in z.infolist()]
    previous = by_path.get(str(archive))
    inventory.append({'path': str(archive), 'bytes': stat.st_size,
                      'filesystem_mtime_utc': dt.datetime.fromtimestamp(stat.st_mtime, dt.timezone.utc).isoformat(),
                      'prior_hash_verification': previous, 'prior_hash_recomputed_this_run': False,
                      'members': members, 'contents_decompressed': False,
                      'date_precision_note': 'ZIP member times have unspecified timezone; filesystem mtime is local possession evidence, not first-publication evidence.'})
write(OUT / 'local-archive-inventory.json', inventory)

evidence = []
for relative in [
    'planning/protocols/science-prerequisites-v0.1.json',
    'planning/review-assets/ordered-execution-20261017/aact2026-qualification.json',
    'planning/review-assets/claude-review-20261017/results/aact-archives.json',
    'data/manifests/public/2026-10-16-aact-restoration-access.json',
    'data/manifests/public/2026-10-17-aact-five-acquisition.json',
]:
    p = ROOT / relative
    evidence.append({'path': relative, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()})
write(OUT / 'prior-evidence-crosswalk.json', evidence)
write(OUT / 'run-scope.json', {
    'created_at_utc': dt.datetime.now(dt.timezone.utc).isoformat(), 'role': 'evaluation_only',
    'origin_at': '2025-01-01T00:00:00Z', 'occurrence_horizon_at': '2026-01-01T00:00:00Z',
    'proposed_ascertainment_at': '2026-04-01T00:00:00Z', 'proposed_calendar_days': 90,
    'lag_allowance_qualified': False, 'ascertainment_coverage_complete': False,
    'new_archive_download_count': 0, 'clinical_table_queries': 0, 'candidate_outcome_requests': 0,
    'endpoint_joins': 0, 'database_restored': False, 'provider_spend_usd': 0,
    'original_receipts_modified': False, 'credentials_used': False,
    'official_aact_filename_for_20260401': None,
    'filename_unverified_reason': 'Official listing redirects to sign-in; API metadata returns invalid_api_key; no authorized credentials used.',
})
print(json.dumps({'output': str(OUT), 'http_statuses': {r['name']: r.get('http_status', r.get('error')) for r in receipts}, 'local_archives': len(inventory)}, indent=2))
