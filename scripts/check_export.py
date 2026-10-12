#!/usr/bin/env python3
"""Check the review export without running models or rewriting provenance."""
import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
LIMIT = 256 * 1024
EXCLUDED = {'.git', '.venv', 'build', '__pycache__', '.cache', '.pytest_cache', 'generated'}

def main():
    errors = []
    checked = 0
    for page in sorted((ROOT/'reproducibility/manifests').glob('files-*.json')):
        for row in json.loads(page.read_text()):
            p = ROOT/row['path']
            if not p.is_file():
                errors.append('Missing source: '+row['path'])
            elif hashlib.sha256(p.read_bytes()).hexdigest() != row['sha256']:
                errors.append('Changed source: '+row['path'])
            checked += 1
    generated = ROOT/'reproducibility/public-files.json'
    if generated.exists():
        for row in json.loads(generated.read_text()):
            p = ROOT/row['path']
            if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=row['sha256']:
                errors.append('Changed public packaging: '+row['path'])
    sizes = []
    sensitive = re.compile(rb'(?:-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----|gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|AKIA[0-9A-Z]{16})')
    for p in ROOT.rglob('*'):
        rel=p.relative_to(ROOT)
        if set(rel.parts)&EXCLUDED or not p.is_file():
            continue
        if p.is_symlink():
            errors.append('Symlink: '+str(rel))
            continue
        size=p.stat().st_size
        sizes.append(size)
        if size>LIMIT:
            errors.append('Over 256 KiB: '+str(rel))
        if sensitive.search(p.read_bytes()):
            errors.append('Credential-pattern match: '+str(rel))
    for name in ['README.md','MANUSCRIPT.md','EVIDENCE_LEDGER.md','METHODS_AND_PROVENANCE.md','SUPPLEMENTARY_EVIDENCE.md','experiments/README.md','reproducibility/README.md','reproducibility/AVAILABILITY.md']:
        p=ROOT/name
        for target in re.findall(r'\]\(([^\s)]+)\)',p.read_text()):
            if target.startswith(('http:', 'https:', 'mailto:', '#')):
                continue
            dest=target.split('#',1)[0]
            if dest and not (p.parent/dest).exists():
                errors.append('Broken navigation in '+name+': '+target)
    result=dict(status='PASS' if not errors else 'FAIL',source_files_checked=checked,
                public_files=len(sizes),total_bytes=sum(sizes),maximum_file_bytes=max(sizes),
                per_file_limit=LIMIT,errors=errors,scientific_replay=False)
    print(json.dumps(result,indent=2))
    return bool(errors)

if __name__=='__main__':
    raise SystemExit(main())
