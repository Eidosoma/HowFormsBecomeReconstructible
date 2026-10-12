"""Immutable recipient-completion source snapshot, tied to completed TT012."""
from pathlib import Path
import json
import support as s


def run():
    fleet=s.HERE.parent.parent;destination=s.HERE/'source';destination.mkdir(exist_ok=False)
    files={};origins={};bindings=[];planning=s.read(s.HERE/'PLANNING_CONTEXT.json')
    def bind(path,digest=None,rel=None):
        path=Path(path).resolve();s.require(path.is_relative_to(fleet),'Experiment-local source')
        actual=s.sha(path);s.require(digest is None or actual==digest,'Source commitment '+str(path))
        if str(path) not in origins:
            target=destination/(rel or 'upstream/'+str(path.relative_to(fleet)))
            target.parent.mkdir(parents=True,exist_ok=True)
            with target.open('xb') as f:f.write(path.read_bytes())
            s.require(s.sha(target)==actual,'Snapshot bytes')
            origins[str(path)]=str(target.relative_to(s.HERE));files[origins[str(path)]]=actual
        bindings.append(dict(original=str(path),local=origins[str(path)],sha256=actual))
    for row in planning['sources'].values():
        s.require(s.sha(row['original'])==s.sha(s.HERE.parent/row['snapshot'])==row['sha256'],'Unchanged planning evidence')
    prior=s.HERE.parent/'TT012';close=s.read(prior/'CLOSEOUT.json')
    s.require(s.sha(prior/'CLOSEOUT.json')==planning['prior_TT012_closeout_sha256'] and close['status']=='PASS','TT012 closeout')
    bind(prior/'CLOSEOUT.json',rel='tt012/CLOSEOUT.json')
    bind(prior/'runs/audit_v1/COMPLETE.json',close['completion_sha256'],'tt012/COMPLETE.json')
    bind(prior/'jobs/audit_v1/job.json',close['job_sha256'],'tt012/job.json')
    job=s.read(prior/'jobs/audit_v1/job.json');done=s.read(prior/'runs/audit_v1/COMPLETE.json')
    for rel,digest in job['inputs_sha256'].items():s.require(s.sha(prior/'jobs/audit_v1/inputs/TT012'/rel)==digest,'Previously audited input')
    for rel,digest in done['outputs_sha256'].items():s.require(s.sha(prior/'runs/audit_v1'/rel)==digest,'Previously audited output')
    bind(prior/'jobs/audit_v1/inputs/TT012/SOURCE_RECEIPT.json',job['inputs_sha256']['SOURCE_RECEIPT.json'],'tt012/SOURCE_RECEIPT.json')
    for rel in ['TECHNICAL_CHECKS.json','INTAKE_AUDIT.json','NATIVE_AUDIT.json']:
        bind(prior/'runs/audit_v1'/rel,done['outputs_sha256'][rel],'tt012/'+rel)
    antecedents=s.read(prior/'jobs/audit_v1/inputs/TT012/SOURCE_RECEIPT.json')
    base=Path(planning['source']);bind(base/'COMPLETE.json',planning['source_complete_sha256'],'recipient/run/COMPLETE.json')
    complete=s.read(base/'COMPLETE.json');s.require(complete['status']=='COMPLETE' and complete['trajectories']==9792,'Complete source scope')
    for rel,digest in complete['outputs_sha256'].items():bind(base/rel,digest,'recipient/run/'+rel)
    manifest=s.read(base/'manifest.json')
    for rel,digest in manifest['files_sha256'].items():bind(base/'inputs'/rel,digest,'recipient/inputs/'+rel)
    prep=s.read(base/'inputs/prepared/COMPLETE.json')
    s.require(s.sha(base/'inputs/prepared/COMPLETE.json')==manifest['prepared_complete_sha256'],'Prepared commitment')
    for rel,digest in prep['outputs_sha256'].items():bind(base/'inputs/prepared'/rel,digest)
    inherited=0
    for path,digest in prep['sources_sha256'].items():
        s.require(path in antecedents['origins'] and job['inputs_sha256'][antecedents['origins'][path]]==digest,'Antecedent independently audited by TT012')
        bind(path,digest);inherited+=1
    reuse=s.read(base/'inputs/SOURCE_REUSE.json');reused=0
    for name,row in reuse.items():
        if 'source' not in row:continue
        source=row['source'];digest=row['source_sha256']
        s.require(source in antecedents['origins'] and job['inputs_sha256'][antecedents['origins'][source]]==digest,'Source code reuse commitment')
        bind(source,digest,'antecedent_code/'+name);reused+=1
    record=dict(status='PASS',recorded_utc=s.utc(),files_sha256=files,origins=origins,bindings=bindings,
        prior_inputs_verified=len(job['inputs_sha256']),prior_outputs_verified=len(done['outputs_sha256']),
        antecedents_bound_to_TT012=inherited,source_reuse_bindings=reused,source_code_executed=False,
        performance_report_inspected=True,source_completion_sha256=s.sha(base/'COMPLETE.json'),new_scientific_outcomes=False)
    s.dump(s.HERE/'SOURCE_RECEIPT.json',record)
    with (s.HERE.parent/'exposure_register.jsonl').open('a') as f:f.write(json.dumps(dict(event='TT013_SOURCE_FREEZE',recorded_utc=s.utc(),source_receipt_sha256=s.sha(s.HERE/'SOURCE_RECEIPT.json'),source_files=len(files),new_scientific_outcomes=False))+'\n')
    return dict(files=len(files),bindings=len(bindings),bytes=sum((s.HERE/name).stat().st_size for name in files),prior_inputs_verified=len(job['inputs_sha256']),prior_outputs_verified=len(done['outputs_sha256']),antecedents=inherited)


if __name__=='__main__':print(json.dumps(run(),indent=2))
