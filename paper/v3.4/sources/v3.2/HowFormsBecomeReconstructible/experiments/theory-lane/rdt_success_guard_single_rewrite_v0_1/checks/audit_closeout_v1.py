"""Independent saved-evidence closeout. No study modules or new native dynamics."""
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path
import hashlib
import json
import math
import time
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT/'jobs/single_rewrite_v1/inputs'
RUN = ROOT/'runs/single_rewrite_v1'
DEST = ROOT/'checks/INDEPENDENT_CLOSEOUT_AUDIT.json'
EXPECTED_INPUT = 'b951cea2d453c7f90318714685f92d9cb2afdb652dcd5ff30e6c1020ef9149ca'
EXPECTED_COMPLETE = '7a94aa660dfef18322d4a52785646462891002bbabd8b32906d2ca62891fe2c7'
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
assert sha(RUN/'COMPLETE.json') == EXPECTED_COMPLETE
complete = read(RUN/'COMPLETE.json'); p = read(INPUT/'protocol.json')
assert complete['inputs_sha256'] == EXPECTED_INPUT
assert sha(RUN/'OUTPUTS.json') == complete['output_manifest_sha256']
input_count = verify_manifest(INPUT, read(INPUT/'INPUTS.json'))
output_manifest = read(RUN/'OUTPUTS.json')
output_count = verify_manifest(RUN, output_manifest)
assert input_count == 73
assert set(output_manifest['sha256']) == {
    str(q.relative_to(RUN)) for q in RUN.rglob('*') if q.is_file()
    and str(q.relative_to(RUN)) not in ['COMPLETE.json', 'OUTPUTS.json', 'STATUS.json', 'HANDOFF.json']}
assert not (RUN/'FAILED.json').exists()
for field in ['native_files_required_byte_identical', 'other_files_required_byte_identical']:
    for name, expected in read(INPUT/'COPY_RECEIPT.json')[field].items():
        assert sha(INPUT/name) == expected
panel = read(INPUT/'context/SOURCE_PANEL.json')
prior = read(INPUT/'context/previous_COHORT.json')
prior_complete = read(INPUT/'context/previous_COMPLETE.json')
prior_closeout = read(INPUT/'context/previous_SCIENTIFIC_CLOSEOUT.json')
prior_outputs = read(INPUT/'context/previous_OUTPUTS.json')
assert sha(INPUT/'context/SOURCE_PANEL.json') == complete['source_panel_sha256'] == p['source_panel_sha256']
assert sha(INPUT/'context/previous_COMPLETE.json') == panel['source_complete_sha256'] == prior_closeout['complete_sha256']
assert sha(INPUT/'context/previous_COHORT.json') == panel['source_cohort_sha256'] == prior_complete['cohort_sha256']
assert sha(INPUT/'context/previous_OUTPUTS.json') == panel['source_output_manifest_sha256'] == prior_complete['output_manifest_sha256']
assert sha(INPUT/'context/previous_INPUTS.json') == panel['source_input_manifest_sha256'] == prior_complete['inputs_sha256']
assert sha(INPUT/'context/previous_SCIENTIFIC_CLOSEOUT.json') == panel['source_closeout_sha256']
assert sha(INPUT/'context/previous_INDEPENDENT_CLOSEOUT_AUDIT.json') == prior_closeout['independent_closeout_audit_sha256']
assert p['namespace'] != read(INPUT/'context/previous_protocol.json')['namespace']
blocks = p['target_blocks']; policies = p['policies']
assert blocks == prior['blocks'] == panel['blocks'] and len(blocks) == 28
assert panel['rows'] == prior['rows'] and len(panel['rows']) == 112
assert policies == ['always_promote', 'matched_random', 'writer_success_guard', 'protected_retain', 'first_success_once']
assert p['primary']['components'] == ['24_independent_guard_minus_first_success_once']
assert p['primary']['degrees_of_freedom'] == 27 and p['primary_generations'] == list(range(16, 34))
assert sha(INPUT/'context/source_packets.npz') == panel['raw_sha256']
with np.load(INPUT/'context/source_packets.npz', allow_pickle=False) as archive:
    source_packets = archive['packets'].copy()
    assert archive['blocks'].tolist() == blocks
