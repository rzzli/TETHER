"""Create explicit current helpers from reviewed predecessors without editing them."""
from pathlib import Path

HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'recovery-step9-retrieval-20261026'


def replace_once(text,old,new):
    assert text.count(old)==1,old
    return text.replace(old,new)


text=(OLD/'verify_installed.py').read_text(encoding='utf-8')
text=replace_once(text,"environment = Path(sys.prefix).resolve()", "environment = Path(sys.prefix).resolve()\nqualification=json.loads((Path(__file__).parent/'QUALIFICATION.json').read_bytes())\ncurrent_bundle=Path(qualification['output']).resolve()\nassert qualification['status']=='passed'")
text=replace_once(text,"approved = [normalized(BASE)","approved = [normalized(current_bundle), normalized(BASE)")
text=replace_once(text,"        path = normalized(os.fsdecode(args[0]))", "        path = normalized(os.fsdecode(args[0]))\n        if path.startswith('e:') or '\\\\data\\\\benchmark\\\\' in path:\n            forbidden_reads.append(dict(event=event,path=path))\n            raise PermissionError('Original assets and benchmark payloads unavailable')")
text=replace_once(text,"assert study_result['status'] == 'recorded_smoke_passed'", "assert study_result['status'] == 'recorded_smoke_passed'\nfrom asof.study.authority_four_arm import verify as four_arm_verify\nfour_arm_result=encode(four_arm_verify(current_bundle,qualification['result']['receipt_sha256']))\nassert four_arm_result == qualification['result']")
text=replace_once(text,"result = dict(installed_retrieval_smoke=", "result = dict(installed_authority_four_arm=four_arm_result, installed_retrieval_smoke=")
with (HERE/'verify_installed.py').open('x',encoding='utf-8') as stream:
    stream.write(text)

text=(OLD/'verify_relocation.py').read_text(encoding='utf-8')
text=replace_once(text,'from asof.study.retrieval_smoke import verify','from asof.study.authority_four_arm import verify')
text=replace_once(text,'        path = normalized(args[0])', '        path = normalized(args[0])\n        if path.startswith("e:") or "\\\\data\\\\benchmark\\\\" in path:\n            attempts["forbidden_reads"].append(path)\n            raise PermissionError("Original tokenizer assets and benchmark payloads unavailable")')
text=replace_once(text,'    if event in ("socket.connect", "subprocess.Popen"):', '    if event == "exec" and args and not args[0].co_filename.startswith("<") and under(normalized(args[0].co_filename), normalized(RESTORED)):\n        attempts["imports"].append(args[0].co_filename)\n        raise PermissionError("Archived execution denied")\n    if event in ("socket.connect", "socket.getaddrinfo", "subprocess.Popen", "os.system"):')
text=text.replace('passed_recorded_retrieval_relocation','passed_authority_four_arm_relocation')
with (HERE/'verify_relocation.py').open('x',encoding='utf-8') as stream:
    stream.write(text)
print('Created two explicit verifier helpers; old files unchanged')
