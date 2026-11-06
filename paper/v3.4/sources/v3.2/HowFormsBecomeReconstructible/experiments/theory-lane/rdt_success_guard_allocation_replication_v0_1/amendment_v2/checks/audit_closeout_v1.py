"""Read-only independent closeout of frozen allocation evidence; no dynamics.

Uses no study modules. Recomputes endpoints from saved windows, actions from
the declared rule, and paired block intervals with exact rational counts.
Writes a new audit receipt only after every assertion passes.
"""
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path
import hashlib
import json
import math
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / 'jobs/replication_v2/inputs'
RUN = ROOT / 'runs/replication_v2'
DEST = ROOT / 'checks/INDEPENDENT_CLOSEOUT_AUDIT.json'
EXPECTED_INPUT = '27252383ef0b4e103f57a4c6575825dd0320d1759416bb62bcb69dd50cb577da'
EXPECTED_COMPLETE = 'b8a20f3a28bb4aa3865aa9e569fbea08a6329ebf92ec7838cf8c5ffee475f09b'
started = time.monotonic()


def read(path):
    return json.loads(path.read_text())


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def array_sha(value):
    return hashlib.sha256(np.ascontiguousarray(value).tobytes()).hexdigest()


def same(a, b):
    assert a.shape == b.shape and a.dtype == b.dtype
    assert a.tobytes() == b.tobytes()


def verify_manifest(root, manifest):
    for name, expected in manifest['sha256'].items():
        path = root / name
        assert not Path(name).is_absolute() and '..' not in Path(name).parts
        assert path.is_file() and not path.is_symlink(), name
        assert path.resolve().is_relative_to(root.resolve()), name
        assert sha(path) == expected, name
    return len(manifest['sha256'])


assert not DEST.exists()
assert sha(INPUT / 'INPUTS.json') == EXPECTED_INPUT
assert sha(RUN / 'COMPLETE.json') == EXPECTED_COMPLETE
complete = read(RUN / 'COMPLETE.json')
assert complete['inputs_sha256'] == EXPECTED_INPUT
assert sha(RUN / 'OUTPUTS.json') == complete['output_manifest_sha256']
input_manifest = read(INPUT / 'INPUTS.json')
output_manifest = read(RUN / 'OUTPUTS.json')
input_count = verify_manifest(INPUT, input_manifest)
output_count = verify_manifest(RUN, output_manifest)
assert input_count == 83 and output_count == 1095
assert not (RUN / 'FAILED.json').exists()
p = read(INPUT / 'protocol.json')
reuse = read(INPUT / 'context/REUSE.json')
OLD_INPUT = Path(reuse['source_inputs'])
OLD_RUN = Path(reuse['source_run'])
assert sha(OLD_INPUT / 'INPUTS.json') == reuse['source_input_manifest_sha256']
old_inputs = verify_manifest(OLD_INPUT, read(OLD_INPUT / 'INPUTS.json'))
old_outputs = verify_manifest(OLD_RUN, read(INPUT / 'context/prior_STOPPED_RUN_MANIFEST.json'))
assert old_inputs == 72 and old_outputs == 443
prior = read(OLD_INPUT / 'protocol.json')
allowed = {'resource','amendment','status','source_pricing_sha256','software_test_count'}
assert {k:v for k,v in p.items() if k not in allowed} == {k:v for k,v in prior.items() if k not in allowed}
for field in ['native_files_required_byte_identical','other_files_required_byte_identical']:
    for name, expected in read(INPUT / 'COPY_RECEIPT.json')[field].items():
        assert sha(INPUT / name) == sha(OLD_INPUT / name) == expected