assert source_packets.shape == (28, 4, 2, 16, 16)
assert len(panel['original_packet_file_bindings']) == 28
for i, block in enumerate(blocks):
    source_rows = [r for r in panel['rows'] if r['block'] == block]
    assert len(source_rows) == 4
    assert [sum(r['current_pass'] == h for r in source_rows) for h in [0, 1]] == [2, 2]
    for j, row in enumerate(source_rows):
        assert hashlib.sha256(source_packets[i, j].tobytes()).hexdigest() == row['packet_sha256']
    binding = panel['original_packet_file_bindings'][i]
    assert binding['block'] == block
    assert prior_outputs['sha256'][binding['original_relative_path']] == binding['original_file_sha256']
    old_unit = str(Path(binding['original_relative_path']).parent/'COMPLETE.json')
    assert prior_outputs['sha256'][old_unit] == binding['original_unit_complete_sha256']

qualification = read(RUN/'QUALIFICATION.json'); release = read(RUN/'TARGET_RELEASE.json')
assert qualification['status'] == 'PASS' and sha(RUN/'QUALIFICATION.json') == complete['qualification_sha256']
assert release['qualification_sha256'] == complete['qualification_sha256']
assert release['policy_seal_sha256'] == sha(RUN/'development_SEAL.json') == complete['policy_seal_sha256']
assert release['fixed_blocks'] == blocks and release['source_panel_sha256'] == p['source_panel_sha256']
assert complete['wall_seconds'] < 3600 and complete['target_wall_seconds'] < 3000
assert qualification['qualification_elapsed_seconds'] < 600 and complete['capacity_wait_seconds'] == 0
assert qualification['target_forecast_seconds']+120 <= 3000
assert datetime.fromisoformat(read(INPUT/'INPUTS.json')['utc']) < datetime.fromisoformat(read(RUN/'START.json')['utc'])
assert datetime.fromisoformat(read(RUN/'development_SEAL.json')['utc']) <= datetime.fromisoformat(release['utc'])
all_rows = read(RUN/'OUTCOMES.json')
key = lambda r: (r['block'], r['regime'], tuple(r['key']), r['policy'])
by_key = {key(r): r for r in all_rows}
assert len(all_rows) == len(by_key) == 560
target_checked = set(); readouts = units = flat_chains = decisions = 0
totals = {stage: dict(guard_rewrites=0, random_rewrites=0, single_rewrites=0,
                     single_retention_after_use=0, additional_guard_rewrites=0) for stage in p['stages']}
forcing_hashes = {stage: set() for stage in p['stages']}

