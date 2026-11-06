#!/usr/bin/env python3
"""Verify/materialize v3.4 frozen small-file sources; never run simulations."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sha=lambda data:hashlib.sha256(data).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify-only',action='store_true')
    parser.add_argument('--intake')
    args=parser.parse_args()
    inventory=json.loads((ROOT/'paper/v3.4/source-inventory.json').read_text())
    if args.intake and args.intake not in {i['tag'] for i in inventory['intakes']}:
        parser.error('Unknown intake')
    count=split=0
    for page in inventory['shards']:
        raw=(ROOT/page['path']).read_bytes();assert sha(raw)==page['sha256'],page['path']
        for item in json.loads(raw):
            if args.intake and item['intake']!=args.intake:continue
            if item['encoding']=='identity':
                payload=(ROOT/item['public_path']).read_bytes()
                assert sha(payload)==item['sha256'],item['source_path']
                output=payload
            else:
                chunks=[]
                for part in item['parts']:
                    chunk=(ROOT/part['path']).read_bytes()
                    assert sha(chunk)==part['sha256'],part['path']
                    chunks.append(chunk)
                payload=b''.join(chunks)
                assert sha(payload)==item['payload_sha256'],item['source_path']
                assert len(payload)==item['payload_bytes']
                if item['encoding']=='text-parts':assert sha(payload)==item['sha256']
                output=gzip.compress(payload,mtime=0) if item['encoding']=='gzip-text-parts' else payload
                split+=1
            if not args.verify_only:
                destination=ROOT/'generated/v3.4/sources'/item['materialized_path']
                assert '..' not in Path(item['materialized_path']).parts
                destination.parent.mkdir(parents=True,exist_ok=True)
                destination.write_bytes(output)
            count+=1
    print(json.dumps({'status':'PASS','source_records':count,'split_records':split,
                      'verify_only':args.verify_only,'scientific_replay':False},indent=2))


if __name__=='__main__':main()