assert (INPUT/'sr_acquire.py').read_text().split('def verify(')[0] == (OLD_INPUT/'sr_acquire.py').read_text().split('def verify(')[0]
assert not (OLD_RUN / 'scientific').exists()
assert not (OLD_RUN / 'FUTURE_RELEASE.json').exists()
assert read(OLD_RUN/'FAILED.json')['scientific_futures_started'] is False
assert sha(RUN/'QUALIFICATION.json') == sha(OLD_RUN/'QUALIFICATION.json') == complete['qualification_sha256']
assert sha(RUN/'QUALIFICATION_REUSE.json') == complete['qualification_reuse_sha256']
qual = read(RUN/'QUALIFICATION.json')
assert qual['status'] == 'PASS'
assert abs(complete['wall_seconds'] - complete['resumed_wall_seconds'] - complete['prior_charged_wall_seconds']) < 1e-9
assert complete['prior_charged_wall_seconds'] == read(OLD_RUN/'FAILED.json')['wall_seconds']
assert complete['wall_seconds'] < 7200 and complete['resumed_wall_seconds'] < 6500
assert complete['capacity_wait_seconds'] == 0
panel = read(RUN/'COHORT.json')
blocks = panel['blocks'];policies = p['policies']
assert len(blocks) == 28 and policies == ['always_promote','matched_random','writer_success_guard','protected_retain']
assert p['primary']['components'] == ['24_independent_guard_minus_matched_random']
assert p['primary']['degrees_of_freedom'] == 27 and p['primary_generations'] == list(range(16,34))
assert sha(RUN/'COHORT.json') == complete['cohort_sha256']
assert sha(RUN/'scientific_SEAL.json') == complete['policy_seal_sha256']
release = read(RUN/'FUTURE_RELEASE.json')
assert release['cohort_sha256'] == sha(RUN/'COHORT.json')
assert release['policy_seal_sha256'] == sha(RUN/'scientific_SEAL.json')
assert release['qualification_sha256'] == sha(RUN/'QUALIFICATION.json')
assert panel['attempted_blocks'] == list(range(35))
new_binding = {'inputs_sha256':EXPECTED_INPUT,'protocol_sha256':sha(INPUT/'protocol.json')}
source_histories = read(INPUT/'native/protocol.json')['acquisition']['histories']
selected_by_block = {};eligible = [];commits = [];acquisition_packets = {};all_source_rows = 0
for block in range(35):
    folder = RUN/'acquisition'/('b'+str(block))
    commit = read(folder/'COMMIT.json')
    expected_binding = reuse['source_binding'] if block < 14 else new_binding
    assert commit['identity'] == dict(binding=expected_binding,kind='acquire',stage='scientific',block=block,legacy=False)
    assert set(commit['sha256']) == {str(q.relative_to(folder)) for q in folder.rglob('*') if q.is_file() and q.name!='COMMIT.json'}
    verify_manifest(folder,commit)
    if block < 14:
        assert sha(folder/'COMMIT.json') == sha(OLD_RUN/'acquisition'/('b'+str(block))/'COMMIT.json') == reuse['imported_acquisition_commits'][str(block)]
    rows = read(folder/'ENROLLMENT.json')['rows']
    assert rows == commit['payload']['rows'] and len(rows) == 64
    assert commit['payload']['native_reads'] == 896 and commit['payload']['flat_native_reads'] == 12
    assert read(folder/'VERIFICATION.json')['status'] == 'PASS'
    keys = {(block,h,f,r) for h in source_histories for f in range(4) for r in range(4)}
    assert {tuple(row['key']) for row in rows} == keys
    with np.load(folder/'boundary.npz',allow_pickle=False) as z:
        outgoing=z['outgoing'];means=z['mean_ports']
    for row in rows:
        idx=(source_histories.index(row['history']),row['founder'],row['recipient'])
        rule=1 if row['founder']%2==0 else -1
        assert row['rule']==rule and row['block']==block
        aligned=means[idx]*rule*np.array([[1.,-1.],[-1.,1.]])
        assert int(aligned.min()>.25)==row['current_pass']
        assert np.allclose(aligned.ravel(),row['boundary'][:4],rtol=0,atol=1e-12)
        assert hashlib.sha256(outgoing[idx].tobytes()).hexdigest()==row['packet_sha256']
        expected_rank=hashlib.sha256(json.dumps([p['namespace']+'/scientific/selection',*row['key']],separators=(',',':')).encode()).hexdigest()
        assert expected_rank==row['selection_hash']
        all_source_rows+=1
    chosen=[]
    for label in [0,1]:
        pools=[[r for r in rows if r['current_pass']==label and r['rule']==rule] for rule in [-1,1]]
        if all(pools):chosen += [min(pool,key=lambda row:row['selection_hash']) for pool in pools]
        else:chosen += sorted([r for r in rows if r['current_pass']==label],key=lambda row:row['selection_hash'])[:2]
    if len(chosen)==4 and [sum(r['current_pass']==h for r in chosen) for h in [0,1]]==[2,2]:
        eligible.append(block);selected_by_block[block]=chosen
        if block in blocks:
            acquisition_packets[block]=np.stack([np.frombuffer(outgoing[source_histories.index(row['history']),row['founder'],row['recipient']].tobytes(),dtype='<f8').reshape(2,16,16) for row in chosen])
    commits.append(commit)
    assert datetime.fromisoformat(commit['utc']) < datetime.fromisoformat(panel['utc'])