for stage, stage_blocks in [('qualification', p['qualification_blocks']), ('development', blocks)]:
    seal = read(RUN/(stage+'_SEAL.json'))
    assert seal['blocks'] == stage_blocks and seal['policies'] == policies
    assert seal['binding']['inputs_sha256'] == EXPECTED_INPUT
    if stage == 'development': assert seal['rows'] == panel['rows']
    for block in stage_blocks:
        folder = RUN/stage/('n24_b'+str(block)); unit = read(folder/'COMPLETE.json')
        assert unit['status'] == 'COMPLETE_AUDITED' and unit['block'] == block and unit['stage'] == stage
        assert unit['injury'] == 24 and unit['binding']['inputs_sha256'] == EXPECTED_INPUT
        assert unit['policy_seal_sha256'] == sha(RUN/(stage+'_SEAL.json'))
        assert unit['native_reads'] == unit['flat_native_reads'] == 380 and unit['outcomes'] == 20
        verify_manifest(folder, unit)
        local = read(folder/'OUTCOMES.json'); assert len(local) == 20
        if stage == 'development':
            assert all(by_key[key(r)] == r for r in local)
            assert datetime.fromisoformat(read(folder/'START.json')['utc']) >= datetime.fromisoformat(release['utc'])
        else:
            assert datetime.fromisoformat(unit['utc']) < datetime.fromisoformat(release['utc'])
        meta = read(folder/'independent.json')
        assert meta['rows'] == [r for r in seal['rows'] if r['block'] == block]
        assert sha(folder/'independent.npz') == meta['raw_sha256']
        with np.load(folder/'independent.npz', allow_pickle=False) as archive:
            raw = {name: archive[name] for name in archive.files if name != '__index__'}
        assert raw['windows'].shape == (19, 4, 32, 5, 2, 2)
        assert raw['generations'].tolist() == list(range(15, 34))
        assert np.all(raw['mask'].sum(axis=(-1, -2)) == 24)
        assert not np.array_equal(raw['birth'][:, :, 0], raw['birth'][:, :, 1])
        if stage == 'development': same(raw['initial_packets'], source_packets[blocks.index(block)])
        for name in ['incoming', 'end', 'windows', 'outgoing', 'actions', 'once_used_before', 'once_used_after', 'once_used_final']:
            same(raw[name], raw['flat_'+name])
        for j, row in enumerate(meta['rows']):
            assert hashlib.sha256(raw['initial_packets'][j].tobytes()).hexdigest() == row['packet_sha256']
            assert int(raw['histories'][j]) == row['current_pass'] and int(raw['rules'][j]) == row['rule']
            for arm, policy in enumerate(policies):
                same(raw['incoming'][0, j, arm], raw['initial_packets'][j])
                same(raw['windows'][0, j, :, arm], raw['windows'][0, j, :, 0])
                computed = []; classes = []
                for g in range(19):
                    values = [math.fsum(float(v) for v in raw['windows'][g, j, :, arm, c, port])/32
                              *row['rule']*(1 if c == port else -1) for c in (0, 1) for port in (0, 1)]
                    cls = 1 if min(values) > .25 else -1 if max(values) < -.25 else 0
                    assert cls == int(raw['classes'][g, j, arm])
                    assert (cls == 1) == bool(raw['passed'][g, j, arm])
                    assert np.allclose(np.array(values).reshape(2, 2), raw['aligned'][g, j, arm], rtol=0, atol=1e-12)
                    computed.append(int(cls == 1)); classes.append(cls); readouts += 1
                record = next(r for r in local if r['key'] == row['key'] and r['policy'] == policy and r['regime'] == 'independent')
                expected = dict(passed=computed, initial_pass=computed[0], downstream_successes=sum(computed[1:]),
                                downstream_reads=18, terminal=computed[-1], uninterrupted=int(all(computed[1:])),
                                opposite_reads=sum(c == -1 for c in classes[1:]), promotions=int(raw['actions'][:-1, j, arm].sum()),
                                first_rewrite_generation=next((15+i for i, a in enumerate(raw['actions'][:, j, arm]) if a), None))
                assert all(record[k] == v for k, v in expected.items())
                assert record['block'] == block and record['injury'] == 24 and record['history_class'] == row['current_pass']
                assert record['rule'] == row['rule']
                if stage == 'development': target_checked.add(key(record))
            first = lambda arm: next((i for i, success in enumerate(raw['passed'][:, j, arm]) if success), None)
            assert first(2) == first(3) == first(4)
        used = np.zeros(4, bool)
        for g, generation in enumerate(range(15, 34)):
            same(raw['once_used_before'][g], used)
            payload = json.dumps([p['namespace'], stage, block, 0, generation, 'promotion_subset'], separators=(',', ':')).encode()
            seed = int.from_bytes(hashlib.sha256(payload).digest()[:16], 'little')
            order = np.random.Generator(np.random.PCG64(seed)).permutation(np.arange(4, dtype=np.int64))
            same(order, raw['allocation_order'][g])
            expected = np.zeros((4, 5), bool)
            if generation < 33:
                for j in range(4):
                    expected[j, 0] = True
                    expected[j, 2] = bool(raw['passed'][g, j, 2])
                    expected[j, 4] = bool(raw['passed'][g, j, 4]) and not used[j]
                expected[order[:int(expected[:, 2].sum())], 1] = True
                totals[stage]['single_retention_after_use'] += int(used.sum())
                totals[stage]['additional_guard_rewrites'] += int((expected[:, 2] & used).sum())
                for j in range(4):
                    for arm in range(5):
                        wanted = raw['outgoing'][g, j, arm] if expected[j, arm] else raw['incoming'][g, j, arm]
                        same(raw['incoming'][g+1, j, arm], wanted)
                decisions += 1
            same(expected, raw['actions'][g])
            assert int(expected[:, 1].sum()) == int(expected[:, 2].sum()) == int(raw['quota_count'][g])
            for j in range(4):
                same(raw['incoming'][g, j, 3], raw['initial_packets'][j])
                if not used[j]:
                    same(raw['incoming'][g, j, 4], raw['initial_packets'][j])
                    same(raw['incoming'][g, j, 2], raw['initial_packets'][j])
            used = used | expected[:, 4]
            same(raw['once_used_after'][g], used)
            wanted_receipt = dict(generation=generation, block=block, order=order.tolist(),
                                  guard_promotions=int(expected[:, 2].sum()), random_promotions=int(expected[:, 1].sum()),
                                  once_promotions=int(expected[:, 4].sum()), once_used_after=used.tolist())
            assert meta['allocation'][g] == wanted_receipt
            totals[stage]['guard_rewrites'] += int(expected[:, 2].sum())
            totals[stage]['random_rewrites'] += int(expected[:, 1].sum())
            totals[stage]['single_rewrites'] += int(expected[:, 4].sum())
        same(raw['once_used_final'], used)
        same(raw['final_packets'], raw['incoming'][-1])
        assert np.all(raw['actions'][:, :, 4].sum(axis=0) <= 1)
        assert len(meta['forcing']) == 76
        for forcing, (generation, row) in zip(meta['forcing'], [(g, row) for g in range(15, 34) for row in meta['rows']]):
            assert forcing['key'] == row['key'] and forcing['generation'] == generation
            assert forcing['regime'] == 'independent' and forcing['injury'] == 24
            assert forcing['base_forcing_sha256'] not in forcing_hashes[stage]
            forcing_hashes[stage].add(forcing['base_forcing_sha256'])
        audit = read(folder/'independent_AUDIT.json')
        assert audit['status'] == 'PASS' and audit['native_readouts_independently_scored'] == audit['flat_reads'] == 380
        assert audit['full_horizon_flat_policy_chains'] == 20
        units += 1; flat_chains += 20
