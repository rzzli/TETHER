"""Optional explicit retrieval of the three fixed example originals only.

Network access requires --allow-network. Existing download workers, catalogs and
receipts are never edited. Archived receipt witnesses are copied unchanged; the
fresh retrieval has its own journal/report and does not backdate new collection.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
import urllib.request

from tether_engine.atomic import publish_bytes
from tether_engine.journal import RunJournal
from tether_engine.serde import ContractError, write_json
from tether_engine.stable_read import checked_path

MANIFEST_SHA='c2b58694416c3d355cff63d07ea30246051dd1948edffbae36f3304fe68cd0f4'
MAX_PAYLOAD_BYTES=16*1024*1024
PREFIX='https://ftp.ebi.ac.uk/pub/databases/opentargets/platform/25.09/'


def fetch_one(url, digest, size, deadline):
    if not isinstance(url,str) or not url.startswith(PREFIX) or type(size) is not int or not 0<size<=MAX_PAYLOAD_BYTES:
        raise ContractError('Unapproved example URL or size')
    if time.monotonic()>=deadline:
        raise TimeoutError('Example retrieval deadline')
    request=urllib.request.Request(url,headers={'User-Agent':'TETHER-pinned-example/1'})
    with urllib.request.urlopen(request,timeout=30) as response:
        if response.status!=200 or response.geturl()!=url:
            raise ContractError('Unexpected example response or redirect')
        chunks,used=[],0
        while True:
            if time.monotonic()>=deadline:
                raise TimeoutError('Example retrieval deadline')
            block=response.read(min(1024*1024,size-used+1))
            if not block:
                break
            used+=len(block)
            if used>size:
                raise ContractError('Example response exceeds pinned size')
            chunks.append(block)
    payload=b''.join(chunks)
    if len(payload)!=size or hashlib.sha256(payload).hexdigest()!=digest:
        raise ContractError('Example response differs from pinned bytes')
    return payload


def fetch(output, *, allow_network=False):
    if allow_network is not True:
        raise ContractError('Example network access requires explicit --allow-network')
    here=Path(__file__).parent
    raw=(here/'il6r_ot2509.json').read_bytes()
    if hashlib.sha256(raw).hexdigest()!=MANIFEST_SHA:
        raise ContractError('Example manifest hash differs')
    manifest=json.loads(raw)
    if len(manifest['sources'])!=3 or sum(s['bytes'] for s in manifest['sources'])>MAX_PAYLOAD_BYTES:
        raise ContractError('Example acquisition cap differs')
    # Validate all retained witnesses before issuing the first network request.
    witnesses={}
    for item in manifest['sources']:
        payload=(here/'receipts'/(item['receipt_sha256']+'.json')).read_bytes()
        if hashlib.sha256(payload).hexdigest()!=item['receipt_sha256']:
            raise ContractError('Archived receipt witness differs')
        witnesses[item['source_id']]=payload
    output=Path(output).absolute()
    checked_path(output.parent.parent,output.parent.name)
    if output.exists() or output.is_symlink():
        raise ContractError('Refusing to reuse an example download directory')
    journal=RunJournal(output,kind='build')
    started=time.monotonic()
    completed=[]
    try:
        for item in manifest['sources']:
            journal.append('download_attempt',url=item['source_url'],expected_sha256=item['sha256'],bytes=item['bytes'])
            payload=fetch_one(item['source_url'],item['sha256'],item['bytes'],started+300)
            for relative,value in ((item['relative_path'],payload),(item['receipt_path'],witnesses[item['source_id']])):
                destination=output/relative
                destination.parent.mkdir(parents=True,exist_ok=True)
                publish_bytes(destination,value)
            record=dict(source_id=item['source_id'],bytes=len(payload),sha256=item['sha256'],
                        retrieved_now_at_utc=datetime.now(timezone.utc).isoformat())
            completed.append(record)
            journal.append('download_completed',**record)
        report=dict(status='downloaded_exact_pinned_originals',files=completed,
            payload_bytes=sum(s['bytes'] for s in completed),elapsed_seconds=time.monotonic()-started,
            archived_receipts='Unchanged prior-acquisition witnesses; not receipts for the fresh downloads',
            publisher_authenticity='not_established',scientific_validation='not_established')
        journal.append('build_completed',**report)
        write_json(output/'download-report.json',report)
        return report
    except BaseException as error:
        journal.fail(error,'bounded_example_retrieval')
        raise
    finally:
        journal.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--allow-network',action='store_true')
    args=parser.parse_args()
    print(json.dumps(fetch(args.output,allow_network=args.allow_network),indent=2))
