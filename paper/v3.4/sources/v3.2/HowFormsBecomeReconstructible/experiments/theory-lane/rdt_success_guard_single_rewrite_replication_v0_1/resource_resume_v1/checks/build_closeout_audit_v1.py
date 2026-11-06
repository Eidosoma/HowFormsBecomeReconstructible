"""Build the independent closeout from the previously audited five-policy scalar checks."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LANE = ROOT.parent.parent
template = (LANE/'rdt_success_guard_single_rewrite_v0_1/checks/audit_closeout_v1.py').read_text()

header = r'''"""Independent saved-evidence audit of the resumed fresh-founder replication.

No study modules or native simulations. Checks original/continued evidence,
boundary selection, raw scalar endpoints, independent flat chains, exact counts,
the original frozen inference, resource amendment and all imported costs.
"""
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path
import hashlib
import json
import math
import time
import numpy as np
from scipy.stats import t

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT.parent
INPUT = PACKAGE/'jobs/replication_v1/inputs'
CONTROL = ROOT/'jobs/resume_v1/inputs'
RUN = ROOT/'runs/resume_v1'
OLD_RUN = PACKAGE/'runs/replication_v1'
DEST = ROOT/'checks/INDEPENDENT_CLOSEOUT_AUDIT.json'
EXPECTED_INPUT = '13c38438056b96bb18d4b57edc1296bbbd82ddf626942853bcb983d5f4f6c60c'
EXPECTED_CONTROL = '5bf293b5561316e1ccf3052e71357f6effea5e1153d937bba37456c3a408d580'
EXPECTED_COMPLETE = '5cc36b7fd9f8769c6937f3f83a0008f49e15dd19cfc30afda576de529ab279e9'
started = time.monotonic()


def read(path): return json.loads(path.read_text())


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def same(a, b):
    assert a.shape == b.shape and a.dtype == b.dtype and a.tobytes() == b.tobytes()


def verify_manifest(root, manifest):
    for name, expected in manifest['sha256'].items():
        assert not Path(name).is_absolute() and '..' not in Path(name).parts
        path = root/name
        assert path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(root.resolve())
        assert sha(path) == expected, name
    return len(manifest['sha256'])


assert not DEST.exists()
assert sha(INPUT/'INPUTS.json') == EXPECTED_INPUT
assert sha(CONTROL/'INPUTS.json') == EXPECTED_CONTROL
assert sha(RUN/'COMPLETE.json') == EXPECTED_COMPLETE
complete, p, plan = read(RUN/'COMPLETE.json'), read(INPUT/'protocol.json'), read(CONTROL/'PLAN.json')
assert complete['scientific_input_manifest_sha256'] == EXPECTED_INPUT
assert complete['controller_input_manifest_sha256'] == EXPECTED_CONTROL
assert sha(RUN/'OUTPUTS.json') == complete['output_manifest_sha256']
input_count = verify_manifest(INPUT, read(INPUT/'INPUTS.json'))
controller_count = verify_manifest(CONTROL, read(CONTROL/'INPUTS.json'))
output_manifest = read(RUN/'OUTPUTS.json')
output_count = verify_manifest(RUN, output_manifest)
assert (input_count, controller_count, output_count) == (76, 8, 562)
assert set(output_manifest['sha256']) == {
    str(q.relative_to(RUN)) for q in RUN.rglob('*') if q.is_file()
    and str(q.relative_to(RUN)) not in ['COMPLETE.json','OUTPUTS.json','STATUS.json','HANDOFF.json']}
assert not (RUN/'FAILED.json').exists()
assert read(RUN/'STATUS.json')['complete_sha256'] == EXPECTED_COMPLETE
assert read(ROOT/'checks/CLOSEOUT_HOST_PROCESS_CHECK.json')['status'] == 'NO_REPLICATION_PROCESSES'
stopped = Path(plan['source_stopped_manifest'])
assert sha(stopped) == plan['source_stopped_manifest_sha256']
old_manifest = read(stopped)
assert verify_manifest(OLD_RUN, old_manifest) == 503
assert set(old_manifest['sha256']) == {str(q.relative_to(OLD_RUN)) for q in OLD_RUN.rglob('*') if q.is_file()}
assert sha(OLD_RUN/'FAILED.json') == plan['source_failure_sha256']
assert sha(Path(plan['source_closeout'])) == plan['source_closeout_sha256']
assert read(OLD_RUN/'FAILED.json')['traceback'].splitlines()[-1] == 'OSError: Required free disk reserve unavailable'
assert not (OLD_RUN/'ANALYSIS.json').exists() and not (OLD_RUN/'COMPLETE.json').exists()
for field in ['native_files_required_byte_identical','other_files_required_byte_identical']:
    for name, expected in read(INPUT/'COPY_RECEIPT.json')[field].items():
        assert sha(INPUT/name) == expected
for name, expected in read(INPUT/'SOFTWARE_QUALIFICATION.json')['implementation_sha256'].items():
    assert sha(INPUT/name) == expected
for name, expected in read(CONTROL/'SOFTWARE_QUALIFICATION.json')['source_sha256'].items():
    assert sha(CONTROL/name) == expected
assert plan['primary_contrast'] == p['primary'] and plan['scientific_fields_changed'] == []
assert (plan['workers'],plan['parent_reserve'],plan['shared_thread_limit']) == (4,1,12)
assert plan['minimum_free_bytes'] == p['resource']['min_free_bytes'] == 4000000000
assert plan['maximum_combined_saved_bytes'] == p['resource']['max_saved_bytes'] == 3000000000
assert plan['new_acquisitions'] == plan['new_native_qualification'] == 0
assert plan['imported_scientific_blocks'] == complete['imported_scientific_blocks'] == list(range(4))
assert plan['remaining_scientific_blocks'] == complete['new_scientific_blocks'] == list(range(4,16))
imports = read(RUN/'IMPORTED.json')
assert imports['files'] == verify_manifest(RUN, imports) == 426
expected_imports = {r:d for r,d in old_manifest['sha256'].items()
                    if any(r==base or r.startswith(base+'/') for base in plan['import_paths'])}
assert imports['sha256'] == expected_imports
assert all(sha(OLD_RUN/name) == sha(RUN/name) == expected for name,expected in expected_imports.items())
assert imports['copied_bytes'] == sum((RUN/name).stat().st_size for name in expected_imports) == 182331918
assert set(q.name for q in (OLD_RUN/'scientific').iterdir()) == {f'n24_b{b}' for b in range(4)}
assert set(q.name for q in (RUN/'scientific').iterdir()) == {f'n24_b{b}' for b in range(16)}

old_start = read(OLD_RUN/'START.json'); failure = read(OLD_RUN/'FAILED.json')
release = read(RUN/'FUTURE_RELEASE.json'); resumed = read(RUN/'RESUME_RELEASE.json')
resume_start = read(RUN/'START.json')
prior_target = failure['wall_seconds'] - ((release['target_deadline_epoch']-3400)-(old_start['deadline_epoch']-3600))
assert abs(prior_target-plan['prior_target_wall_seconds']) < 1e-9
assert complete['prior_wall_seconds'] == failure['wall_seconds'] == plan['prior_wall_seconds']
assert abs(complete['wall_seconds']-complete['prior_wall_seconds']-complete['resumed_wall_seconds']) < 1e-9
assert abs(complete['target_charged_seconds']-prior_target-complete['resumed_wall_seconds']) < 1e-9
assert plan['resume_hard_seconds'] == math.floor(min(3600-failure['wall_seconds'],3400-prior_target)) == 2449
assert complete['resumed_wall_seconds'] < 2449 and complete['wall_seconds'] < 3600 and complete['target_charged_seconds'] < 3400
assert resumed['new_deadline_epoch'] == resume_start['deadline_epoch']
assert datetime.fromisoformat(complete['utc']).timestamp() < resume_start['deadline_epoch']
assert datetime.fromisoformat(resume_start['utc']).timestamp() > old_start['deadline_epoch']
assert complete['original_absolute_deadline_expired']
assert resumed['controller_input_sha256'] == EXPECTED_CONTROL
assert resumed['original_future_release_sha256'] == sha(RUN/'FUTURE_RELEASE.json')
assert resumed['imported_sha256'] == sha(RUN/'IMPORTED.json')
assert complete['capacity_wait_seconds'] == failure['capacity_wait_seconds'] == 0
assert plan['pricing']['guarded_wave_floor_seconds'] == read(OLD_RUN/'tasks/scientific_wave_0_COMPLETE.json')['wall_seconds']
assert plan['pricing']['forecast_including_all_reserves_seconds'] == 180+1.5*3*plan['pricing']['guarded_wave_floor_seconds']+180+120
assert plan['pricing']['forecast_including_all_reserves_seconds'] < 2449

panel = read(RUN/'COHORT.json'); qualification = read(RUN/'QUALIFICATION.json')
blocks, policies = panel['blocks'], p['policies']
assert blocks == list(range(16)) and panel['attempted_blocks'] == blocks and panel['eligible_blocks'] == blocks
assert not panel['ineligible_blocks'] and not panel['surplus_blocks'] and panel['complete']
assert policies == ['always_promote','matched_random','writer_success_guard','protected_retain','first_success_once']
assert p['primary']['components'] == ['24_independent_guard_minus_first_success_once']
assert p['primary']['degrees_of_freedom'] == 15 and p['primary_generations'] == list(range(16,34))
assert abs(p['primary']['critical_two_sided95']-float(t.ppf(.975,15))) < 1e-12
assert abs(p['primary']['critical_one_sided95']-float(t.ppf(.95,15))) < 1e-12
assert len(panel['rows']) == 64
assert sha(RUN/'COHORT.json') == complete['cohort_sha256'] == release['cohort_sha256']
assert sha(RUN/'scientific_SEAL.json') == complete['policy_seal_sha256'] == release['policy_seal_sha256']
assert sha(RUN/'QUALIFICATION.json') == complete['qualification_sha256'] == release['qualification_sha256']
assert qualification['status'] == 'PASS' and qualification['qualification_elapsed_seconds'] < 600
assert qualification['target_forecast_seconds']+120 <= qualification['available_target_seconds']
assert datetime.fromisoformat(read(INPUT/'INPUTS.json')['utc']) < datetime.fromisoformat(old_start['utc'])
assert datetime.fromisoformat(read(CONTROL/'INPUTS.json')['utc']) < datetime.fromisoformat(resume_start['utc'])
assert datetime.fromisoformat(panel['utc']) <= datetime.fromisoformat(read(RUN/'scientific_SEAL.json')['utc']) <= datetime.fromisoformat(release['utc'])

binding = {'inputs_sha256':EXPECTED_INPUT,'protocol_sha256':sha(INPUT/'protocol.json')}
histories = read(INPUT/'native/protocol.json')['acquisition']['histories']
source_packets = {}; selected = {}; source_rows_checked = 0; acquisition_commits = []
for stage, stage_blocks, parent in [('scientific',blocks,'acquisition'),('qualification',[34000,-2],'qualification_acquisition')]:
    for block in stage_blocks:
        folder = RUN/parent/f'b{block}'
        commit = read(folder/'COMMIT.json')
        legacy = stage=='qualification' and block==34000
        assert commit['identity'] == dict(binding=binding,kind='acquire',stage=stage,block=block,legacy=legacy)
        verify_manifest(folder,commit)
        assert set(commit['sha256']) == {str(f.relative_to(folder)) for f in folder.rglob('*') if f.is_file() and f.name!='COMMIT.json'}
        rows = read(folder/'ENROLLMENT.json')['rows']
        assert rows == commit['payload']['rows'] and len(rows)==64
        assert commit['payload']['native_reads']==896 and commit['payload']['flat_native_reads']==12
        assert commit['payload']['teaching_episodes']==2
        assert commit['payload']['namespaces'] == dict(acquisition=p['namespace']+'/'+stage+'/acquisition',selection=p['namespace']+'/'+stage+'/selection')
        audit = read(folder/'VERIFICATION.json')
        assert audit['status']=='PASS' and audit['records']==64
        assert audit['full_teaching_replay']==dict(teaching_episodes_replayed=2,byte_exact=True)
        assert sum(v['flat_native_reads'] for v in audit['native_flat_audits'])==12
        assert all(v['byte_exact'] for v in audit['native_flat_audits'])
        assert audit['legacy_byte_exact']==legacy
        assert {tuple(r['key']) for r in rows} == {(block,h,f,r) for h in histories for f in range(4) for r in range(4)}
        with np.load(folder/'boundary.npz',allow_pickle=False) as z:
            outgoing,means,end=z['outgoing'],z['mean_ports'],z['end']
        if legacy:
            with np.load(INPUT/'native/context/legacy_g14.npz',allow_pickle=False) as z:
                same(outgoing,z['outgoing']);same(means,z['mean_ports']);same(end,z['end'])
        for row in rows:
            idx=(histories.index(row['history']),row['founder'],row['recipient'])
            rule=1 if row['founder']%2==0 else -1
            assert row['rule']==rule and row['block']==block
            aligned=means[idx]*rule*np.array([[1.,-1.],[-1.,1.]])
            assert int(aligned.min()>.25)==row['current_pass']
            assert np.allclose(aligned.ravel(),row['boundary'][:4],rtol=0,atol=1e-12)
            assert hashlib.sha256(outgoing[idx].tobytes()).hexdigest()==row['packet_sha256']
            expected_rank=hashlib.sha256(json.dumps([p['namespace']+'/'+stage+'/selection',*row['key']],separators=(',',':')).encode()).hexdigest()
            assert expected_rank==row['selection_hash']
            source_rows_checked+=1
        if stage=='scientific':
            chosen=[]
            for label in [0,1]:
                groups=[[r for r in rows if r['current_pass']==label and r['rule']==rule] for rule in [-1,1]]
                if all(groups):chosen.extend([min(g,key=lambda r:r['selection_hash']) for g in groups])
                else:chosen.extend(sorted([r for r in rows if r['current_pass']==label],key=lambda r:r['selection_hash'])[:2])
            assert len(chosen)==4 and [sum(r['current_pass']==h for r in chosen) for h in [0,1]]==[2,2]
            selected[block]=chosen
            source_packets[block]=np.stack([np.frombuffer(outgoing[histories.index(r['history']),r['founder'],r['recipient']].tobytes(),dtype='<f8').reshape(2,16,16) for r in chosen])
            ref=next(r for r in panel['acquisitions'] if r['block']==block)
            assert ref['path']==f'acquisition/b{block}' and ref['commit_sha256']==sha(folder/'COMMIT.json')
            assert datetime.fromisoformat(commit['utc']) < datetime.fromisoformat(panel['utc'])
        acquisition_commits.append(dict(stage=stage,block=block,sha256=sha(folder/'COMMIT.json')))
assert panel['rows']==[r for b in blocks for r in selected[b]]
assert source_rows_checked==1152 and len(acquisition_commits)==18
'''

body = template[template.index("all_rows = read(RUN/'OUTCOMES.json')"):template.index("admissions = [ROOT/")]
body = body.replace("'development'", "'scientific'")
body = body.replace("source_packets[blocks.index(block)]", "source_packets[block]")
body = body.replace('== 560', '== 320')
body = body.replace('units == 32 and readouts == 12160 and flat_chains == 640 and decisions == 576',
                    'units == 18 and readouts == 6840 and flat_chains == 360 and decisions == 324')
body = body.replace('guard_rewrites=1643, random_rewrites=1643, single_rewrites=98,\n                                   single_retention_after_use=1573, additional_guard_rewrites=1545',
                    'guard_rewrites=808, random_rewrites=808, single_rewrites=49,\n                                   single_retention_after_use=789, additional_guard_rewrites=759')
body = body.replace('== 28','== 16').replace('/28','/16').replace('/27','/15')
body = body.replace("assert primary['lower_one_sided95'] > 0\nassert complete['decision'] == analysis['decision'] == 'REPEATED_REWRITE_DEVELOPMENT_SUPPORTED'",
'''assert primary['lower_one_sided95'] <= 0 < primary['upper_one_sided95']
assert analysis['primary']['24_independent_guard_minus_first_success_once']['decision']=='UNRESOLVED'
assert complete['decision'] == analysis['decision'] == 'REPEATED_REWRITE_REPLICATION_UNRESOLVED'
assert all_rows and counts['writer_success_guard']['downstream_successes']==821
assert counts['first_success_once']['downstream_successes']==815
assert primary_values == [Fraction(n,72) for n in [1,0,-1,2,2,-1,1,0,0,0,1,-1,0,1,1,0]]''')

tail = r'''
# Original and resumed resource admissions are distinct; the rejected disk wave
# passed CPU admission but started no workers. Count every physical batch once.
admissions = [PACKAGE/'jobs/replication_v1/CPU_ADMISSION.json',ROOT/'jobs/resume_v1/CPU_ADMISSION.json']
admissions += sorted((OLD_RUN/'tasks').glob('*_ADMISSION.json'))+sorted((RUN/'tasks').glob('*_ADMISSION.json'))
for path in admissions:
    record=read(path)
    assert record['within_limit'] and record['planned_threads']==5
    assert record['other_active_or_recently_busy_threads']+5<=record['shared_limit']==12
assert len(admissions)==12
old_waves=sorted((OLD_RUN/'tasks').glob('*_COMPLETE.json'))
new_waves=sorted((RUN/'tasks').glob('*_COMPLETE.json'))
assert len(old_waves)==6 and len(new_waves)==3
assert all(read(f)['units']==4 for f in old_waves+new_waves)
assert not (OLD_RUN/'tasks/scientific_wave_1_STARTED.json').exists()
assert len(list((OLD_RUN/'tasks').glob('*_ADMISSION_attempt_*.json')))==7
assert len(list((RUN/'tasks').glob('*_ADMISSION_attempt_*.json')))==3
assert resumed['remaining_blocks']==list(range(4,16))
for block in range(4,16):
    task=read(RUN/'scientific'/f'n24_b{block}'/'START.json')['task']
    assert task['binding']==binding and task['deadline']==resumed['new_deadline_epoch']
    assert Path(task['run'])==RUN and Path(task['seal_path'])==RUN/'scientific_SEAL.json'
    assert task['parent_pid']==2022598
    assert datetime.fromisoformat(read(RUN/'scientific'/f'n24_b{block}'/'START.json')['utc'])>=datetime.fromisoformat(resumed['utc'])
for name in ['DISK_ADMISSION.json','DISK_BEFORE_WAVE_1.json','DISK_BEFORE_WAVE_2.json','DISK_BEFORE_WAVE_3.json','FINAL_DISK.json']:
    record=read(RUN/name)
    assert record['free_bytes']>=4000000000 and record['combined_saved_bytes']<=3000000000
for name in ['PRIOR_VERIFICATION.json','FINAL_SOURCE_VERIFICATION.json']:
    record=read(RUN/name)
    assert record['status']=='PASS' and record['original_input_files']==76 and record['original_output_files']==503
software=read(INPUT/'SOFTWARE_QUALIFICATION.json')
controller_software=read(CONTROL/'SOFTWARE_QUALIFICATION.json')
assert software['status']=='PASS' and software['tests_passed']==38
assert controller_software['status']=='PASS' and controller_software['tests_passed']==32
assert controller_software['new_native_reads']==controller_software['new_short_native_reads']==0
assert complete['target_continuation']['native_reads']==complete['target_continuation']['flat_reads']==6080
assert complete['qualification_continuation']['native_reads']==complete['qualification_continuation']['flat_reads']==760
assert complete['acquisition']['native_reads']==14336 and complete['acquisition']['flat_reads']==192
assert complete['qualification_acquisition']['native_reads']==1792 and complete['qualification_acquisition']['flat_reads']==24
assert 16*908+16*760+2*908+2*760==complete['full_native_reads_total']==30024
assert 12*760==complete['newly_run_full_native_reads']==9120
assert complete['prior_full_native_reads']==20904
pause_seconds=datetime.fromisoformat(resume_start['utc']).timestamp()-datetime.fromisoformat(failure['utc']).timestamp()
counts['writer_success_guard']['extra_rewrites_over_single']=counts['writer_success_guard']['promotions']-counts['first_success_once']['promotions']
capture=Fraction(counts['first_success_once']['downstream_successes']-counts['protected_retain']['downstream_successes'],
                 counts['writer_success_guard']['downstream_successes']-counts['protected_retain']['downstream_successes'])
assert capture==Fraction(113,119)
assert sha(RUN/'COMPLETE.json')==EXPECTED_COMPLETE
assert verify_manifest(OLD_RUN,old_manifest)==503
assert verify_manifest(INPUT,read(INPUT/'INPUTS.json'))==76
assert verify_manifest(CONTROL,read(CONTROL/'INPUTS.json'))==8
assert verify_manifest(RUN,output_manifest)==562
result=dict(utc=datetime.now(timezone.utc).isoformat(),status='PASS',script_sha256=sha(Path(__file__)),
    scientific_input_sha256=EXPECTED_INPUT,controller_input_sha256=EXPECTED_CONTROL,complete_sha256=EXPECTED_COMPLETE,
    output_manifest_sha256=sha(RUN/'OUTPUTS.json'),scientific_input_files_verified=input_count,
    controller_input_files_verified=controller_count,output_files_verified=output_count,
    preserved_stopped_run_files=503,byte_identical_imported_files=426,
    acquisition_commitments_verified=18,boundary_rows_scored_and_selection_hashes_checked=source_rows_checked,
    source_packets_verified=64,complete_target_outcomes_verified=320,units_verified=units,
    raw_readouts_rescored=readouts,saved_flat_chains_verified=flat_chains,
    actual_decision_quota_checks=decisions,target_decision_quota_checks=288,policy_state_totals=totals,
    exact_policy_and_primary_block_summaries=256,exact_descriptive_recovery_contributions=2,
    primary=primary,all_policy_means=overall,all_policy_counts=counts,recovery_descriptive=recovery,
    descriptive_single_rewrite_share_of_guard_gain_over_retention=float(capture),
    cpu_admissions_checked=12,completed_worker_batches_checked=9,
    full_native_readers_including_qualification=30024,new_readers_after_resume=9120,
    software_full_readers_separate=software['full2048_step_reader_calls'],
    software_short32_readers_separate=software['short32_step_reader_calls'],
    controller_software_reader_calls=0,wall_seconds=complete['wall_seconds'],
    resumed_wall_seconds=complete['resumed_wall_seconds'],target_charged_seconds=complete['target_charged_seconds'],
    calendar_pause_seconds_excluded=pause_seconds,capacity_wait_seconds=0,
    native_worker_cpu_seconds=sum(complete[k]['worker_cpu_seconds'] for k in ['acquisition','target_continuation','qualification_acquisition','qualification_continuation']),
    closeout_audit_wall_seconds=time.monotonic()-started,new_native_dynamics=0,new_model_fits=0,
    scope='Independent saved evidence verification, source selection, raw scalar endpoints, full saved flat chains, allocation RNG, persistent single-rewrite memory, record inheritance, exact block reductions, unchanged imports and resource costs. No new native simulation or full forcing rerun.',
    decision=complete['decision'],prospective_fresh_founders_within_programme=True,
    hypothesis_and_sample_informed_by_development=True,external_preregistration=False,
    RDT_specific_validation=False,automatic_successor=False)
with DEST.open('x') as stream:
    json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
print(json.dumps({k:result[k] for k in ['status','output_files_verified','complete_target_outcomes_verified',
    'raw_readouts_rescored','saved_flat_chains_verified','primary','all_policy_counts','closeout_audit_wall_seconds']}))
'''

destination=ROOT/'checks/audit_closeout_v1.py'
with destination.open('x') as stream:
    stream.write(header+body+tail)
print(destination)
