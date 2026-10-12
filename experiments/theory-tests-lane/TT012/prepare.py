"""Snapshot completed approximate-alignment evidence, bound to TT011."""
from pathlib import Path
import json
import shutil
import support as s


def run():
    fleet=s.HERE.parent.parent;destination=s.HERE/'source';destination.mkdir(exist_ok=False)
    files={};origins={};bindings=[]
    def bind(path,digest=None,rel=None):
        path=Path(path).resolve();s.require(path.is_relative_to(fleet),'Local experiment evidence')
        actual=s.sha(path);s.require(digest is None or actual==digest,'Source identity '+str(path))
        if str(path) not in origins:
            target=destination/(rel or 'upstream/'+str(path.relative_to(fleet)))
            target.parent.mkdir(parents=True,exist_ok=True)
            with target.open('xb') as f:f.write(path.read_bytes())
            s.require(s.sha(target)==actual,'Snapshot bytes')
            origins[str(path)]=str(target.relative_to(s.HERE));files[origins[str(path)]]=actual
        bindings.append(dict(original=str(path),local=origins[str(path)],sha256=actual))
    prior=s.HERE.parent/'TT011';close=s.read(prior/'CLOSEOUT.json')
    s.require(close['status']=='PASS' and close['completion_sha256']=='aa3dc7157f8ad7cf2ab2870d4af0ad8cc03aceec1b5b402f8735b5f618c88175','Completed TT011 identity')
    bind(prior/'CLOSEOUT.json',rel='tt011/CLOSEOUT.json')
    bind(prior/'runs/audit_v1/COMPLETE.json',close['completion_sha256'],'tt011/COMPLETE.json')
    bind(prior/'jobs/audit_v1/job.json',close['job_sha256'],'tt011/job.json')
    job=s.read(prior/'jobs/audit_v1/job.json');done=s.read(prior/'runs/audit_v1/COMPLETE.json')
    for rel,digest in job['inputs_sha256'].items():s.require(s.sha(prior/'jobs/audit_v1/inputs/TT011'/rel)==digest,'TT011 frozen input')
    for rel,digest in done['outputs_sha256'].items():s.require(s.sha(prior/'runs/audit_v1'/rel)==digest,'TT011 committed output')
    bind(prior/'jobs/audit_v1/inputs/TT011/SOURCE_RECEIPT.json',job['inputs_sha256']['SOURCE_RECEIPT.json'],'tt011/SOURCE_RECEIPT.json')
    antecedents=s.read(prior/'jobs/audit_v1/inputs/TT011/SOURCE_RECEIPT.json')
    run=fleet/'theory-lane/p05_approximate_alignment_v0_1/runs/pilot_v1'
    bind(run/'COMPLETE.json',rel='approx/run/COMPLETE.json');complete=s.read(run/'COMPLETE.json')
    s.require(complete['status']=='COMPLETE' and complete['trajectories']==9792,'Source complete assay')
    for rel,digest in complete['outputs_sha256'].items():bind(run/rel,digest,'approx/run/'+rel)
    manifest=s.read(run/'manifest.json')
    for rel,digest in manifest['files_sha256'].items():bind(run/'inputs'/rel,digest,'approx/inputs/'+rel)
    prep=s.read(run/'inputs/prepared/COMPLETE.json')
    s.require(s.sha(run/'inputs/prepared/COMPLETE.json')==manifest['prepared_complete_sha256'],'Prepared binding')
    for rel,digest in prep['outputs_sha256'].items():bind(run/'inputs/prepared'/rel,digest)
    inherited=0
    for path,digest in prep['sources_sha256'].items():
        bind(path,digest)
        if '/p05_backup_task_swap_v0_1/' in path:
            s.require(path in antecedents['origins'],'P05 source audited in TT011')
            s.require(job['inputs_sha256'][antecedents['origins'][path]]==digest,'P05 antecedent exact audit binding');inherited+=1
    exact=fleet/'theory-lane/p05_sign_alignment_audit_v0_1'
    s.require(s.sha(exact/'COMPLETE.json')==manifest['config']['alignment_audit_complete_sha256'],'Exact audit identity')
    for rel,digest in s.read(exact/'COMPLETE.json')['files_sha256'].items():bind(exact/rel,digest,'exact/'+rel)
    receipt=dict(status='PASS',recorded_utc=s.utc(),files_sha256=files,origins=origins,bindings=bindings,
        prior_inputs_verified=len(job['inputs_sha256']),prior_outputs_verified=len(done['outputs_sha256']),
        P05_antecedents_bound_to_TT011=inherited,source_code_executed=False,performance_report_inspected=False,
        source_completion_sha256=s.sha(run/'COMPLETE.json'),new_scientific_outcomes=False,
        exact_fallback_supplement='Hash-bound background only; not independently recertified by TT012')
    s.dump(s.HERE/'SOURCE_RECEIPT.json',receipt)
    with (s.HERE.parent/'exposure_register.jsonl').open('a') as f:f.write(json.dumps(dict(event='TT012_SOURCE_FREEZE',recorded_utc=s.utc(),source_receipt_sha256=s.sha(s.HERE/'SOURCE_RECEIPT.json'),files=len(files),performance_report_inspected=False))+'\n')
    return dict(files=len(files),bindings=len(bindings),bytes=sum((s.HERE/n).stat().st_size for n in files),prior_inputs_verified=len(job['inputs_sha256']),prior_outputs_verified=len(done['outputs_sha256']),source_complete=receipt['source_completion_sha256'])


if __name__=='__main__':print(json.dumps(run(),indent=2))