assert panel['blocks']==eligible[:28]
assert panel['ineligible_blocks']==[6,23]
assert panel['surplus_blocks']==eligible[28:]==[30,31,32,33,34]
assert panel['rows']==[r for b in blocks for r in selected_by_block[b]]
assert all_source_rows==2240
assert datetime.fromisoformat(panel['utc']) <= datetime.fromisoformat(read(RUN/'scientific_SEAL.json')['utc']) <= datetime.fromisoformat(release['utc'])

all_rows = read(RUN / 'OUTCOMES.json')
assert len(all_rows) == 448
row_key = lambda r: (r['block'], r['regime'], tuple(r['key']), r['policy'])
by_key = {row_key(r): r for r in all_rows}
assert len(by_key) == 448
readouts = units = quotas = decision_quotas = flat_chains = 0
promotions = {'independent': 0}
branches = {stage: {'interior': 0, 'different': 0} for stage in p['stages']}
target_rows_checked = set()
native_reads = flat_reads = 0
base_hashes = {stage: set() for stage in p['stages']}

for stage, stage_blocks in [('qualification', p['qualification_blocks']), ('scientific', blocks)]:
    stage_run = OLD_RUN if stage=='qualification' else RUN
    expected_input = reuse['source_input_manifest_sha256'] if stage=='qualification' else EXPECTED_INPUT
    seal = read(stage_run / (stage + '_SEAL.json'))
    assert seal['blocks'] == stage_blocks and seal['policies'] == policies
    if stage == 'scientific':
        assert seal['rows'] == panel['rows']
    for block in stage_blocks:
        unit = stage_run / stage / ('n24_b' + str(block))
        unit_complete = read(unit / 'COMPLETE.json')
        assert unit_complete['status'] == 'COMPLETE_AUDITED'
        assert unit_complete['binding']['inputs_sha256'] == expected_input
        assert unit_complete['policy_seal_sha256'] == sha(stage_run / (stage + '_SEAL.json'))
        assert unit_complete['native_reads'] == unit_complete['flat_native_reads'] == 304
        native_reads += unit_complete['native_reads']
        flat_reads += unit_complete['flat_native_reads']
        units += 1
        unit_rows = read(unit / 'OUTCOMES.json')
        assert len(unit_rows) == 16
        if stage == 'scientific':
            assert all(by_key[row_key(r)] == r for r in unit_rows)
            assert datetime.fromisoformat(read(unit/'START.json')['utc']) >= datetime.fromisoformat(release['utc'])
        paired = []
        for regime in ['independent']:
            meta = read(unit / (regime + '.json'))
            raw_path = unit / (regime + '.npz')
            assert sha(raw_path) == meta['raw_sha256']
            assert meta['rows'] == [r for r in seal['rows'] if r['block'] == block]
            with np.load(raw_path, allow_pickle=False) as archive:
                z = {k: archive[k] for k in archive.files if k != '__index__'}
            assert z['windows'].shape == (19, 4, 32, 4, 2, 2)
            assert z['generations'].tolist() == list(range(15, 34))
            if stage=='scientific':same(z['initial_packets'],acquisition_packets[block])
            assert np.all(z['mask'].sum(axis=(-1,-2))==24)
            assert not np.array_equal(z['birth'][:,:,0],z['birth'][:,:,1])
            for name in ['incoming', 'end', 'windows', 'outgoing', 'actions']:
                same(z[name], z['flat_' + name])
            flat_chains += 16
            for j, row in enumerate(meta['rows']):
                assert array_sha(z['initial_packets'][j]) == row['packet_sha256']
                assert int(z['rules'][j]) == row['rule']
                for arm, policy in enumerate(policies):
                    same(z['incoming'][0, j, arm], z['initial_packets'][j])
                    same(z['windows'][0, j, :, arm], z['windows'][0, j, :, 0])
                    computed = []
                    for g in range(19):
                        scores = [math.fsum(float(v) for v in z['windows'][g, j, :, arm, c, port])
                                  / 32 * row['rule'] * (1 if c == port else -1)
                                  for c in (0, 1) for port in (0, 1)]
                        cls = 1 if min(scores) > .25 else -1 if max(scores) < -.25 else 0
                        assert cls == int(z['classes'][g, j, arm])
                        assert (cls == 1) == bool(z['passed'][g, j, arm])
                        computed.append(int(cls == 1))
                        readouts += 1
                    outcome = next(r for r in unit_rows if r['key'] == row['key']
                                   and r['policy'] == policy and r['regime'] == regime)
                    expected = dict(passed=computed, initial_pass=computed[0],
                                    downstream_successes=sum(computed[1:]), downstream_reads=18,
                                    terminal=computed[-1], uninterrupted=int(all(computed[1:])),
                                    opposite_reads=int((z['classes'][1:, j, arm] == -1).sum()),
                                    promotions=int(z['actions'][:-1, j, arm].sum()))
                    assert all(outcome[k] == v for k, v in expected.items())
                    if stage == 'scientific':
                        target_rows_checked.add(row_key(outcome))
            for g, generation in enumerate(range(15, 34)):
                seed_text = json.dumps([p['namespace'], stage, block, 0, generation,
                                        'promotion_subset'], separators=(',', ':')).encode()
                seed = int.from_bytes(hashlib.sha256(seed_text).digest()[:16], 'little')
                order = np.random.Generator(np.random.PCG64(seed)).permutation(np.arange(4, dtype=np.int64))
                same(order, z['allocation_order'][g])
                expected = np.zeros((4, 4), dtype=bool)
                if generation < 33:
                    expected[:, 0] = True
                    expected[:, 2] = z['passed'][g, :, 2].astype(bool)
                    expected[order[:int(expected[:, 2].sum())], 1] = True
                    k = int(expected[:, 2].sum())
                    branches[stage]['interior'] += int(0 < k < 4)
                    branches[stage]['different'] += int(not np.array_equal(expected[:, 1], expected[:, 2]))
                    decision_quotas += 1
                    if stage == 'scientific':
                        promotions[regime] += k
                    for j in range(4):
                        for arm in range(4):
                            same(z['incoming'][g + 1, j, arm],
                                 z['outgoing'][g, j, arm] if expected[j, arm] else z['incoming'][g, j, arm])
                same(expected, z['actions'][g])
                assert int(expected[:, 1].sum()) == int(expected[:, 2].sum()) == int(z['quota_count'][g])
                for j in range(4):
                    same(z['incoming'][g, j, 3], z['initial_packets'][j])
                quotas += 1
            same(z['final_packets'], z['incoming'][-1])
            for j in range(4):
                first = lambda arm: next((g for g in range(19) if z['passed'][g, j, arm]), None)
                assert first(2) == first(3)
            audit = read(unit / (regime + '_AUDIT.json'))
            assert audit['status'] == 'PASS' and audit['flat_reads'] == 304
            assert audit['native_readouts_independently_scored'] == 304
            assert audit['full_horizon_flat_policy_chains'] == 16
            assert meta['native_reads'] == meta['flat_native_reads'] == 304
            paired.append((z['mask'], z['allocation_order'], meta['forcing']))
        for rec in paired[0][2]:
            assert rec['regime']=='independent' and rec['injury']==24
            assert rec['base_forcing_sha256'] not in base_hashes[stage]
            base_hashes[stage].add(rec['base_forcing_sha256'])

