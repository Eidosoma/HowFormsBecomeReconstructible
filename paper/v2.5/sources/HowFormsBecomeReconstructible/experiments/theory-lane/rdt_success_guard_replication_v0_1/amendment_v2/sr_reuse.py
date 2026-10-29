"""Reuse only the fully verified qualification that failed its old time gate."""
from pathlib import Path
from sr_common import ROOT,P,read,sha,binding
import ledger
import sr_acquire
import sr_verification


def timing_gate(acquisition_seconds,continuation_seconds,elapsed):
    a=max(P['resource']['historical_acquisition_floor'],acquisition_seconds)
    f=max(P['resource']['historical_continuation_floor'],continuation_seconds)
    forecast=180+1.5*(3*a+4*f)
    cap=P['resource']['target_seconds']
    okay=(forecast+120<=cap and elapsed<=P['resource']['qualification_seconds'] and elapsed+cap<=3600)
    return dict(status='PASS' if okay else 'FAILED',guarded_acquisition_unit_seconds=a,
        guarded_continuation_unit_seconds=f,target_forecast_seconds=forecast,
        target_completion_reserve_seconds=120,target_hard_seconds=cap,combined_hard_seconds=3600,
        charged_prior_qualification_seconds=elapsed,charged_acquisition_waves=3,charged_continuation_waves=4)


def verify_reuse():
    prior=ROOT/'context/prior_inputs';run=ROOT/'context/reused_qualification'
    source=read(ROOT/'context/QUALIFICATION_REUSE_BINDING.json')
    original=read(prior/'protocol.json')
    ignored={'status','resource','qualification','source_pricing_sha256','software_test_count','budget_amendment'}
    if {k:v for k,v in P.items() if k not in ignored}!={k:v for k,v in original.items() if k not in ignored}:
        raise ValueError('Scientific protocol differs from the original fixed replication')
    resource=dict(P['resource']);resource['qualification_seconds']=600;resource['target_seconds']=3000
    if resource!=original['resource'] or P['resource']['qualification_seconds']!=400 or P['resource']['target_seconds']!=3200:
        raise ValueError('Only the declared400/3200-second budget allocation may change')
    failure=read(run/'FAILED.json');old=read(run/'QUALIFICATION.json')
    if failure['acquisition_started'] or failure['scientific_futures_started']:
        raise ValueError('Original attempt exposed scientific outcomes; this amendment is disallowed')
    if failure['traceback'].splitlines()[-1]!='RuntimeError: Full-cap forecast does not fit the fixed one-hour design':
        raise ValueError('The previous failure was not solely the time gate')
    if (run/'acquisition').exists() or (run/'scientific').exists():raise ValueError('Unexpected scientific source data')
    for path,expected in [(prior/'INPUTS.json',source['original_input_manifest_sha256']),
                          (run/'QUALIFICATION.json',source['original_qualification_sha256']),
                          (run/'FAILED.json',source['original_failure_sha256']),
                          (run/'qualification_SEAL.json',source['original_seal_sha256'])]:
        if sha(path)!=expected:raise ValueError('Prior qualification binding changed')
    prior_files=read(prior/'INPUTS.json')['sha256']
    for rel,digest in prior_files.items():
        if sha(prior/rel)!=digest:raise ValueError('Original frozen input changed')
    unchanged=['sr_common.py','sr_acquire.py','sr_source.py','sr_policy.py','sr_forcing.py','sr_worker.py',
               'sr_unit_audit.py','sr_analysis.py','sr_verification.py']
    unchanged += [rel for rel in prior_files if rel.startswith('native/')]
    for rel in unchanged:
        if sha(ROOT/rel)!=prior_files[rel]:raise ValueError('Qualified scientific implementation changed: '+rel)
    if sha(ROOT/'sr_schedule.py')!=prior_files['sr_run.py']:raise ValueError('Original scheduling helpers changed')
    old_binding=dict(inputs_sha256=sha(prior/'INPUTS.json'),protocol_sha256=sha(prior/'protocol.json'))
    if old['binding']!=old_binding:raise ValueError('Qualification belongs to different inputs')
    payloads=[]
    for block in [34000,-3,-2,-1]:
        folder=run/'qualification_acquisition'/f'b{block}'
        entry=ledger.verify(folder,dict(binding=old_binding,kind='acquire',stage='qualification',block=block,legacy=block==34000))
        payload=entry['payload'];sr_acquire.check_rows(payload['rows'],block)
        check=read(folder/'VERIFICATION.json')
        if check['status']!='PASS' or not check['full_teaching_replay']['byte_exact']:raise ValueError('Acquisition qualification failed')
        if block==34000 and not check['legacy_byte_exact']:raise ValueError('Legacy replay did not qualify')
        if payload['native_reads']!=896 or payload['flat_native_reads']!=12:raise ValueError('Acquisition read charge differs')
        payloads.append(payload)
    qacq=dict(status='PASS',units=4,native_reads=sum(v['native_reads'] for v in payloads),
              flat_reads=sum(v['flat_native_reads'] for v in payloads),teaching_episodes=8,
              maximum_unit_seconds=max(v['wall_seconds'] for v in payloads),worker_cpu_seconds=sum(v['cpu_seconds'] for v in payloads))
    _,qfuture=sr_verification.verify_stage(run,'qualification',[(b,n) for b in [-2,-1] for n in [18,24]],source['original_seal_sha256'])
    if qacq!=old['acquisition'] or qfuture!=old['continuation'] or not all(v>0 for v in qfuture['policy_branch_coverage'].values()):
        raise ValueError('Reused qualification checks differ from their original receipts')
    spent=failure['wall_seconds']
    if spent!=source['charged_prior_qualification_seconds']:raise ValueError('Prior execution charge differs')
    timing=timing_gate(qacq['maximum_unit_seconds'],qfuture['maximum_unit_wall_seconds'],spent)
    if timing['status']!='PASS':raise ValueError('Amended budget still does not fit one hour')
    proof=dict(status='PASS',original_input_files_verified=len(prior_files),unchanged_scientific_files_verified=len(unchanged),
        original_qualification_sha256=source['original_qualification_sha256'],original_failure_sha256=source['original_failure_sha256'],
        prior_time_gate_status=old['status'],original_scientific_acquisition_absent=True,original_scientific_futures_absent=True,
        native_qualification_reexecuted=False,charged_prior_execution_seconds=spent,scientific_protocol_unchanged=True)
    return timing,qacq,qfuture,proof
