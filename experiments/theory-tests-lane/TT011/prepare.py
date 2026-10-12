"""Freeze P05 evidence and bind its P04 antecedents to the completed TT010 audit."""
from pathlib import Path
import json
import shutil
import support as s


def run():
    fleet=s.HERE.parent.parent; destination=s.HERE/'source';destination.mkdir(exist_ok=False)
    files={};origins={};links=[]
    def bind(path,digest=None,rel=None):
        path=Path(path).resolve();s.require(path.is_relative_to(fleet),'Local experiment source')
        actual=s.sha(path);s.require(digest is None or actual==digest,'Source identity '+str(path))
        if str(path) not in origins:
            target=destination/(rel or 'upstream/'+str(path.relative_to(fleet)))
            target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target)
            s.require(s.sha(target)==actual,'Snapshot identity')
            origins[str(path)]=str(target.relative_to(s.HERE));files[origins[str(path)]]=actual
        links.append(dict(original=str(path),local=origins[str(path)],sha256=actual))
    planning=s.read(s.HERE/'PLANNING_CONTEXT.json')
    for path,row in planning['sources_read'].items():
        s.require(s.sha(s.HERE.parent/path)==row['sha256'],'Unchanged planning evidence')
    base=fleet/'theory-lane/p05_backup_task_swap_v0_1/runs/pilot_v1'
    bind(base/'COMPLETE.json',rel='p05/run/COMPLETE.json')
    done=s.read(base/'COMPLETE.json');s.require(done['status']=='COMPLETE','P05 completion')
    for rel,digest in done['outputs_sha256'].items():bind(base/rel,digest,'p05/run/'+rel)
    manifest=s.read(base/'manifest.json')
    for rel,digest in manifest['files_sha256'].items():bind(base/'inputs'/rel,digest,'p05/inputs/'+rel)
    prep=s.read(base/'inputs/prepared/COMPLETE.json')
    s.require(s.sha(base/'inputs/prepared/COMPLETE.json')==manifest['prepared_complete_sha256'],'Prepared manifest binding')
    for rel,digest in prep['outputs_sha256'].items():bind(base/'inputs/prepared'/rel,digest)
    for path,digest in prep['sources_sha256'].items():bind(path,digest)
    for label,source in prep['donor_source_runs'].items():
        source=Path(source);completion=s.read(source/'COMPLETE.json')
        for block in manifest['config']['blocks']:
            name=f'boundary_{block:06d}_g13.npz'
            s.require(prep['sources_sha256'][str(source/name)]==completion['outputs_sha256'][name],'Donor completion binding')
    prior=s.HERE.parent/'TT010';closeout=s.read(prior/'CLOSEOUT.json')
    s.require(s.sha(prior/'CLOSEOUT.json')==planning['prior_TT010_closeout_sha256'] and closeout['status']=='PASS','TT010 closeout')
    s.require(s.sha(prior/'runs/audit_v1/COMPLETE.json')==closeout['completion_sha256'],'TT010 completion')
    job=s.read(prior/'jobs/audit_v1/job.json');complete=s.read(prior/'runs/audit_v1/COMPLETE.json')
    s.require(s.sha(prior/'jobs/audit_v1/job.json')==closeout['job_sha256'],'TT010 job identity')
    for rel,digest in job['inputs_sha256'].items():s.require(s.sha(prior/'jobs/audit_v1/inputs/TT010'/rel)==digest,'Prior audited input')
    for rel,digest in complete['outputs_sha256'].items():s.require(s.sha(prior/'runs/audit_v1'/rel)==digest,'Prior audited output')
    old=s.read(prior/'SOURCE_RECEIPT.json');antecedents=0
    for path,digest in prep['sources_sha256'].items():
        if '/p04_hybrid_composition_' in path:
            s.require(job['inputs_sha256'][old['origins'][path]]==digest,'P04 antecedent audited by TT010');antecedents+=1
    for rel in ['CLOSEOUT.json','runs/audit_v1/COMPLETE.json','jobs/audit_v1/job.json','SOURCE_RECEIPT.json']:
        bind(prior/rel,rel='tt010/'+rel)
    alignment=fleet/'theory-lane/p05_sign_alignment_audit_v0_1'
    verification=s.read(alignment/'results_v1/VERIFICATION.json')
    bind(alignment/'results_v1/VERIFICATION.json',rel='alignment/results/VERIFICATION.json')
    for rel,digest in verification['files_sha256'].items():bind(alignment/'results_v1'/rel,digest,'alignment/results/'+rel)
    start=s.read(alignment/'results_v1/START.json')
    for rel,digest in start['files_sha256'].items():bind(alignment/rel,digest,'alignment/code/'+rel)
    for record in [verification,s.read(alignment/'results_v1/SYMMETRY.json')]:
        for rel,digest in record['code_sha256'].items():bind(alignment/rel,digest,'alignment/code/'+rel)
    for row in s.read(alignment/'SOURCE_BINDINGS.json')['bindings'].values():bind(row['source'],row['sha256'])
    receipt=dict(status='PASS',recorded_utc=s.utc(),files_sha256=files,origins=origins,bindings=links,
                 source_code_executed=False,prior_TT010_inputs_verified=len(job['inputs_sha256']),
                 prior_TT010_outputs_verified=len(complete['outputs_sha256']),P04_antecedents_bound=antecedents,
                 new_scientific_outcomes=False)
    s.dump(s.HERE/'SOURCE_RECEIPT.json',receipt)
    with (s.HERE.parent/'exposure_register.jsonl').open('a') as f:
        f.write(json.dumps(dict(event='TT011_P05_SOURCE_FREEZE',recorded_utc=s.utc(),source_receipt_sha256=s.sha(s.HERE/'SOURCE_RECEIPT.json'),
                                source_files=len(files),new_scientific_outcomes=False))+'\n')
    return dict(files=len(files),bindings=len(links),bytes=sum((s.HERE/name).stat().st_size for name in files))


if __name__=='__main__':print(json.dumps(run(),indent=2))
