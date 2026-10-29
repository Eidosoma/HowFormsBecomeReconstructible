"""Bind the completed predecessor, audited code and excluded bridge evidence."""
from pathlib import Path
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parent
LANE=ROOT.parent
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,value):
    with p.open('x') as f:json.dump(value,f,sort_keys=True,indent=2);f.write('\n')
def main():
    prior=LANE/'TT038';handoff=read(prior/'COMPLETION_HANDOFF.json')
    archive=ROOT/'intake_inputs';archive.mkdir();saved={}
    paths=set(map(Path,handoff['files']))|{prior/n for n in ('COMPLETION_HANDOFF.json','PROTOCOL.md','FREEZE.json','runs/followup_v1/COMPLETE.json','runs/followup_v1/REPORT.md')}
    for p in sorted(paths):
        if str(p) in handoff['files']:assert sha(p)==handoff['files'][str(p)]
        dest=archive/p.relative_to(LANE);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
        saved[str(p)]=dict(snapshot=str(dest),sha256=sha(p));assert sha(dest)==sha(p)
    write(archive/'MANIFEST.json',dict(files=saved))
    copied={}
    sources=[('TT036',name,name) for name in ('baseline.py','design.py','intervention.py','inherited_repair.py','physical_reference.py','receiving.py','capture_reference.py')]
    sources += [('TT037','kernel.py','kernel.py'),('TT037','repair_audit.py','repair_audit.py'),
        ('TT038','analysis_core.py','analysis_core.py'),('TT038','analysis.py','trajectory_analysis.py')]
    for study,name,target in sources:
        p=LANE/study/name;frozen=read(LANE/study/'FREEZE.json');assert sha(p)==frozen['inputs'][str(p)]
        q=ROOT/target;assert not q.exists();shutil.copyfile(p,q)
        copied[str(q)]=dict(source=str(p),sha256=sha(q))
    old=read(LANE/'TT036/SOURCE_MANIFEST.json');native=old['native_code'];source_bridge=old['exposed_bridge']
    for p,h in native.items():assert sha(Path(p))==h
    for p,h in source_bridge.items():assert sha(Path(p))==h
    evidence={str(p):sha(p) for p in (prior/'FREEZE.json',prior/'CLOSEOUT.json',prior/'FINDINGS.json',
        prior/'runs/followup_v1/COMPLETE.json',prior/'runs/benchmark_v1/COMPLETE.json',
        LANE/'TT036/FREEZE.json',LANE/'TT036/SOURCE_MANIFEST.json',LANE/'TT028/FREEZE.json',
        LANE/'TT028/CLOSEOUT.json',LANE/'TT028/checks/closeout_v1/ORIGINAL_FILES.json')}
    for p,h in old['evidence'].items():assert sha(Path(p))==h
    original=read(LANE/'TT028/checks/closeout_v1/ORIGINAL_FILES.json')
    for p,h in source_bridge.items():assert original[p]==h
    closeout=read(prior/'CLOSEOUT.json');assert sha(prior/'runs/followup_v1/COMPLETE.json')==closeout['completion_sha256']
    benchpath=prior/'runs/benchmark_v1/COMPLETE.json'
    assert sha(benchpath)==read(prior/'FREEZE.json')['evidence'][str(benchpath)]
    bench=read(benchpath);inherited=read(prior/'SOURCE_MANIFEST.json')['benchmark'];bridges={};bridge_hashes={}
    for i in (608280,608281):
        d=prior/'runs/benchmark_v1'/f'tissue_{i}';ap=d/'ALIASES.json'
        assert sha(ap)==bench['outputs'][str(ap)];bridge_hashes[str(ap)]=sha(ap)
        alias=next(a for a in read(ap) if a['family']=='residual' and a['body_source']=='own' and a['mask']=='axis0_side0')
        entries=[]
        for source,target in zip(alias['source_repairs'],alias['continuations']):
            study,name=source.split(':');prefix=LANE/study/'runs/benchmark_v1'/f'tissue_{i}'/(name+'.npz')
            continuation=d/(target+'.npz')
            assert sha(prefix)==inherited[str(prefix)] and sha(continuation)==bench['outputs'][str(continuation)]
            for p in (prefix,continuation):bridge_hashes[str(p)]=sha(p)
            entries.append(dict(prefix=str(prefix),continuation=str(continuation)))
        bridges[str(i)]=entries
    write(ROOT/'SOURCE_MANIFEST.json',dict(native_code=native,copied_audited_code=copied,evidence=evidence,
        exposed_bridge=source_bridge,excluded_window_bridges=bridges,excluded_window_bridge_hashes=bridge_hashes,
        production_population_reused=False,production_recipient_outcomes_reused=False))
    print(dict(status='BOUND',native_files=len(native),copied_files=len(copied),archived_files=len(saved),
        source_bridge_files=len(source_bridge),window_bridge_files=len(bridge_hashes)))
if __name__=='__main__':main()
