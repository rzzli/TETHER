"""Independent actual Q06 ZIP closure; no packager imports or legacy unpacking."""
from pathlib import Path, PurePosixPath
from datetime import datetime, timezone
import csv
import hashlib
import io
import json
import posixpath
import re
import zipfile
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
STAGE = ROOT / 'data/cache/tether-q06/working-v2'
ARCHIVE = STAGE / 'data/derived/tether-review-0.5.0-q06-first.zip'
REPEAT = STAGE / 'data/derived/tether-review-0.5.0-q06-repeat.zip'
checks = []
def sha(raw): return hashlib.sha256(raw).hexdigest()
def check(name, condition, detail=None): checks.append(dict(name=name,passed=bool(condition),detail=detail))
raw = ARCHIVE.read_bytes()
check('whole_zip_expected_sha', sha(raw) == '10a2d79798e5b0ec97042ae3f599df89c75d62b9b46b45b51cd29866c737492d')
check('whole_zip_expected_size', len(raw) == 21694289)
check('two_fresh_process_packets_byte_equal', raw == REPEAT.read_bytes())
with zipfile.ZipFile(io.BytesIO(raw)) as archive:
    names = archive.namelist()
    records = archive.infolist()
    entries = {name: archive.read(name) for name in names}
check('78_unique_safe_member_names', len(names) == len(set(names)) == len({n.casefold() for n in names}) == 78 and all(not n.startswith('/') and '\\' not in n and '..' not in PurePosixPath(n).parts for n in names))
check('stored_members_no_encryption', all(r.compress_type == zipfile.ZIP_STORED and not r.flag_bits & 1 for r in records))

# Literal document/results categories plus the actual current package source
# file inventory; no package source_inventory() or allowlist helper is imported.
expected = {'README.md', 'TETHER-QUALIFICATION.json', 'PACKET-MANIFEST.json', 'documentation/CURRENT-SOFTWARE.md', 'documentation/SOFTWARE-QUALIFICATION.json', 'software/tether_target_agents-0.5.0-py3-none-any.whl'}
expected.update('paper/' + n for n in ['manuscript.md','supplement.md','references.bib','references.json','RELATED-WORK-SOURCE-AUDIT.md','AUTHOR-DECLARATIONS.md','tether-source-reporting-preprint.pdf'])
expected.update('reproduction/' + n for n in ['README.md','qualification.json','RELEASE-RECORD.json','asof-research-artifact-0.1.0.zip'])
expected.update('paper/results/' + n for n in ['README.md','ARTIFACTS.json'])
for stem in ['figure1-flow','figure2-availability','figure3-controls']:
    expected.update('paper/results/figures/' + stem + suffix for suffix in ['.pdf','.svg','-preview.png','-data.json','-caption.md'])
for stem in ['constructed_control_verdicts','constructed_policy_summary','decision_schedule','native_case_results','native_fact_accounting','native_missingness','native_operation_resources','output_schedule','paired_discordance','paired_verdict_cells','resource_phases']:
    expected.update('paper/results/tables/' + stem + ext for ext in ['.csv','.md'])
source_root = ROOT / 'packages/tether'
source_files = list((source_root/'src/tether').rglob('*.py'))
check('current_runtime_source_count', len(source_files) == 18)
expected.update('software/source/packages/tether/' + p.relative_to(source_root).as_posix() for p in source_files)
expected.update('software/source/packages/tether/' + n for n in ['README.md','LICENSE','pyproject.toml','uv.lock'])
check('independently_assembled_exact_members', set(names) == expected, dict(missing=sorted(expected-set(names)),extra=sorted(set(names)-expected)))

manifest = json.loads(entries['PACKET-MANIFEST.json'])
qual = json.loads(entries['TETHER-QUALIFICATION.json'])
check('manifest_hash', sha(entries['PACKET-MANIFEST.json']) == 'ac31868f89e94d89a670274ffa7e1b6e89dbf2fd339f4295c009f3521e5fc62d')
check('qualification_hash', sha(entries['TETHER-QUALIFICATION.json']) == '4a8ee7176d2839cc0b1c5ed0ed480e0007ebe6e788372ee7bbc999450647623c')
check('qualification_exact_reviewed_root_copy', entries['TETHER-QUALIFICATION.json'] == (ROOT/'paper/release/tether-v2/QUALIFICATION.json').read_bytes())
check('manifest_closure_self_excluded', set(manifest['files']) == set(names)-{'PACKET-MANIFEST.json'} and manifest['manifest_self_excluded'] is True)
check('qualification_closure', set(qual['payloads']) == set(names)-{'PACKET-MANIFEST.json','TETHER-QUALIFICATION.json'})
for name, descriptor in manifest['files'].items():
    check('manifest_bytes:' + name, descriptor['sha256'] == sha(entries[name]) and descriptor['bytes'] == len(entries[name]))
for name, descriptor in qual['payloads'].items():
    check('qualification_binding:' + name, descriptor == manifest['files'][name])
fixed = dict(publication_authorized=False, owner_declarations='deferred', author_acceptance='pending', submission_ready=False, public_deposit=None, scientific_validation='not_established', study_independence='not_established', tether_version='0.5.0', compatibility_engine_version='0.3.11', role='evaluation_only', agent_visible=False)
for label, record in [('qualification',qual),('manifest',manifest)]:
    check(label + '_limited_scope', all(type(record[k]) is type(v) and record[k] == v for k,v in fixed.items()))