assert len(target_rows_checked) == 448 and units == 32
assert readouts == native_reads == flat_reads == 9728
assert not (base_hashes['qualification'] & base_hashes['scientific'])
assert all(all(count > 0 for count in b.values()) for b in branches.values())

analysis = read(RUN / 'ANALYSIS.json')
summary_count = 0
def check_summary(record, values):
    global summary_count
    assert len(values) == 28
    mean = sum(values, Fraction()) / 28
    variance = sum((v - mean) ** 2 for v in values) / 27
    se = math.sqrt(float(variance / 28))
    expected = {'mean': float(mean),
                'lower': float(mean) - p['primary']['critical_two_sided95'] * se,
                'upper': float(mean) + p['primary']['critical_two_sided95'] * se,
                'lower_one_sided95': float(mean) - p['primary']['critical_one_sided95'] * se,
                'upper_one_sided95': float(mean) + p['primary']['critical_one_sided95'] * se}
    assert all(abs(record[k] - value) < 1e-12 for k, value in expected.items())
    assert all(abs(a - float(b)) < 1e-12 for a, b in zip(record['block_values'], values))
    assert record['zero_variance'] == (variance == 0)
    summary_count += 1
    return expected

overall = {}
for regime in ['independent']:
    overall[regime] = {}
    for label, history in [('all', None), ('historical_fail', 0), ('historical_pass', 1)]:
        values = {}
        for policy in policies:
            for metric in ['downstream_successes', 'terminal', 'uninterrupted', 'opposite_reads', 'promotions']:
                divisor = 18 if metric in ['downstream_successes', 'opposite_reads', 'promotions'] else 1
                vs = []
                for block in blocks:
                    subset = [r for r in all_rows if r['regime'] == regime and r['block'] == block
                              and r['policy'] == policy and (history is None or r['history_class'] == history)]
                    assert len(subset) == (4 if history is None else 2)
                    vs.append(Fraction(sum(r[metric] for r in subset), len(subset) * divisor))
                values[policy, metric] = vs
                check_summary(analysis['cells']['24'][regime][label][policy][metric], vs)
                if history is None:
                    overall[regime].setdefault(policy, {})[metric] = float(sum(vs) / 28)
        for a in policies:
            for b in policies:
                if a == b:
                    continue
                for metric in ['downstream_successes', 'terminal', 'uninterrupted']:
                    vs = [x - y for x, y in zip(values[a, metric], values[b, metric])]
                    key = a + '__minus__' + b + '__' + metric
                    check_summary(analysis['contrasts']['24'][regime][label][key], vs)
                    if (regime, label, a, b, metric) == ('independent', 'all',
                            'writer_success_guard', 'matched_random', 'downstream_successes'):
                        primary_values = vs
