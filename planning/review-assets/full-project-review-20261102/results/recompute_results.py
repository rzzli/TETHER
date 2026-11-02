"""Read-only arithmetic/byte check; no producer/scorer imports or scientific oracle."""
import csv
from collections import Counter
from fractions import Fraction
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent


def main():
    checks = []
    def check(label, value):
        checks.append({'label': label, 'passed': bool(value)})
        if not value:
            raise AssertionError(label)
    manifest = json.loads((ROOT/'paper/results/ARTIFACTS.json').read_bytes())
    for label, descriptor in {**manifest['inputs'], **manifest['tables_and_outputs']}.items():
        raw = (ROOT/descriptor['path']).read_bytes()
        check('byte binding: '+label, hashlib.sha256(raw).hexdigest()==descriptor['sha256'] and len(raw)==descriptor['bytes'])
    tables = {}
    for path in sorted((ROOT/'paper/results/tables').glob('*.csv')):
        with path.open(newline='', encoding='utf-8') as stream:
            tables[path.stem]=list(csv.DictReader(stream))
    check('eleven tables / 392 rows',len(tables)==11 and sum(map(len,tables.values()))==392)
    ledger=json.loads((ROOT/manifest['inputs']['ledger']['path']).read_bytes())
    check('38 outputs / 90 decisions',len(ledger['output_cells'])==38 and len(ledger['decision_cells'])==90)
    native=[]
    root=(ROOT/manifest['inputs']['ledger']['path']).parent
    for row in ledger['output_cells']:
        raw=(root/row['raw_path']).read_bytes()
        check('retained raw: '+row['cell_id'],hashlib.sha256(raw).hexdigest()==row['raw_sha256'] and len(raw)==row['raw_bytes'])
        if row['stratum']=='native' and row['arm']=='L':
            doc=json.loads(raw)
            facts=doc['facts']
            measured=[f for f in facts if f['source']['field'] in ('beta','standardError','pValueMantissa','pValueExponent')]
            known=sum(f['value'] is not None for f in measured)
            identity=[f for f in facts if f not in measured]
            native.append({'case_id':row['case_id'],'measurement_known':known,'measurement_null':4-known,'identity_known':sum(f['value'] is not None for f in identity),'identity_null':sum(f['value'] is None for f in identity),'minimum_matches_60':next(n for n in range(known+1) if Fraction(n,known)>=Fraction(3,5)),'minimum_matches_80':next(n for n in range(known+1) if Fraction(n,known)>=Fraction(4,5)),'minimum_matches_100':known})
            check('15 slots/4 measurements/11 identities: '+row['case_id'],len(facts)==15 and len(measured)==4 and len(identity)==11)
    check('native availability',len(native)==12 and sum(r['measurement_known'] for r in native)==40 and sum(r['identity_known'] for r in native)==108)
    check('80 and 100 mathematically identical in every native unit',all(r['minimum_matches_80']==r['minimum_matches_100'] for r in native))
    terminals=dict(Counter(r['terminal'] for r in ledger['output_cells']))
    verdicts=dict(Counter(r['verdict'] for r in ledger['decision_cells']))
    check('terminal totals',terminals=={'returned':36,'malformed':2})
    check('decision totals',verdicts=={'admitted':57,'rejected':33})
    native_table=tables['native_case_results']
    for arm,want in [('L',12),('A',0)]:
        check('native completion '+arm,sum(r['completion_80']=='true' for r in native_table if r['arm']==arm)==want)
    constructed={}
    for policy,want in [('FULL',0),('WITHOUT_WRAPPER',2),('WIRE_ONLY',7)]:
        rows=[r for r in ledger['decision_cells'] if r['policy']==policy and r['output_cell_id'].startswith('S-')]
        invalid=[r for r in rows if r['output_cell_id'].startswith('S-F')]
        valid=[r for r in rows if r['output_cell_id'].startswith('S-C')]
        bad=sum(r['verdict']=='admitted' for r in invalid)
        rejection=sum(r['verdict']=='rejected' for r in valid)
        check('constructed '+policy,len(invalid)==10 and len(valid)==4 and bad==want and rejection==0)
        constructed[policy]={'invalid_admitted':bad,'invalid_count':10,'valid_rejected':rejection,'valid_count':4}
    phases={r['phase']:r for r in tables['resource_phases']}
    total=float(phases['producer_total']['wall_seconds'])
    wrapper=float(phases['amortized_source_verification']['wall_seconds'])
    logical=int(phases['producer_total']['logical_completed_hash_bytes'])
    result={'schema_version':1,'method':'independent_retained_result_arithmetic_review_v1','status':'PASS_RETAINED_RESULT_ARITHMETIC_WITH_DESIGN_LIMITATIONS','role':'evaluation_only','agent_visible':False,'checks':checks,'check_count':len(checks),'source_originals_reread':False,'scientific_validation':'not_established','tables':{k:len(v) for k,v in tables.items()},'native':native,'outputs':terminals,'decisions':verdicts,'constructed':constructed,'new_design_observations':{'native_80_and_100_identical_for_every_possible_match_count':True,'source_wrapper_fraction_of_production_wall':wrapper/total,'logical_hash_bytes_per_selected_frame_byte':logical/2866248239},'limitations':['Arithmetic and current retained-byte checks, not a new source-inclusive scientific audit.','No producer/scorer imports or execution; no source/response/protected outcome read; no model/network calls.']}
    (HERE/'RECOMPUTED-RESULTS.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':result['status'],'checks':len(checks),'design':result['new_design_observations']}))


if __name__=='__main__':
    main()
