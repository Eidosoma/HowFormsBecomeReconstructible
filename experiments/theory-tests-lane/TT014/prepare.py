"""Bind audited code and exposed qualification evidence; no new simulation."""
from pathlib import Path
import hashlib
import json
from datetime import datetime,timezone

HERE=Path(__file__).resolve().parent;LANE=HERE.parent
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def run():
    files={};bindings=[];reuse={}
    tt8=LANE/'TT008';tt13=LANE/'TT013'
    eight=read(tt8/'runs/prospective_v2/COMPLETE.json');eight_job=read(tt8/'jobs/prospective_v2/job.json')
    thirteen=read(tt13/'runs/audit_v1/COMPLETE.json');thirteen_job=read(tt13/'jobs/audit_v1/job.json')
    assert eight['audit_status']==thirteen['audit_status']=='PASS'
    assert read(tt13/'CLOSEOUT.json')['completion_sha256']==sha(tt13/'runs/audit_v1/COMPLETE.json')
    def copy(source,target,expected=None,use=None):
        digest=sha(source)
        if expected is not None:assert digest==expected,str(source)
        dest=HERE/target;dest.parent.mkdir(parents=True,exist_ok=True)
        with dest.open('xb') as f:f.write(source.read_bytes())
        assert sha(dest)==digest
        files[target]=digest;bindings.append(dict(original=str(source),local=target,sha256=digest))
        if use:reuse[target]=dict(source=str(source),source_sha256=digest,use=use)
    for name in ['native.py','optimizer.py','repair.py']:
        copy(tt13/'jobs/audit_v1/inputs/TT013'/name,name,thirteen_job['inputs_sha256'][name],'unchanged independent TT013 implementation')
    for name,target in [('native.py','lineage.py'),('auditor.py','lineage_audit.py')]:
        copy(tt8/'jobs/prospective_v2/inputs/TT008'/name,target,eight_job['inputs_sha256'][name],'unchanged code, renamed module')
    for name in ['source/spacing_dynamics.py','source/native/common.py','source/native/E015_functional_inheritance/model.py','source/native/E016_teaching_consistency/model.py']:
        copy(tt8/'jobs/prospective_v2/inputs/TT008'/name,name,eight_job['inputs_sha256'][name],'unchanged published production source')
    for name,target in [('reader.py','reader.py'),('audit_optimizer.py','optimizer_audit.py')]:
        rel='source/recipient/inputs/'+name
        copy(tt13/'jobs/audit_v1/inputs/TT013'/rel,target,thirteen_job['inputs_sha256'][rel],'unchanged production reader / independent Prim solver')
    for generation in [12,13,14]:
        rel=f'qualification_sources/spacing/boundary_034000_g{generation}.npz'
        copy(tt8/'jobs/prospective_v2/inputs/TT008'/rel,f'source/known/g{generation}.npz',eight_job['inputs_sha256'][rel])
    rel='known_qualification/teaching.npz'
    copy(tt8/'runs/prospective_v2'/rel,'source/known/teaching.npz',eight['outputs_sha256'][rel])
    for label,root,done in [('tt008',tt8,eight),('tt013',tt13,thirteen)]:
        mode='prospective_v2' if label=='tt008' else 'audit_v1'
        copy(root/f'runs/{mode}/COMPLETE.json',f'source/{label}/COMPLETE.json')
        copy(root/f'jobs/{mode}/job.json',f'source/{label}/job.json')
        copy(root/'CLOSEOUT.json',f'source/{label}/CLOSEOUT.json')
        for name in (['native_checks.json'] if label=='tt008' else ['TECHNICAL_CHECKS.json','PROVENANCE_AUDIT.json']):
            if name in done['outputs_sha256']:copy(root/f'runs/{mode}'/name,f'source/{label}/{name}',done['outputs_sha256'][name])
    # Freeze only the encountered design/exposure documents, not the fresh-cohort outcomes.
    source=LANE.parent/'theory-lane'
    for study in ['p05_fresh_lineages_v0_1','p05_serial_repair_v0_1']:
        for name in ['PROTOCOL.md','config.json']:
            copy(source/study/name,f'source/exposure/{study}/{name}')
    stamp=datetime.now(timezone.utc).isoformat()
    for name,value in [('SOURCE_RECEIPT.json',dict(recorded_utc=stamp,files_sha256=files,bindings=bindings,bytes=sum((HERE/x).stat().st_size for x in files),new_test_outcomes_generated=False)),
        ('IMPLEMENTATION_REUSE.json',dict(recorded_utc=stamp,reused=reuse,production_source_functions_execute=True,independent_full_replays=True,new_test_outcomes_generated=False))]:
        with (HERE/name).open('x') as f:json.dump(value,f,indent=2,sort_keys=True);f.write('\n')
    print(json.dumps(dict(files=len(files),bytes=sum((HERE/x).stat().st_size for x in files))))


if __name__=='__main__':run()