primary = check_summary(analysis['primary']['24_independent_guard_minus_matched_random'], primary_values)
assert primary['lower_one_sided95'] > 0
assert analysis['decision'] == complete['decision'] == 'ALLOCATION_REPLICATION_SUPPORTED'
assert summary_count == 169

recovery = {}
for regime in ['independent']:
    recovery[regime] = {}
    for initial, label in [(0, 'shared_g15_fail'), (1, 'shared_g15_pass')]:
        cells = {}
        for policy in policies:
            subset = [r for r in all_rows if (r['regime'], r['initial_pass'], r['policy']) == (regime, initial, policy)]
            expected = dict(packets=len(subset), downstream_success_count=sum(sum(r['passed'][1:]) for r in subset),
                            downstream_read_count=18 * len(subset), terminal_count=sum(r['passed'][-1] for r in subset),
                            uninterrupted_count=sum(all(r['passed'][1:]) for r in subset),
                            any_g16_33_success_count=sum(any(r['passed'][1:]) for r in subset))
            saved = analysis['recovery'][regime][label]['cells'][policy]
            assert all(saved[k] == v for k, v in expected.items())
            cells[policy] = expected
        recovery[regime][label] = cells

admissions = [ROOT/'jobs/replication_v2/CPU_ADMISSION.json'] + sorted((RUN/'tasks').glob('*_ADMISSION.json'))
for path in admissions:
    receipt=read(path)
    assert receipt['within_limit'] and receipt['planned_threads']==5
    assert receipt['other_active_or_recently_busy_threads']+5<=receipt['shared_limit']==12
