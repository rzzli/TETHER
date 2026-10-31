"""Mechanical fresh-v3 map/result names only; no subject import or test."""
import hashlib
from pathlib import Path

H=Path(__file__).resolve().parent


def mapped(t):
    for a,b in [('role_ledger_codec_v2','role_ledger_codec_v3'),('role_owner_v2','role_owner_v3'),
                ('role_file_ports_v2','role_file_ports_v3'),('continue_role_verification_v2','continue_role_verification_v3')]:
        t=t.replace(a,b)
    return t


def main():
    raw=(H/'run_role_aware_independent_v5.py').read_bytes()
    assert hashlib.sha256(raw).hexdigest()=='ba767e126b1a07f215095f9c6e13d573b486b7df909537f4d85981df66b41d9a'
    t=mapped(raw.decode()).replace('-SOURCE-BINDING-v5.json','-SOURCE-BINDING-v6.json')
    t=t.replace("+'-PROOF-v5.json'","+'-PROOF-v6.json'").replace("+'-ATTEMPT-v5.json'","+'-ATTEMPT-v6.json'")
    t=t.replace('ROLE-AWARE-INDEPENDENT-UNBOUND-ERROR-v5.json','ROLE-AWARE-INDEPENDENT-UNBOUND-ERROR-v6.json')
    with (H/'run_role_aware_independent_v6.py').open('x',encoding='utf-8',newline='\n') as f:f.write(t)
    raw=(H/'run_role_aware_extensions_v2.py').read_bytes()
    assert hashlib.sha256(raw).hexdigest()=='5694ec9898c385c8ae825d2b88dcaea0b5e73684c9a9d6984d975aed68064aa8'
    t=mapped(raw.decode()).replace('ROLE-AWARE-EXTENSIONS-SOURCE-BINDING-v2.json','ROLE-AWARE-EXTENSIONS-SOURCE-BINDING-v3.json')
    t=t.replace("+'-PROOF-v2.json'","+'-PROOF-v3.json'").replace("+'-ATTEMPT-v2.json'","+'-ATTEMPT-v3.json'")
    t=t.replace('ROLE-AWARE-EXTENSIONS-UNBOUND-ERROR-v2.json','ROLE-AWARE-EXTENSIONS-UNBOUND-ERROR-v3.json')
    with (H/'run_role_aware_extensions_v3.py').open('x',encoding='utf-8',newline='\n') as f:f.write(t)
    print('Prepared mechanical all-v3 runner maps; no subject import/run')


if __name__=='__main__':main()