source_map = {
    'paper/manuscript.md': STAGE/'paper/manuscript.md',
    'paper/supplement.md': STAGE/'paper/supplement.md',
    'paper/tether-source-reporting-preprint.pdf': ROOT/'paper/revisions/20261102/tether-source-reporting-preprint-v2.pdf',
    'documentation/CURRENT-SOFTWARE.md': ROOT/'paper/release/tether-v2/CURRENT-SOFTWARE.md',
    'documentation/SOFTWARE-QUALIFICATION.json': ROOT/'paper/release/tether-v2/SOFTWARE-QUALIFICATION.json',
    'reproduction/asof-research-artifact-0.1.0.zip': ROOT/'data/derived/preprint-p09-release-20261101T232900Z/asof-research-artifact-0.1.0.zip',
    'software/tether_target_agents-0.5.0-py3-none-any.whl': ROOT/'data/cache/tether-050-qualified-build/wheels/tether_target_agents-0.5.0-py3-none-any.whl',
}
for name, path in source_map.items(): check('reviewed_exact_payload:' + name, entries[name] == path.read_bytes())
check('PDF_previously_reviewed_pin', sha(entries['paper/tether-source-reporting-preprint.pdf']) == 'b6a93fadbd309ba03fe2497d0e59fcd5bf4344d7ed7cd3693840ee87485b5f23')
check('opaque_P09_historical_pin', sha(entries['reproduction/asof-research-artifact-0.1.0.zip']) == 'f4d7ab4bb1a0b79c0ecadbac15891f4cc2925abe624298e8a48a762190b6782e')
for p in source_files + [source_root/n for n in ['README.md','LICENSE','pyproject.toml','uv.lock']]:
    name = 'software/source/packages/tether/' + p.relative_to(source_root).as_posix()
    check('current_source_exact:' + name, entries[name] == p.read_bytes())
with zipfile.ZipFile(io.BytesIO(entries['software/tether_target_agents-0.5.0-py3-none-any.whl'])) as wheel:
    for p in source_files:
        name = p.relative_to(source_root/'src').as_posix()
        check('wheel_python_exact:' + name, wheel.read(name) == p.read_bytes())
    check('wheel24_members', len(wheel.namelist()) == 24)
    check('wheel_version_and_engine_dependency', b'Version: 0.5.0' in wheel.read('tether_target_agents-0.5.0.dist-info/METADATA') and b'asof-target-agents==0.3.11' in wheel.read('tether_target_agents-0.5.0.dist-info/METADATA'))

result_manifest = json.loads(entries['paper/results/ARTIFACTS.json'])
check('portable_result_manifest_fixed', sha(entries['paper/results/ARTIFACTS.json']) == 'da802210539141fd7e25418d1440b1f749c3e5d16e6b62ddc7562db01cc11eb4')
check('37_historical_payloads', len(result_manifest['historical_payload_comparisons']) == 37)
for descriptor in result_manifest['historical_payload_comparisons']:
    name = 'paper/results/' + descriptor['path']
    old = ROOT / name
    check('historical_result_exact:' + descriptor['path'], entries[name] == old.read_bytes() and sha(entries[name]) == descriptor['sha256'] and len(entries[name]) == descriptor['bytes'] and descriptor['matches_historical'] is True)

link_count = 0
for name in names:
    if not name.endswith('.md'): continue
    text = entries[name].decode('utf-8')
    for match in re.finditer(r'\[[^\]\n]+\]\((?:<([^>\n]+)>|([^\)\n]+))\)', text):
        target = (match.group(1) or match.group(2)).strip()
        parsed = urlsplit(target)
        if parsed.scheme in ['http','https']: continue
        if not parsed.path: continue
        link_count += 1
        resolved = posixpath.normpath(posixpath.join(posixpath.dirname(name), unquote(parsed.path)))
        check('local_markdown_link:' + name + ':' + target, not parsed.scheme and not resolved.startswith('../') and (resolved in names or any(n.startswith(resolved.rstrip('/')+'/') for n in names)))
for name in ['README.md','documentation/CURRENT-SOFTWARE.md','documentation/SOFTWARE-QUALIFICATION.json','TETHER-QUALIFICATION.json','PACKET-MANIFEST.json']:
    text = entries[name].decode('utf-8')
    check('no_local_machine_paths:' + name, not re.search(r'(?i)[A-Z]:[\\/]|/Users/|/home/|C:\\\\Users', text))
check('unchanged_zip_after_review', ARCHIVE.read_bytes() == raw)
report = dict(schema_version=1, checked_at_utc=datetime.now(timezone.utc).isoformat(), status='PASS_ACTUAL_PACKET_CLOSURE' if all(c['passed'] for c in checks) else 'FINDINGS', archive=dict(path=str(ARCHIVE),sha256=sha(raw),bytes=len(raw),members=len(names)), manifest_sha256=sha(entries['PACKET-MANIFEST.json']),qualification_sha256=sha(entries['TETHER-QUALIFICATION.json']),checks=checks,local_markdown_links=link_count,checker_sha256=sha(Path(__file__).read_bytes()), scope='Exact actual ZIP bytes/membership/source/result/software/qualification bindings and Markdown link closure; no legacy archive unpacking, raw scans, study rerun or model calls.', P09_archive_opened_as_nested_zip=False)
out = HERE / ('PACKET-CHECK-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.json')
with out.open('x',encoding='utf-8') as f: json.dump(report,f,indent=2)
print(json.dumps(dict(record=str(out),status=report['status'],checks=len(checks),local_markdown_links=link_count,findings=[c for c in checks if not c['passed']]),indent=2))