waves=sorted((RUN/'tasks').glob('*_COMPLETE.json'))
assert len(waves)==13 and all(read(path)['units'] in [3,4] for path in waves)
assert sorted(read(path)['units'] for path in waves)==[3]*3+[4]*10
assert len(list((RUN/'tasks').glob('*_ADMISSION_attempt_*.json')))==13
scientific_full_acq=sum(c['payload']['native_reads']+c['payload']['flat_native_reads'] for c in commits)
qualification_acq=qual['acquisition']['native_reads']+qual['acquisition']['flat_reads']
full_reads=scientific_full_acq+qualification_acq+native_reads+flat_reads
assert full_reads==53960
for name in ['inputs_sha256','protocol_sha256']:
    assert read(RUN/'ACQUISITION_RELEASE.json')['binding'][name]==new_binding[name]
result=dict(utc=datetime.now(timezone.utc).isoformat(),status='PASS',script_sha256=sha(Path(__file__)),
    input_manifest_sha256=EXPECTED_INPUT,complete_sha256=EXPECTED_COMPLETE,output_manifest_sha256=sha(RUN/'OUTPUTS.json'),
    input_files_verified=input_count,output_files_verified=output_count,prior_input_files_verified=old_inputs,
    prior_output_files_verified=old_outputs,acquisition_commitments_verified=35,boundary_rows_independently_checked=all_source_rows,
    selected_blocks=blocks,selected_packets=112,ineligible_blocks=panel['ineligible_blocks'],surplus_blocks=panel['surplus_blocks'],
    target_outcomes_verified=len(target_rows_checked),units_verified=units,raw_readouts_rescored=readouts,
    saved_flat_chains_verified=flat_chains,actual_decision_quota_checks=decision_quotas,
    target_decision_quota_checks=28*18,target_rewrites_each_guard_and_random=promotions,
    allocation_branch_coverage=branches,exact_rational_block_summaries=summary_count,primary=primary,
    all_policy_means=overall,recovery_descriptive=recovery,cpu_admissions_checked=len(admissions),worker_batches_checked=len(waves),
    full_native_readers_including_reused_qualification=full_reads,new_native_readers_in_amendment=36092,
    software_full_readers_all_preparations_separate=128,software_and_diagnostic_short32_reads_lower_bound=1824,
    software_and_diagnostic_short32_reads_upper_bound=2432,
    charged_total_wall_seconds=complete['wall_seconds'],resumed_wall_seconds=complete['resumed_wall_seconds'],
    prior_charged_wall_seconds=complete['prior_charged_wall_seconds'],capacity_wait_seconds=0,
    closeout_audit_wall_seconds=time.monotonic()-started,new_native_dynamics=0,
    scope='Independent post-completion hash checks, original binding/reuse checks, acquisition g14 scalar labels and selection ranks, initial packet identity, raw continuation scoring, saved full flat chains, quota RNG/action/inheritance checks and exact block reductions. No native dynamics or full noise forcing rerun.',
    decision=complete['decision'],prospective_within_programme_replication=True,RDT_specific_validation=False)
with DEST.open('x') as stream:
    json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
print(json.dumps({k:result[k] for k in ['status','input_files_verified','output_files_verified','prior_input_files_verified','prior_output_files_verified',
    'acquisition_commitments_verified','boundary_rows_independently_checked','target_outcomes_verified','raw_readouts_rescored',
    'exact_rational_block_summaries','primary','target_rewrites_each_guard_and_random','closeout_audit_wall_seconds']}))