assert units == 32 and readouts == 12160 and flat_chains == 640 and decisions == 576
assert len(target_checked) == 560
assert not (forcing_hashes['qualification'] & forcing_hashes['development'])
assert totals['development'] == dict(guard_rewrites=1643, random_rewrites=1643, single_rewrites=98,
                                   single_retention_after_use=1573, additional_guard_rewrites=1545)

analysis = read(RUN/'ANALYSIS.json'); summaries = 0


def check_summary(record, values):
    global summaries
    assert len(values) == 28
    mean = sum(values, Fraction())/28
    variance = sum((v-mean)**2 for v in values)/27
    se = math.sqrt(float(variance/28))
    expected = dict(mean=float(mean), lower=float(mean)-p['primary']['critical_two_sided95']*se,
                    upper=float(mean)+p['primary']['critical_two_sided95']*se,
                    lower_one_sided95=float(mean)-p['primary']['critical_one_sided95']*se,
                    upper_one_sided95=float(mean)+p['primary']['critical_one_sided95']*se,
                    leave_one_block_out_min=float(min((sum(values)-v)/27 for v in values)),
                    leave_one_block_out_max=float(max((sum(values)-v)/27 for v in values)))
    assert all(abs(record[k]-v) < 1e-12 for k, v in expected.items())
    assert len(record['block_values']) == 28 and all(abs(a-float(b)) < 1e-12 for a, b in zip(record['block_values'], values))
    assert record['zero_variance'] == (variance == 0)
    summaries += 1
    return expected


overall = {}; counts = {}
for label, history in [('all', None), ('historical_fail', 0), ('historical_pass', 1)]:
    values = {}
    for policy in policies:
        for metric in ['downstream_successes', 'terminal', 'uninterrupted', 'opposite_reads', 'promotions']:
            divisor = 18 if metric in ['downstream_successes', 'opposite_reads', 'promotions'] else 1
            vs = []
            for block in blocks:
                chosen = [r for r in all_rows if r['block'] == block and r['policy'] == policy and (history is None or r['history_class'] == history)]
                assert len(chosen) == (4 if history is None else 2)
                vs.append(Fraction(sum(r[metric] for r in chosen), len(chosen)*divisor))
            check_summary(analysis['cells']['24']['independent'][label][policy][metric], vs)
            values[policy, metric] = vs
            if history is None:
                overall.setdefault(policy, {})[metric] = float(sum(vs)/28)
                counts.setdefault(policy, {})[metric] = sum(r[metric] for r in all_rows if r['policy'] == policy)
    for a in policies:
        for b in policies:
            if a == b: continue
            for metric in ['downstream_successes', 'terminal', 'uninterrupted']:
                vs = [x-y for x, y in zip(values[a, metric], values[b, metric])]
                name = a+'__minus__'+b+'__'+metric
                check_summary(analysis['contrasts']['24']['independent'][label][name], vs)
                if (label, a, b, metric) == ('all', 'writer_success_guard', 'first_success_once', 'downstream_successes'):
                    primary_values = vs
