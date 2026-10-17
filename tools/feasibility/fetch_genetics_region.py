"""Bounded regional retrieval with pysam; run in the isolated Linux tool environment.

Stores every indexed row in the specified region, not only significant hits.
Regional hashes identify retrieved subsets, not the complete remote source files.
"""
import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import time
import urllib.request

import pysam


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    args = parser.parse_args()
    root = args.root
    protocol = json.loads((root/'protocol.json').read_text())
    out = root/'regional_originals'
    out.mkdir(exist_ok=False)
    receipts = []
    for name, url in protocol['sources'].items():
        record = {'source':name, 'url':url, 'region':protocol['region'],
                  'started_at_utc':datetime.now(timezone.utc).isoformat(),
                  'status':'started','pysam_version':pysam.__version__}
        receipts.append(record)
        def save():
            (root/'regional-receipts.json').write_text(json.dumps(receipts,indent=2))
        save()
        started = time.monotonic()
        try:
            with urllib.request.urlopen(urllib.request.Request(url,method='HEAD'),timeout=45) as response:
                record['remote_headers'] = {k:response.headers.get(k) for k in
                    ['Content-Length','Last-Modified','ETag','Accept-Ranges']}
            index = out/(name+'.tbi')
            with urllib.request.urlopen(url+'.tbi',timeout=60) as response:
                data = response.read(32*1024*1024+1)
                if len(data)>32*1024*1024:
                    raise ValueError('Index exceeds 32 MiB bound')
            index.write_bytes(data)
            record['index_sha256']=hashlib.sha256(data).hexdigest()
            record['index_bytes']=len(data)
            save()
            time.sleep(3)
            tabix = pysam.TabixFile(url,index=str(index))
            region = protocol['region']
            if region.split(':')[0] not in tabix.contigs and 'chr'+region.split(':')[0] in tabix.contigs:
                region = 'chr'+region
            path=out/(name+'.region.tsv.gz')
            count=0
            raw_bytes=0
            with gzip.open(path,'wt',encoding='utf-8',newline='\n') as stream:
                for header in tabix.header:
                    stream.write(header+'\n')
                for line in tabix.fetch(region=region):
                    raw_bytes+=len(line.encode())+1
                    if raw_bytes>protocol['max_output_bytes_per_source']:
                        raise ValueError('Regional output exceeds explicit byte bound')
                    stream.write(line+'\n')
                    count+=1
            tabix.close()
            record.update(status='retrieved',rows=count,uncompressed_row_bytes=raw_bytes,
                bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                output=path.name,elapsed_seconds=time.monotonic()-started,
                coverage='All indexed records returned for the requested interval; source-wide hash not verified')
        except Exception as error:
            record.update(status='failed',error=repr(error),elapsed_seconds=time.monotonic()-started)
        save()
        print(json.dumps(record),flush=True)
        time.sleep(3)


if __name__=='__main__':
    main()
