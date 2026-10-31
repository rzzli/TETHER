"""Retain strategic metadata review; no subject imports, targets or experiments."""
from pathlib import Path
import datetime
import hashlib
import json
import re
import subprocess
from urllib.parse import unquote

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[2]
PREFIX = 'R09-STRATEGIC-PRIORITY-REVIEW-v1'
MD = BASE / (PREFIX + '.md')


def pin(path):
    path = Path(path)
    if not path.is_absolute():
        path = ROOT / path
    raw = path.read_bytes()
    return dict(path=path.relative_to(ROOT).as_posix(), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def cite(path, start, end, meaning):
    return dict(path=path, line_start=start, line_end=end, supports=meaning)


opus = 'docs/Opus_20261026T050236Z_review.md'
plan = 'planning/Project Recovery and Evaluation Plan 2026-10-26.md'
phase = 'planning/decisions/2026-10-26-phase-scope.md'
r07 = 'planning/review-assets/recovery-step7-20261026/DISPOSITION.md'
bridge = 'planning/review-assets/recovery-step9-native-bank-bridge-20261030/NATIVE-BANK-TICKET-BRIDGE-PROPOSAL-v2.md'
inputs = [opus, plan, phase, r07,
          'planning/review-assets/recovery-step7-20261026/gate-correction.md',
          'planning/Project Progress Reassessment 2026-10-31 - Component Guards.md', bridge,
          'planning/review-assets/recovery-step9-native-bank-bridge-20261030/NATIVE-BANK-TICKET-BRIDGE-INDEPENDENT-STATIC-REVIEW-v1.json',
          'planning/review-assets/recovery-step5-20261026/diagnostic-design.md',
          'planning/review-assets/recovery-step5-20261026/acceptance.json',
          'planning/review-assets/recovery-step8-20261026/source-feasibility.md',
          'planning/review-assets/recovery-step8-20261026/bounded-source-qualification.md',
          'planning/review-assets/recovery-step8-20261026/metadata-followup-v1.md',
          'planning/review-assets/recovery-step9-collected-composition-20261027/acceptance.json',
          'planning/review-assets/recovery-step9-collected-composition-20261027/NEXT-GATE-AUDIT.md',
          'planning/review-assets/recovery-step9-generation-contract-20261028/acceptance.json',
          'planning/review-assets/recovery-step9-native-duration-20261028/RESOURCE-RISK-NOTE.md',
          'planning/review-assets/recovery-step9-generation-contract-20261028/NEXT-GATE-CRITICAL-REVIEW.md',
          'planning/review-assets/recovery-step9-entry-source5-20261030/SOURCE5-ROOT-ACCEPTANCE-v1.json',
          'planning/review-assets/recovery-step9-entry-source5-20261030/SOURCE5-NATIVE25-INDEPENDENT-ACTUAL-REVIEW-v1.json',
          'docs/AUTHORITY_FOUR_ARM_COMPARISON.md', 'docs/INTERPRETATION_INTERFACE.md',
          'docs/INTERPRETATION_GENERATION.md', 'docs/NATIVE_INTERPRETATION.md',
          'src/asof/study/authority_four_arm.py', 'src/asof/study/interpretation_interface.py',
          'src/asof/study/interpretation_generation.py', 'src/asof/study/session.py',
          'src/asof/study/recorded.py', 'src/asof/study/fixed_evidence.py']
findings = [
    dict(id='S1', severity='high', classification='priority_mismatch',
         finding='The private same-Core CPython bank/physical14 stack is not established as a prerequisite of the smallest T6/H5 comparison.',
         evidence=[cite(opus, 18, 28, 'Capability, human references and labels are the main bottlenecks.'),
                   cite(opus, 153, 178, 'Governance overhead and capability/interface confounding.'),
                   cite(plan, 139, 157, 'Only relevant infrastructure, no broad rewrite prerequisite.'),
                   cite(plan, 262, 271, 'R09 smallest interpretable comparison requirements.'),
                   cite(bridge, 9, 23, 'Substantive planned kernel/extension changes, not a delivered scientific capability.')],
         recommendation='Defer optional native implementation until a scheduled scientific consumer and demonstrated blocking defect justify it.'),
    dict(id='S2', severity='high', classification='stop_rule_conflict',
         finding='Successive locally valid systems proofs can violate the controlling bounded-diagnostic and proportional-governance intent.',
         evidence=[cite(plan, 213, 224, 'Redesign before another full controller stack; no unbounded converter search.'),
                   cite(plan, 238, 249, 'Choose a direction, retain negative result, no twenty-case expansion without useful answer.'),
                   cite(plan, 379, 385, 'Development versus confirmatory governance; invariants preserved.'),
                   cite(r07, 11, 22, 'Stop this native version; retain extractive framework; capacity unidentifiable.')],
         recommendation='Record a prospective priority disposition without weakening, replaying or falsely passing any frozen native contract.'),
    dict(id='S3', severity='medium', classification='available_minimal_deliverable',
         finding='Accepted recorded comparison, quote/post-validation and pure generation support an honest development capability/negative-feasibility account now.',
         evidence=[cite('docs/AUTHORITY_FOUR_ARM_COMPARISON.md', 14, 58, 'Collected-source recorded mechanics, zero actual model calls and explicit source limits.'),
                   cite('src/asof/study/authority_four_arm.py', 80, 101, 'Native configuration optional; recorded remains default.'),
                   cite('docs/INTERPRETATION_INTERFACE.md', 36, 80, 'Generated assertions separate from exact source strings and strict post-validation.'),
                   cite('src/asof/study/interpretation_generation.py', 62, 87, 'Pure preparation declares no execution authority/native conformance.')],
         recommendation='Reuse retained evidence. Do not rerun the scripted demonstration or mislabel it as a model/H5 result.'),
    dict(id='S4', severity='high', classification='external_science_dependencies',
         finding='Human references/domain coverage, fresh source sufficiency and an approved useful capability condition remain unresolved; clinical labels are a separate deferred route.',
         evidence=[cite(phase, 20, 51, 'Resource, recruitment and proportional-governance decisions.'),
                   cite(r07, 52, 77, 'Scientific references/fresh generation gates and permitted preparation.'),
                   cite('planning/review-assets/recovery-step8-20261026/bounded-source-qualification.md', 1, 25, 'Technically extracted, scientifically unqualified development contexts.'),
                   cite('planning/Project Progress Reassessment 2026-10-31 - Component Guards.md', 41, 66, 'Current R/HR and data/science limitations.')],
         recommendation='Prepare exact owner-facing intake/unblock checklist, then stop at the genuine dependent gate; agents cannot substitute for human submissions.'),
    dict(id='S5', severity='high', classification='integrated_fit_unestablished',
         finding='Retained295.922/300s simulation excludes actual startup/inference; native-cell correctness does not establish integrated fit.',
         evidence=[cite('docs/NATIVE_INTERPRETATION.md', 85, 114, 'Simulation/cost limits and actual qualification open.'),
                   cite('planning/review-assets/recovery-step9-native-duration-20261028/RESOURCE-RISK-NOTE.md', 1, 24, 'Uncontrolled timing pair and no actual inference fit.')],
         recommendation='Choose scientific consumer before scoping a measured bottleneck and prospective finite resource test.')]
constraints = [
    dict(id='U1', origin='explicit_user_project_plans', rule='Chronology, complete lineage, evaluator isolation, immutable admitted evidence, failure/accounting preservation, empty unvalidated features/null probabilities.', binding='Every project deliverable.'),
    dict(id='U2', origin='explicit_user_approved_execution_boundaries', rule='$0 spending; no unapproved model/source acquisition/payment; downloader and stopped monitor untouched.', binding='Current execution.'),
    dict(id='U3', origin='explicit_current_user_goal', rule='Validated task progression, honest blocker, timestamped commits, major-step reassessment.', binding='Current project goal; does not activate every optional branch.'),
    dict(id='P1', origin='accepted_recovery_scientific_protocol', rule='Independent source-only human references, fresh exposure-qualified cases and masked judgments before fresh R10/R12 generation/scientific acceptance.', binding='Independent H5 claims; no AI substitution.'),
    dict(id='P2', origin='accepted_recovery_development_governance', rule='Minimal necessary infrastructure, smallest comparison, bounded diagnostics, unresolved capacity when stronger condition unavailable.', binding='Priority and claim decisions.'),
    dict(id='A1', origin='agent_authored_optional_native_design', rule='Same Core/Origin/nonce,256B cell,native-before-Python publication,private tickets,physical14/exact bank limits.', binding='Required to execute/claim that route; not an original H5 endpoint.'),
    dict(id='A2', origin='agent_authored_frozen_prospective_conformance_route', rule='Distinct new84/actual vocabulary/EOG/full physical and resource contract.', binding='No weakening/replay/false pass; may be explicitly deferred with history intact.')]
readiness = [
    dict(id='G1', prerequisite='Independent human references and domain coverage', state='externally_pending', owner='Two relevant source-only submissions, conflicts/exposure/timing and adjudication coverage.', agents='Existing clean packets/intake/masking; no AI answer key or early candidate follow-up.'),
    dict(id='G2', prerequisite='Useful capability condition', state='unresolved_under_approved_assets', owner='Unavailable alternative model/access or a concretely capped resource change if desired.', agents='Matched bounded proposal; R05 inventory is dated/scoped, not a global model census. No automatic download/spend.'),
    dict(id='G3', prerequisite='Fresh source/question sufficiency', state='partial_not_qualified', owner='Domain-qualified source judgment/coverage.', agents='Exposure, linkage, context, rights and question fit; all six fixed article identities already checked. Do not repeat old lookup gaps or select favorable replacements.'),
    dict(id='G4', prerequisite='Integrated resources for chosen future live route', state='unestablished', owner='None yet absent a concrete missing resource/file/permission.', agents='Choose minimal consumer and measured bottleneck first; unchanged ceilings.'),
    dict(id='G5', prerequisite='Clinical labels, chronology and power', state='separately_deferred', owner='Named future source/access/adjudication need only after concrete plan.', agents='36unqualifiedlabels/17of32observablestates/0of12joint-readyclinical are not efficacy labels or R08freshness.'),
    dict(id='G6', prerequisite='Genetics/action/scorer qualification', state='separately_conditional', owner='Estimator/domain-specific judgment or named missing product only if activated.', agents='Full-cis assets do not establish MR/action transfer. Features remain empty/probabilities null.')]
next_actions = [
    dict(order=1, action='Record priority disposition, retain Source5/C79 scopes, defer optional bank/physical14/new84 implementation.', acceptance='History/limits unchanged; reopening requires scheduled scientific consumer and demonstrated blocking defect.'),
    dict(order=2, action='Close one concise R09 capability/negative-feasibility account from retained artifacts.', acceptance='Recorded/simulated/pure/live, source/human/capability/resource gaps and failures explicit; no unnecessary replay or H5 claim.'),
    dict(order=3, action='Prepare exact scientific unblock/intake packet using existing clean exercises.', acceptance='Reviewer role, response path, conflicts/timing and source-only-before-candidate release order; no redundant data/software request.'),
    dict(order=4, action='Only if gates pass, prospectively define smallest fixed-evidence development question/route using packaged infrastructure.', acceptance='Strict semantic validation, source/budget/accounting invariants. GenericJSON would be a separately named option, not inherited native conformance or old-cell repair.'),
    dict(order=5, action='Stop at genuine unavailable scientific/capability prerequisite after bounded preparation.', acceptance='Exact blocker reported; useful extractive framework/negative result retained; H5/project incomplete; no unrelated engineering to avoid stop.')]
text = MD.read_text(encoding='utf-8')
links = []
broken = []
for value in re.findall(r'(?<!!)\[[^\]\n]+\]\((<[^>]+>|[^)\n]+)\)', text):
    target = unquote(value.strip().strip('<>')).split('#', 1)[0]
    if re.match(r'^https?://', target):
        continue
    path = (BASE / target).resolve()
    links.append(dict(target=target, resolved=path.relative_to(ROOT).as_posix()))
    if not path.exists() and path.name != PREFIX + '.json':
        broken.append(target)
codepaths = list((ROOT / 'src/asof/study').rglob('*.py'))
tokens = ('RawCallStore', 'PF14', 'preflight_native_bank', 'physical14')
matches = [dict(path=path.relative_to(ROOT).as_posix(), token=token)
           for path in codepaths for token in tokens if token in path.read_text(encoding='utf-8')]
commit = 'ceab32fd4f6ee7529fc3ed254646e104a465d8bf'
names = subprocess.run(['git', 'ls-tree', '-r', '--name-only', commit, 'planning/review-assets'],
                       capture_output=True, text=True, check=True).stdout.splitlines()
selected = [name for name in names if any(token in name for token in
            ('native', 'preflight', 'unicode', 'entry-source', 'entry-contract', 'real-route'))]
citation_failures = []
for finding in findings:
    for citation in finding['evidence']:
        length = len((ROOT / citation['path']).read_text(encoding='utf-8').splitlines())
        if not 1 <= citation['line_start'] <= citation['line_end'] <= length:
            citation_failures.append(dict(citation=citation, actual_lines=length))
report = dict(schema_version=1,
              status='RECOMMEND_SCIENTIFIC_PRIORITY_REASSESSMENT_DEFER_OPTIONAL_NATIVE_STACK',
              at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
              review_scope='Complete Opus/recovery plan and selected actual package/acceptance metadata. Strategic priority recommendation only; no execution authority or current-doc edits.',
              reviewed_inputs={name: pin(name) for name in inputs}, narrative=pin(MD), reviewer_helper=pin(__file__),
              findings=findings, requirement_provenance_taxonomy=constraints,
              scientific_readiness=readiness, recommended_next_actions=next_actions,
              retained_invariants=['No old experiment replay/healing, response repair or favorable fixture substitution.',
                                   'Unknown/potentially billed attempts not repeated; conservative reservation and measured usage separate.',
                                   'Chronology/lineage/evaluator isolation and original/protected data boundaries retained.',
                                   '$0,no new model/source acquisition,no downloader/monitor change,no raised resource ceilings.',
                                   'No fabricated human consensus, biological absence, clinical probability or H5 completion.',
                                   'Optional native contracts stay strict if reactivated; deferral is not conformance.'],
              architectural_search=dict(paths_scanned=len(codepaths), tokens=tokens, matches=matches,
                                        meaning='Private proof stack not a code dependency of inspected packaged study sources. No native readiness implied.'),
              maintenance_surface=dict(commit=commit, tracked_review_asset_paths=len(names),
                                       native_preflight_unicode_entry_route_name_matches=len(selected),
                                       method='Git tree metadata and fixed lexical path predicates.',
                                       not_measured=['effort', 'wasted time', 'runtime cost', 'code quality', 'scientific independence']),
              bridge_draft_caveat='Latest observed V2 was being authored. Its observed pin and proposed status do not establish independent design-clear/implementation authority; recommendation does not depend on unfinished microdetails.',
              metadata_checker_note='First unretained metadata assembly used platform-default cp1252 read_text and raised UnicodeDecodeError before writing JSON. This named helper explicitly reads UTF-8. No subject, original target, native image or model was involved.',
              validation=dict(local_markdown_links=len(links), links=links, broken_links=broken,
                              citation_line_range_failures=citation_failures, current_doc_edits=0,
                              retained_scoped_statuses_not_promoted=True),
              activity=dict(subject_imports=0, subject_runs=0, native_dispatches=0, compiler_calls=0,
                            model_calls=0, tokenizer_calls=0, protected_outcome_or_gold_content_reads=0,
                            new_downloads=0, provider_spend_usd=0, current_doc_edits=0),
              qualification=dict(review_recommendation_only=True, new_execution_authorized=False,
                                 native25_complete=False, H5_complete=False, entire_project_complete=False))
output = BASE / (PREFIX + '.json')
with output.open('x', encoding='utf-8', newline='\n') as stream:
    json.dump(report, stream, indent=2)
    stream.write('\n')
print(json.dumps(dict(status=report['status'], report=pin(output), narrative=pin(MD),
                      input_pins=len(inputs), architectural_matches=matches, broken_links=broken,
                      citation_failures=citation_failures, maintenance_surface=report['maintenance_surface'])))