primary = check_summary(analysis['primary']['24_independent_guard_minus_first_success_once'], primary_values)
assert summaries == 256
assert primary['lower_one_sided95'] > 0
assert complete['decision'] == analysis['decision'] == 'REPEATED_REWRITE_DEVELOPMENT_SUPPORTED'
recovery = {}
for initial, label in [(0, 'shared_g15_fail'), (1, 'shared_g15_pass')]:
    cells = {}
    for policy in policies:
        chosen = [r for r in all_rows if r['policy'] == policy and r['initial_pass'] == initial]
        expected = dict(packets=len(chosen), downstream_success_count=sum(sum(r['passed'][1:]) for r in chosen),
                        downstream_read_count=18*len(chosen), terminal_count=sum(r['passed'][-1] for r in chosen),
                        uninterrupted_count=sum(all(r['passed'][1:]) for r in chosen),
                        any_g16_33_success_count=sum(any(r['passed'][1:]) for r in chosen),
                        first_success_generations=[next((15+i for i, v in enumerate(r['passed']) if v), None) for r in chosen])
        saved = analysis['recovery']['independent'][label]['cells'][policy]
        assert all(saved[k] == v for k, v in expected.items())
        cells[policy] = {k: v for k, v in expected.items() if k != 'first_success_generations'}
    contribution = []
    for block in blocks:
        chosen = [r for r in all_rows if r['block'] == block and r['initial_pass'] == initial]
        gain = sum(r['downstream_successes'] for r in chosen if r['policy'] == 'writer_success_guard')
        gain -= sum(r['downstream_successes'] for r in chosen if r['policy'] == 'first_success_once')
        contribution.append(Fraction(gain, 72))
    check_summary(analysis['recovery']['independent'][label]['guard_minus_single_rewrite_contribution'], contribution)
    recovery[label] = dict(cells=cells, whole_cohort_contribution=float(sum(contribution)/28))
assert summaries == 258
admissions = [ROOT/'jobs/single_rewrite_v1/CPU_ADMISSION.json']+sorted((RUN/'tasks').glob('*_ADMISSION.json'))
for path in admissions:
    record = read(path)
    assert record['within_limit'] and record['planned_threads'] == 5
    assert record['other_active_or_recently_busy_threads']+5 <= record['shared_limit'] == 12
waves = sorted((RUN/'tasks').glob('*_COMPLETE.json'))
assert len(waves) == 8 and len(admissions) == 9
assert all(read(path)['units'] == 4 for path in waves)
assert len(list((RUN/'tasks').glob('*_ADMISSION_attempt_*.json'))) == 8
software = read(INPUT/'SOFTWARE_QUALIFICATION.json')
assert software['status'] == 'PASS' and software['tests_passed'] == 30
result = dict(utc=datetime.now(timezone.utc).isoformat(), status='PASS', script_sha256=sha(Path(__file__)),
              input_manifest_sha256=EXPECTED_INPUT, complete_sha256=EXPECTED_COMPLETE, output_manifest_sha256=sha(RUN/'OUTPUTS.json'),
              input_files_verified=input_count, output_files_verified=output_count, source_packets_verified=112,
              complete_target_outcomes_verified=560, units_verified=32, raw_readouts_rescored=readouts,
              saved_flat_chains_verified=flat_chains, actual_decision_quota_checks=decisions,
              target_decision_quota_checks=504, policy_state_totals=totals,
              exact_policy_and_primary_block_summaries=256, exact_descriptive_recovery_contributions=2,
              primary=primary, all_policy_means=overall, all_policy_counts=counts, recovery_descriptive=recovery,
              cpu_admissions_checked=9, worker_batches_checked=8, full_native_readers_including_qualification=24320,
              software_full_readers_separate=software['full2048_step_reader_calls'],
              software_short32_readers_separate=software['short32_step_reader_calls'],
              wall_seconds=complete['wall_seconds'], target_wall_seconds=complete['target_wall_seconds'], capacity_wait_seconds=0,
              closeout_audit_wall_seconds=time.monotonic()-started, new_native_dynamics=0,
              scope='Independent saved-evidence hashes, source identities and release ordering, raw scalar endpoints, full saved flat chains, allocation RNG, persistent single-rewrite memory, all record inheritance, exact block reductions and costs. No new native dynamics or full noise forcing rerun.',
              decision=complete['decision'], development_exposed_panel=True, fresh_founder_confirmation=False, RDT_specific_validation=False)
with DEST.open('x') as stream:
    json.dump(result, stream, indent=2, allow_nan=False); stream.write('\n')
print(json.dumps({k: result[k] for k in ['status', 'input_files_verified', 'output_files_verified',
                                      'complete_target_outcomes_verified', 'raw_readouts_rescored',
                                      'saved_flat_chains_verified', 'primary', 'policy_state_totals', 'closeout_audit_wall_seconds']}))
