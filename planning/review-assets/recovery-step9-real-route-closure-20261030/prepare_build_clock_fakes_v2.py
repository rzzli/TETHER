"""Extend the retained trusted-helper fakes with one slow-spawn regression."""
from pathlib import Path
import hashlib

base=Path(__file__).resolve().parent
prior=base/"check_build_cleanup_with_fakes_v1.py"
text=prior.read_text(encoding="utf-8")
text=text.replace('build_native_carrier_component_v2.py','build_native_carrier_component_v3.py')
text=text.replace('6f83b18c02a058074bb5b571edf63b7d3bd79f1cbd894d6a2d4371e6d7e1f848','2d0b0ad29ab13ea9a82b01d28238a87c3e4c4eefbacf1a1eff5f0916cb92d3db')
text=text.replace('r09-native-carrier-driver-cleanup-fakes-v1','r09-native-carrier-driver-cleanup-fakes-v2')
text=text.replace('"ordinary_success",FakeProcess([(b"ok",b"")]),None),','"ordinary_success",FakeProcess([(b"ok",b"")]),None),\n    ("slow_spawn_preserves_original_deadline",FakeProcess([(b"late",b"")]),"DEADLINE_AFTER_SPAWN"),')
text=text.replace('    def spawn(*args,**kwargs):spawns.append((args,kwargs));return process\n',
'''    clock=[0.0]
    def spawn(*args,**kwargs):
        spawns.append((args,kwargs))
        if name=="slow_spawn_preserves_original_deadline":clock[0]=58.5
        return process
''')
text=text.replace('monotonic=lambda:0)','monotonic=lambda:clock[0])')
text=text.replace('        require(caught is expected_error,"Exact original error identity")',
'''        if expected_error=="DEADLINE_AFTER_SPAWN":
            require(isinstance(caught,TimeoutError),"Same-clock timeout after slow spawn")
        else:
            require(caught is expected_error,"Exact original error identity")''')
text=text.replace('        else:\n            require(process.timeouts==[58,2.0]',
'''        elif expected_error=="DEADLINE_AFTER_SPAWN":
            require(process.timeouts==[1.5] and process.kill_calls==1,"Only remaining1.5 cleanup seconds, no new58-second work wait")
            require(primary()["type"]=="TimeoutError"and row["returncode"]==0,"Cleanup exit0 cannot heal original work deadline")
        else:
            require(process.timeouts==[58,2.0]''',1)
text=text.replace('NATIVE-CARRIER-BUILD-DRIVER-FAKE-REGRESSIONS-v1.json','NATIVE-CARRIER-BUILD-DRIVER-FAKE-REGRESSIONS-v2.json')
text=text.replace('Three fixed fake process controls','Four fixed fake process controls')
output=base/"check_build_cleanup_with_fakes_v2.py"
with output.open("x",encoding="utf-8",newline="\n")as stream:stream.write(text)
print(hashlib.sha256(output.read_bytes()).hexdigest())
