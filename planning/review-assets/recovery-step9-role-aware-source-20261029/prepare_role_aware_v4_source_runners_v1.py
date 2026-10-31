"""Closed source4 map and test2 pin, no subject execution."""
import hashlib
from pathlib import Path

H=Path(__file__).resolve().parent


def map4(t):
    for a,b in [('role_ledger_codec_v3','role_ledger_codec_v4'),('role_owner_v3','role_owner_v4'),
                ('role_file_ports_v3','role_file_ports_v4'),('continue_role_verification_v3','continue_role_verification_v4')]:t=t.replace(a,b)
    return t


def main():
    raw=(H/'run_role_aware_independent_v7.py').read_bytes()
    assert hashlib.sha256(raw).hexdigest()=='6603401fa9d5083628261596d02d08b45985f90a931b4c5379e89adbfae1f760'
    text=map4(raw.decode()).replace('-SOURCE-BINDING-v7.json','-SOURCE-BINDING-v8.json')
    text=text.replace("+'-PROOF-v7.json'","+'-PROOF-v8.json'").replace("+'-ATTEMPT-v7.json'","+'-ATTEMPT-v8.json'").replace('ROLE-AWARE-INDEPENDENT-UNBOUND-ERROR-v7.json','ROLE-AWARE-INDEPENDENT-UNBOUND-ERROR-v8.json')
    with (H/'run_role_aware_independent_v8.py').open('x',encoding='utf-8',newline='\n') as f:f.write(text)
    raw=(H/'run_role_aware_extensions_v4.py').read_bytes()
    assert hashlib.sha256(raw).hexdigest()=='c02b07ed72b606c31c61c5f2acadf77b8945c248db3996aaeda50fe09759877d'
    text=map4(raw.decode()).replace('ROLE-AWARE-EXTENSIONS-SOURCE-BINDING-v4.json','ROLE-AWARE-EXTENSIONS-SOURCE-BINDING-v5.json')
    text=text.replace("+'-PROOF-v4.json'","+'-PROOF-v5.json'").replace("+'-ATTEMPT-v4.json'","+'-ATTEMPT-v5.json'").replace('ROLE-AWARE-EXTENSIONS-UNBOUND-ERROR-v4.json','ROLE-AWARE-EXTENSIONS-UNBOUND-ERROR-v5.json')
    text=text.replace('role_aware_actual_producer_extensions_v1','role_aware_actual_producer_extensions_v2')
    with (H/'run_role_aware_extensions_v5.py').open('x',encoding='utf-8',newline='\n') as f:f.write(text)
    print('Prepared closed source4 runner8/extensions5; no subject import/test')


if __name__=='__main__':main()
