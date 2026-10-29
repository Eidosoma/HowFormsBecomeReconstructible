"""Archive the completed predecessor and copy audited code without production data."""
from pathlib import Path
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parent
LANE=ROOT.parent
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):
    with p.open('x') as f:json.dump(v,f,sort_keys=True,indent=2);f.write('\n')
def main():
    prior=LANE/'TT035';h=read(prior/'COMPLETION_HANDOFF.json');archive=ROOT/'intake_inputs';archive.mkdir(exist_ok=True)
    paths=set(map(Path,h['files']))|{prior/n for n in ('COMPLETION_HANDOFF.json','PROTOCOL.md','FREEZE.json','runs/stopped_v1/COMPLETE.json','runs/stopped_v1/REPORT.md')}
    snapshot={}
    for p in sorted(paths):
        if str(p) in h['files']:assert sha(p)==h['files'][str(p)],p
        dest=archive/p.relative_to(LANE);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
        snapshot[str(p)]=dict(snapshot=str(dest),sha256=sha(p));assert sha(dest)==sha(p)
    
    if (archive/'MANIFEST.json').exists():assert read(archive/'MANIFEST.json')==dict(files=snapshot)
    else:write(archive/'MANIFEST.json',dict(files=snapshot))
    copied={}
    for study,names in (('TT035',('kernel.py','inherited_repair.py','physical_reference.py','repair_audit.py')),
                        ('TT034',('receiving.py',)),('TT028',('capture_reference.py',))):
        frozen=read(LANE/study/'FREEZE.json')
        for name in names:
            p=LANE/study/name;assert sha(p)==frozen['inputs'][str(p)]
            target=ROOT/name
            if target.exists():assert sha(target)==sha(p)
            else:shutil.copyfile(p,target)
            copied[str(target)]=dict(source=str(p),sha256=sha(p))
    native=read(prior/'SOURCE_MANIFEST.json')['native_code']
    for p,v in native.items():assert sha(Path(p))==v
    bridge=LANE/'TT028/runs/confirmation_v1/tissue_28000000/baseline'
    close=read(LANE/'TT028/CLOSEOUT.json')
    mp=LANE/'TT028/checks/closeout_v1/ORIGINAL_FILES.json'
    assert sha(mp)==close['outputs'][str(mp)]
    complete=read(mp)
    bridge_files={str(p):sha(p) for p in bridge.rglob('*') if p.is_file()}
    assert bridge_files
    for p,v in bridge_files.items():assert complete[p]==v
    evidence={str(p):sha(p) for p in (prior/'CLOSEOUT.json',prior/'FINDINGS.json',prior/'runs/stopped_v1/COMPLETE.json',LANE/'TT028/FREEZE.json',LANE/'TT028/CLOSEOUT.json',mp)}
    write(ROOT/'SOURCE_MANIFEST.json',dict(native_code=native,copied_audited_code=copied,evidence=evidence,exposed_bridge=bridge_files,production_population_reused=False))
    print(dict(status='BOUND',native_files=len(native),archived_files=len(snapshot),bridge_files=len(bridge_files)))
if __name__=='__main__':main()
