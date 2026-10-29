"""Copy exact inherited physics, retained serial controls and one-episode prefixes."""
import hashlib
import json
from pathlib import Path
import shutil
from datetime import datetime,timezone

ROOT=Path(__file__).resolve().parent
LANE=ROOT.parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def write(p,v):
    with p.open('x') as stream:stream.write(json.dumps(v,sort_keys=True,indent=2,allow_nan=False)+'\n')
def copy(source,target,digest):
    assert sha(source)==digest,str(source)
    target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists():assert sha(target)==digest
    else:shutil.copyfile(source,target)
    assert sha(target)==digest

def main():
    assert not (ROOT/'SOURCE_MANIFEST.json').exists() and not (ROOT/'BASELINE_MANIFEST.json').exists()
    old=LANE/'TT023';previous=read(old/'SOURCE_MANIFEST.json');files=[]
    for row in previous['files']:
        source=old/row['snapshot'];copy(source,ROOT/row['snapshot'],row['sha256'])
        files.append(dict(snapshot=row['snapshot'],copied_from=str(source),sha256=row['sha256'],bytes=source.stat().st_size))
    inherited={}
    for source,name in ((old/'reference.py','reference.py'),(old/'tt019_reference.py','tt019_reference.py'),
                        (old/'kernel.py','inherited23_kernel.py'),(LANE/'TT022/audit.py','inherited22_audit.py')):
        digest=sha(source);copy(source,ROOT/name,digest);inherited[name]=digest
    write(ROOT/'SOURCE_MANIFEST.json',dict(study='TT024',recorded_utc=datetime.now(timezone.utc).isoformat(),
        copied_from_manifest=str(old/'SOURCE_MANIFEST.json'),copied_from_manifest_sha256=sha(old/'SOURCE_MANIFEST.json'),
        files=files,independent_reference={k:inherited[k] for k in ('reference.py','tt019_reference.py')},
        inherited_code=inherited))
    evidence={};rows={}
    for path in (LANE/'TT022/FREEZE.json',LANE/'TT022/CLOSEOUT.json',LANE/'TT022/checks/report_recovery_v1/COMPLETE.json',
        LANE/'TT022/checks/report_recovery_v1/ORIGINAL_FILES.json',old/'FREEZE.json',old/'CLOSEOUT.json',
        old/'NEXT_STEP.md',old/'INTERPRETATION.md',old/'SOURCE_MANIFEST.json'):
        evidence[str(path)]=sha(path)
    sources={
        'development':(LANE/'TT022/runs/serial_v1',old/'runs/counterfactual_v1',range(21000000,21000004),4),
        'benchmark':(LANE/'TT022/runs/benchmark_v1',old/'runs/benchmark_v1',(603210,603211),2),
        'qualification':(LANE/'TT022/checks/qualification_v1/serial',old/'checks/qualification_v1/serial',(603210,603211),1)}
    for role,(serial,prefix,blocks,futures) in sources.items():
        if role=='development':
            old_map=read(LANE/'TT022/checks/report_recovery_v1/ORIGINAL_FILES.json')
            new_receipt=prefix/'COMPLETE.json'
        else:
            old_receipt=serial/'COMPLETE.json' if role=='benchmark' else serial.parent/'COMPLETE.json'
            evidence[str(old_receipt)]=sha(old_receipt);old_map=read(old_receipt)['outputs']
            new_receipt=prefix/'COMPLETE.json' if role=='benchmark' else prefix.parent/'COMPLETE.json'
        evidence[str(new_receipt)]=sha(new_receipt);new_map=read(new_receipt)['outputs']
        for index in blocks:
            configs={};config_hashes={}
            for label,origin,mapping in (('serial',serial,old_map),('prefix',prefix,new_map)):
                source=origin/f'tissue_{index}/CONFIG.json'
                name=f'baseline/{role}/tissue_{index}/{label}_CONFIG.json'
                digest=mapping[str(source)];copy(source,ROOT/name,digest)
                configs[label]=name;config_hashes[name]=digest;evidence[str(source)]=digest
            for future in range(futures):
                for family in ('common','residual'):
                    entry=dict(configs=configs,arms={},hashes=dict(config_hashes),originals={})
                    for arm,origin,source_arm,mapping in (
                        ('full_on',serial,'capture',old_map),('zero_off',serial,'capture_once',old_map),
                        ('subtract_on',prefix,'subtract_on',new_map),('zero_on',prefix,'zero_on',new_map)):
                        source=origin/f'tissue_{index}/future_{future:02d}'/family/source_arm
                        destination=f'baseline/{role}/tissue_{index}/future_{future:02d}/{family}/{arm}'
                        entry['arms'][arm]=destination
                        for path in sorted(source.iterdir()):
                            assert path.is_file();digest=mapping[str(path)]
                            name=f'{destination}/{path.name}';copy(path,ROOT/name,digest)
                            entry['hashes'][name]=digest;entry['originals'][name]=str(path);evidence[str(path)]=digest
                    rows[f'{role}:{index}:{future}:{family}']=entry
    write(ROOT/'BASELINE_MANIFEST.json',dict(study='TT024',recorded_utc=datetime.now(timezone.utc).isoformat(),
        rows=rows,evidence=evidence,original_control_and_prefix_outcomes_exposed=True,
        selection='All four exposed blocks, both families, all positions and original futures; no outcome selection'))
    paths=set(name for row in rows.values() for name in row['hashes'])
    print(json.dumps(dict(native_source_files=len(files),baseline_batches=len(rows),baseline_files=len(paths),
        baseline_bytes=sum((ROOT/p).stat().st_size for p in paths),evidence_files=len(evidence)),sort_keys=True))

if __name__=='__main__':main()
