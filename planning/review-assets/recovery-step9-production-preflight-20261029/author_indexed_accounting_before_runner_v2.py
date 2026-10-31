"""New runner names/pins only; same accepted-V2 baseline replay logic."""
import ast
from pathlib import Path
HERE=Path(__file__).resolve().parent
raw=(HERE/'run_indexed_accounting_v2_before_v1.py').read_text(encoding='utf-8')
replacements={
 'INDEXED-ACCOUNTING-ACTUAL-V2-BEFORE-PROOF-v1.json':'INDEXED-ACCOUNTING-ACTUAL-V2-BEFORE-PROOF-v2.json',
 'INDEXED-ACCOUNTING-PRECODE-CONTROL-FREEZE-v1.json':'INDEXED-ACCOUNTING-PRECODE-CONTROL-FREEZE-v2.json',
 '888c7bec39a5b59861409c71bbd2cdfbb7b500a91755e82fc196fd886c478fed':'52da9451c215d50f4b3e559a47eb4c286dd7e33fc884b8bf67430d9e6ac9703d',
 'INDEXED-ACCOUNTING-PRECODE-TEST-CONTRACT-v1.json':'INDEXED-ACCOUNTING-PRECODE-TEST-CONTRACT-v2.json',
 'a693c8f1529732e40792a1aefb00f3dae2997eb0998663665db6a1b684680115':'cccf8a1f4f6219ff51ade0279e82f587cfbe76c969e1be69125c0cc72ff2a3bd',
 'independent_indexed_precode_controls_v1':'independent_indexed_precode_controls_v2',
 'indexed_accounting_controls_v1.py':'indexed_accounting_controls_v2.py',
 'before this first actual accepted-V2 replay':'before this first v2-control accepted-V2 replay (v1 first replay remains preserved)',
}
for old,new in replacements.items():
 assert old in raw,old
 raw=raw.replace(old,new)
ast.parse(raw)
with (HERE/'run_indexed_accounting_v2_before_v2.py').open('xb') as out:out.write(raw.encode('utf-8'))
