"""Disposable software checks; no scientific acquisition or target futures."""
from collections import Counter
from contextlib import contextmanager
from itertools import permutations
import copy
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import time
import unittest
from unittest.mock import patch
from scipy.stats import t
from sr_common import ROOT, P, POLICIES, np, bridge, fast_reader, flat, ev, read, write, sha, Deadline, byte_equal
import sr_policy
import sr_quota
import sr_forcing
import sr_source
import sr_worker
import sr_unit_audit
import sr_verification
import sr_analysis
import sr_run
import sr_acquire
import acquisition
from sr_scheduler import CapacityGate, batches

WORK = Path(os.environ['RDT_REPLICATION_TEST_DIR'])
TEST_BLOCKS = list(range(P['cohort']['eligible_blocks']))


@contextmanager
def short_reader():
    before = copy.deepcopy(P['reader']); native_before = copy.deepcopy(bridge.P['reader'])
    try:
        for cfg in (P['reader'], bridge.P['reader']):
            cfg.update(read_steps=32, settling_steps=16, observe_steps=32)
        yield
    finally:
        P['reader'].clear(); P['reader'].update(before)
        bridge.P['reader'].clear(); bridge.P['reader'].update(native_before)


def short_case():
    output = WORK / 'short_reader_case'; rows, packets = sr_source.synthetic(-2)
    for row in rows:
        row['key'][1] = 'software_only_32_steps'
    if not output.with_suffix('.json').exists():
        seal = WORK / 'short_seal.json'; write(seal, dict(rows=rows, software_only=True))
        with short_reader():
            sr_worker.evolve(rows, packets, 'qualification', 24, 'independent', output,
                             Deadline(time.time()+90), seal, sha(seal))
    return output, rows


def example_outcomes(tie=False, negative=False, initial=1):
    rows = []
    for block in TEST_BLOCKS:
        for i in range(4):
            for policy in POLICIES:
                count = dict(always_promote=8+block % 2, matched_random=9+block % 3,
                             writer_success_guard=14+block % 3, protected_retain=5+block % 2,
                             first_success_once=10+block % 2)[policy]
                if policy == 'writer_success_guard':
                    if tie: count = 10+block % 2
                    if negative: count = 3+block % 3
                y = [initial]+[1]*count+[0]*(18-count)
                promotions = 1 if policy == 'first_success_once' else 0 if policy == 'protected_retain' else 18
                first = None if policy == 'protected_retain' else 15 if policy != 'first_success_once' else 15 if initial else 16
                rows.append(dict(key=[block, 'fixture', i, 0], block=block, injury=24, regime='independent',
                                 history_class=int(i >= 2), rule=1 if i % 2 == 0 else -1, policy=policy,
                                 downstream_successes=count, downstream_reads=18, terminal=y[-1], uninterrupted=int(all(y[1:])),
                                 opposite_reads=0, promotions=promotions, initial_pass=initial, passed=y, first_rewrite_generation=first))
    return rows


def selection_fixture(block, eligible=True):
    return [dict(key=[block,'fixture',i,0],block=block,current_pass=int(i>=2) if eligible else 0,
                 rule=1 if i%2==0 else -1,selection_hash=f'{i:064x}') for i in range(4)]


def forcing_fixture():
    mask = np.zeros((19, 4, 16, 16), bool); mask.reshape(19, 4, 256)[:, :, :24] = True
    birth = np.ones((19, 4, 2, 16, 16)); birth[:, :, 1] = 2
    rows = [dict(key=[-2, 'fixture', j, 0]) for j in range(4)]
    receipts = [dict(key=row['key'], generation=g, injury=24, regime='independent',
                     base_forcing_sha256=f'{row["key"]}_{g}') for g in range(15, 34) for row in rows]
    return {(-2, 24, 'independent'): dict(mask=mask, birth=birth, forcing=receipts, rows=rows)}


class Checks(unittest.TestCase):
    def test_matched_random_ignores_other_policy_labels(self):
        y = np.zeros((4, 5), np.uint8); y[[0, 2], 2] = 1; rank = np.array([3, 1, 0, 2]); used = np.zeros(4, bool)
        a = sr_policy.actions(y, rank, used, 15); y[:, [0, 1, 3, 4]] = 1
        b = sr_policy.actions(y, rank, used, 15)
        byte_equal(a[:, :4], b[:, :4], 'non-guard labels cannot change quota control')
        self.assertEqual(a[:, 1].tolist(), [False, True, False, True])
        self.assertTrue(b[:, 4].all())

    def test_uniform_subsets_for_all_quotas(self):
        for k in range(5):
            y = np.zeros((4, 5), np.uint8); y[:k, 2] = 1; counts = Counter()
            for order in permutations(range(4)):
                a = sr_policy.actions(y, np.array(order), np.zeros(4, bool), 15)
                self.assertEqual(int(a[:, 1].sum()), k); self.assertEqual(int(a[:, 2].sum()), k)
                self.assertTrue(a[:, 0].all()); self.assertFalse(a[:, 3].any())
                counts[tuple(np.flatnonzero(a[:, 1]))] += 1
            self.assertEqual(len(set(counts.values())), 1)
            self.assertEqual(len(counts), [1, 4, 6, 4, 1][k])

    def test_single_rewrite_waits_then_never_resets(self):
        incoming = np.zeros((4, 5, 2, 16, 16)); used = np.zeros(4, bool)
        for generation in range(15, 34):
            y = np.zeros((4, 5), np.uint8)
            y[:, 4] = [generation >= 18, generation in [16, 20, 28], generation == 33, 0]
            outgoing = np.full_like(incoming, float(generation))
            incoming, a, used = sr_policy.advance(incoming, outgoing, y, np.arange(4), used, generation)
            self.assertEqual(a[:, 4].tolist(), [generation == 18, generation == 16, False, False])
            self.assertEqual(float(incoming[0, 4, 0, 0, 0]), 18. if generation >= 18 else 0.)
            self.assertEqual(float(incoming[1, 4, 0, 0, 0]), 16. if generation >= 16 else 0.)
        self.assertEqual(used.tolist(), [True, True, False, False])

    def test_single_rewrite_uses_own_success(self):
        y = np.zeros((4, 5), np.uint8); y[:, 2] = 1; y[[1, 3], 4] = 1
        a = sr_policy.actions(y, np.arange(4), np.array([False, False, False, True]), 15)
        self.assertEqual(a[:, 4].tolist(), [False, True, False, False])

    def test_terminal_success_never_consumes_memory(self):
        incoming = np.zeros((4, 5, 2, 16, 16)); used = np.array([False, True, False, True])
        after, a, next_used = sr_policy.advance(incoming, incoming+1, np.ones((4, 5)), np.arange(4), used, 33)
        self.assertFalse(a.any()); byte_equal(after, incoming, 'terminal record'); byte_equal(used, next_used, 'terminal memory')

    def test_invalid_policy_inputs_are_rejected(self):
        y = np.zeros((4, 5)); used = np.zeros(4, bool)
        for order in [np.array([0, 0, 2, 3]), np.arange(4, dtype=float), np.array([0, 1, 2, 4])]:
            with self.assertRaises(ValueError): sr_policy.actions(y, order, used, 15)
        for bad in [np.zeros((4, 4)), np.full((4, 5), 2)]:
            with self.assertRaises(ValueError): sr_policy.actions(bad, np.arange(4), used, 15)
        with self.assertRaises(ValueError): sr_policy.actions(y, np.arange(4), np.zeros(4, int), 15)
        with self.assertRaises(ValueError): sr_policy.actions(y, np.arange(4), used, 34)

    def test_no_packet_or_memory_aliasing(self):
        a = np.zeros((4, 5, 2, 16, 16)); b = np.ones_like(a); used = np.zeros(4, bool)
        after, actions, next_used = sr_policy.advance(a, b, np.ones((4, 5)), np.arange(4), used, 15)
        self.assertFalse(after[:, 3].any()); after[:] = 9; next_used[:] = False
        self.assertFalse(a.any()); self.assertTrue((b == 1).all()); self.assertFalse(used.any()); self.assertTrue(actions[:, 4].all())

    def test_strict_threshold_and_original_identity(self):
        x = np.zeros((4, 32, 5, 2, 2)); pattern = np.array([[1., -1.], [-1., 1.]])
        for arm, value in enumerate([.25, .25001, -.5, 0., -.25001]): x[:, :, arm] = value*pattern
        y, classes, _ = sr_policy.classify(x, [1, 1, -1, -1])
        self.assertEqual(y[0].tolist(), [0, 1, 0, 0, 0]); self.assertEqual(classes[0].tolist(), [0, 1, -1, 0, -1])
        self.assertEqual(y[2].tolist(), [0, 0, 1, 0, 1])
        x[0, 0, 0, 0, 0] = np.nan
        with self.assertRaises(ValueError): sr_policy.classify(x, [1]*4)

    def test_scalar_actions_cover_all_memory_and_label_patterns(self):
        order = np.array([3, 1, 0, 2])
        for bits in range(16):
            for memory in range(16):
                y = np.zeros((4, 5), np.uint8); y[:, 2] = [(bits >> j) & 1 for j in range(4)]; y[:, 4] = 1-y[:, 2]
                used = np.array([bool((memory >> j) & 1) for j in range(4)])
                classes = np.where(y, 1, -1).tolist()
                for generation in [15, 32, 33]:
                    byte_equal(sr_policy.actions(y, order, used, generation),
                               sr_unit_audit.scalar_actions(classes, order, generation, used), 'separate scalar decisions')

    def test_allocation_rng_is_independently_derived(self):
        outputs = []
        for stage in P['stages']:
            for block in [-2, 0, 29]:
                for g in [15, 16, 33]:
                    a = sr_quota.order(stage, block, g); b = sr_unit_audit.independent_order(stage, block, g)
                    byte_equal(a, b, 'allocation RNG'); outputs.append(tuple(a))
        self.assertGreater(len(set(outputs)), 5)
        with self.assertRaises(ValueError): sr_quota.order('undeclared', 0, 15)

    def test_forcing_streams_separate_stages_and_predecessor(self):
        key = [0, 'fixture', 0, 0]
        ids = [sr_forcing.seed(stage, key, g, channel) for stage in P['stages'] for g in [15, 16, 33] for channel in ['injury', 'forcing']]
        self.assertEqual(len(ids), len(set(ids)))
        current = sr_forcing.seed('qualification', key, 15, 'forcing')
        with patch.dict(P, namespace=read(ROOT/'context/previous_protocol.json')['namespace']):
            self.assertNotEqual(current, sr_forcing.seed('qualification', key, 15, 'forcing'))

    def test_forcing_injury_and_cue_independence(self):
        env, receipt = sr_forcing.environment('qualification', [-2, 'mask', 0, 0], 15, 24, 'independent')
        self.assertEqual(int(env[0].sum()), 24); self.assertFalse(np.any(env[0] & bridge.e.PORTS.any(axis=0)))
        self.assertFalse(np.array_equal(env[1][0], env[1][1])); self.assertFalse(np.array_equal(env[2][:, 0], env[2][:, 1]))
        mask, birth, hashes = sr_unit_audit.independent_environment('qualification', [-2, 'mask', 0, 0], 15, 24, 'independent')
        byte_equal(mask, env[0], 'independent injury'); byte_equal(birth, env[1], 'independent birth')
        self.assertTrue(all(receipt[k] == v for k, v in hashes.items()))
        with self.assertRaises(ValueError): sr_forcing.environment('qualification', [-2, 'mask', 0, 0], 15, 24, 'matched')

    def test_full_native_five_policy_group_and_four_policy_invariance(self):
        rows, packets = sr_source.synthetic(-2)
        envs = [sr_forcing.environment('qualification', [-2, 'software_full', j, 0], 15, 24, 'independent')[0] for j in range(4)]
        incoming = np.repeat(packets[:, None], 5, axis=1); got = fast_reader.read_batch(incoming, envs)
        old = fast_reader.read_batch(incoming[:, :4].copy(), envs)
        for name in ['end', 'windows', 'outgoing']:
            axis = 2 if name == 'windows' else 1
            byte_equal(np.take(got[name], range(4), axis=axis), old[name], 'existing four-policy dynamics unchanged')
        for j in range(4):
            reference = flat.read_write(incoming[j], *envs[j], P['reader'], 3.)
            for name in ['end', 'windows', 'outgoing']: byte_equal(got[name][j], reference[name], 'full flat five-policy group')
        y, _, _ = sr_policy.classify(got['windows'], [row['rule'] for row in rows])
        self.assertEqual(y[:, 2].tolist(), [0, 1, 1, 0])
        a = sr_policy.actions(y, np.array([0, 3, 1, 2]), np.zeros(4, bool), 15)
        byte_equal(a[:, 2], a[:, 4], 'same first successful rewrite'); self.assertFalse(np.array_equal(a[:, 1], a[:, 2]))

    def test_complete_short_chain_audit(self):
        output, rows = short_case(); receipt = read(output.with_suffix('.json'))
        with short_reader(): check = sr_unit_audit.audit_case(output, rows, 'qualification', 24, 'independent', receipt['policy_seal_sha256'])
        self.assertEqual(check['native_readouts_independently_scored'], 380); self.assertEqual(check['full_horizon_flat_policy_chains'], 20)

    def test_corrupt_saved_memory_is_detected(self):
        output, rows = short_case(); receipt = read(output.with_suffix('.json')); raw = ev.load(output.with_suffix('.npz'), receipt['raw_sha256'])
        raw['once_used_before'][3, 1] = ~raw['once_used_before'][3, 1]
        path = WORK/'broken_memory'; receipt['raw_sha256'] = ev.save(path.with_suffix('.npz'), raw); write(path.with_suffix('.json'), receipt)
        with short_reader(), self.assertRaises(ArithmeticError): sr_unit_audit.audit_case(path, rows, 'qualification', 24, 'independent', receipt['policy_seal_sha256'])

    def test_corrupt_once_action_is_detected(self):
        output, rows = short_case(); receipt = read(output.with_suffix('.json')); raw = ev.load(output.with_suffix('.npz'), receipt['raw_sha256'])
        raw['actions'][2, 0, 4] = ~raw['actions'][2, 0, 4]
        path = WORK/'broken_once_action'; receipt['raw_sha256'] = ev.save(path.with_suffix('.npz'), raw); write(path.with_suffix('.json'), receipt)
        with short_reader(), self.assertRaises(ArithmeticError): sr_unit_audit.audit_case(path, rows, 'qualification', 24, 'independent', receipt['policy_seal_sha256'])

    def test_corrupt_flat_inheritance_is_detected(self):
        output, rows = short_case(); receipt = read(output.with_suffix('.json')); raw = ev.load(output.with_suffix('.npz'), receipt['raw_sha256'])
        raw['flat_incoming'][1, 1, 4, 0, 0, 0] += .125
        path = WORK/'broken_flat'; receipt['raw_sha256'] = ev.save(path.with_suffix('.npz'), raw); write(path.with_suffix('.json'), receipt)
        with short_reader(), self.assertRaises(ArithmeticError): sr_unit_audit.audit_case(path, rows, 'qualification', 24, 'independent', receipt['policy_seal_sha256'])

    def test_terminal_raw_record_and_state_are_unchanged(self):
        output, _ = short_case(); raw = ev.load(output.with_suffix('.npz'), read(output.with_suffix('.json'))['raw_sha256'])
        self.assertFalse(raw['actions'][-1].any()); self.assertFalse(raw['flat_actions'][-1].any())
        byte_equal(raw['final_packets'], raw['incoming'][-1], 'terminal packet')
        byte_equal(raw['once_used_before'][-1], raw['once_used_after'][-1], 'terminal boolean')

    def test_primary_excludes_g15_and_keeps_terminal_separate(self):
        a = sr_analysis.summarize(example_outcomes(initial=0), TEST_BLOCKS)
        b = sr_analysis.summarize(example_outcomes(initial=1), TEST_BLOCKS)
        self.assertEqual(a['primary'], b['primary']); self.assertEqual(a['cells'], b['cells'])
        self.assertEqual(a['cells']['24']['independent']['all']['writer_success_guard']['terminal']['mean'], 0)

    def test_primary_decisions_and_independent_block_reductions(self):
        for kwargs, wanted in [({}, 'SUPPORTED'), ({'tie': True}, 'UNRESOLVED'), ({'negative': True}, 'CONTRADICTED')]:
            rows = example_outcomes(**kwargs); result = sr_analysis.summarize(rows, TEST_BLOCKS)
            self.assertEqual(result['decision'], 'REPEATED_REWRITE_REPLICATION_'+wanted)
            self.assertEqual(sr_analysis.audit_analysis(rows, result)['independent_scalar_block_summaries'], 256)
        self.assertGreater(sr_analysis.report(result, dict(native_reads=6080, flat_reads=6080), dict(units=20, native_reads=17920, flat_reads=240, teaching_episodes=40)).count('\n'), 10)

    def test_primary_is_single_rewrite_comparison_not_random(self):
        rows = example_outcomes(); result = sr_analysis.summarize(rows, TEST_BLOCKS)
        for row in rows:
            if row['policy'] == 'matched_random':
                row['passed'] = [row['initial_pass']]+[1]*18; row.update(downstream_successes=18, terminal=1, uninterrupted=1)
        self.assertEqual(result['primary'], sr_analysis.summarize(rows, TEST_BLOCKS)['primary'])

    def test_recovery_is_descriptive_and_requires_structural_identity(self):
        rows = example_outcomes(initial=0); result = sr_analysis.summarize(rows, TEST_BLOCKS)
        self.assertEqual(sr_analysis.audit_recovery(rows, result)['recovery_cells'], 10)
        bad = copy.deepcopy(rows); row = next(row for row in bad if row['policy'] == 'first_success_once')
        row['passed'][1] = 0
        with self.assertRaises(ArithmeticError): sr_analysis.summarize(bad, TEST_BLOCKS)

    def test_analysis_rejects_incomplete_data_and_false_once_count(self):
        with self.assertRaises(ValueError): sr_analysis.summarize(example_outcomes()[:-1], TEST_BLOCKS)
        rows = example_outcomes(); next(row for row in rows if row['policy'] == 'first_success_once')['promotions'] = 2
        with self.assertRaises(ArithmeticError): sr_analysis.summarize(rows, TEST_BLOCKS)

    def test_stage_forcing_coverage_and_duplicate_detection(self):
        self.assertEqual(len(sr_verification.verify_forcing_pairs(forcing_fixture(), [-2])), 76)
        for kind in ['missing', 'duplicate', 'cuecopy', 'injury']:
            cases = forcing_fixture(); case = cases[-2, 24, 'independent']
            if kind == 'missing': case['forcing'].pop()
            if kind == 'duplicate': case['forcing'][1]['base_forcing_sha256'] = case['forcing'][0]['base_forcing_sha256']
            if kind == 'cuecopy': case['birth'][:, :, 1] = case['birth'][:, :, 0]
            if kind == 'injury': case['mask'][0, 0] = False
            with self.subTest(kind=kind), self.assertRaises(ArithmeticError): sr_verification.verify_forcing_pairs(cases, [-2])

    def test_fixed_sample_costs_and_timing_rejection(self):
        self.assertEqual(P['cohort']['eligible_blocks'], 16)
        self.assertEqual(P['cohort']['maximum_attempts'], 20)
        self.assertEqual(P['counts']['total_full_native_reads_cap'], 20*908+16*760+2*908+2*760)
        self.assertEqual(P['counts']['total_full_native_reads_minimum'], 16*908+16*760+2*908+2*760)
        self.assertEqual(P['counts']['target_outcomes'], 16*4*5)
        self.assertEqual(P['resource']['combined_seconds'], 3600)
        self.assertAlmostEqual(P['primary']['critical_two_sided95'], t.ppf(.975, 15))
        self.assertAlmostEqual(P['primary']['critical_one_sided95'], t.ppf(.95, 15))
        self.assertEqual(sr_run.timing_gate(0, 0, 100)['status'], 'PASS')
        self.assertEqual(sr_run.timing_gate(0, 400, 100)['status'], 'FAILED')
        self.assertEqual(sr_run.timing_gate(400, 0, 100)['status'], 'FAILED')
        self.assertEqual(sr_run.timing_gate(0, 0, 601)['status'], 'FAILED')
        self.assertEqual(sha(ROOT/'context/PRICING.json'), P['source_pricing_sha256'])
        self.assertEqual([len(x) for x in batches(TEST_BLOCKS)], [4]*4)
        self.assertEqual(len(P['qualification_blocks'])+len(P['qualification_acquisition_blocks'])+1, 4)

    def test_actual_qualification_time_reduces_available_target_budget(self):
        early = sr_run.timing_gate(0, 0, 100)
        later = sr_run.timing_gate(0, 0, 300)
        too_late = sr_run.timing_gate(0, 0, 400)
        self.assertEqual(early['available_target_seconds'], 3400)
        self.assertEqual(later['available_target_seconds'], 3300)
        self.assertEqual(too_late['available_target_seconds'], 3200)
        self.assertEqual(later['status'], 'PASS')
        self.assertEqual(too_late['status'], 'FAILED')
        for elapsed in [1, 100, 200, 300, 400, 599]:
            gate = sr_run.timing_gate(0, 0, elapsed)
            self.assertLessEqual(gate['available_target_seconds']+elapsed, 3600)
        expected = 180+1.5*(5*P['resource']['historical_acquisition_floor']+4*P['resource']['historical_continuation_floor'])+180
        self.assertAlmostEqual(early['target_forecast_seconds'], expected)

    def test_cpu_wait_budget_is_cumulative_and_deadline_bounded(self):
        clock = [0.]
        def sleep(delay): clock[0] += delay
        answers = iter([8, 8, 1])
        gate = CapacityGate(200., clock=lambda: clock[0], sleep=sleep)
        with patch.dict(P['resource'], capacity_wait_seconds=60):
            gate.admit(WORK/'capacity_first.json', lambda: dict(other_active_or_recently_busy_threads=next(answers)))
            self.assertEqual(gate.wait_seconds, 60.)
            with self.assertRaises(RuntimeError): gate.admit(WORK/'capacity_second.json', lambda: dict(other_active_or_recently_busy_threads=8))
        late = CapacityGate(10., clock=lambda: 9., sleep=lambda x: self.fail('Must not sleep past deadline'))
        with self.assertRaises(RuntimeError): late.admit(WORK/'capacity_deadline.json', lambda: dict(other_active_or_recently_busy_threads=8))

    def test_native_equations_and_stream_code_remain_byte_identical(self):
        receipt = read(ROOT/'COPY_RECEIPT.json')
        for field in ['native_files_required_byte_identical', 'other_files_required_byte_identical']:
            for rel, expected in receipt[field].items(): self.assertEqual(sha(ROOT/rel), expected, rel)
        self.assertEqual(bridge.verify_inputs(), len(read(ROOT/'native/INPUTS.json')['sha256']))
        prefix = (ROOT/'sr_worker.py').read_text().split('def execute(task):')[0]
        self.assertEqual(hashlib.sha256(prefix.encode()).hexdigest(), receipt['required_worker_evolve_prefix_sha256'])

    def test_worker_failure_is_durable_without_target_outcome(self):
        output = WORK/'expected_failure'; task = WORK/'invalid_task.json'
        write(task, dict(output=str(output), deadline=time.time()+20, parent_pid=-1))
        with (WORK/'expected_failure.log').open('xb') as log:
            child = subprocess.run([sys.executable, str(ROOT/'sr_worker.py'), str(task)], stdout=log, stderr=subprocess.STDOUT,
                                   stdin=subprocess.DEVNULL, timeout=25)
        self.assertNotEqual(child.returncode, 0); self.assertTrue((output/'FAILED.json').exists())
        self.assertFalse((output/'COMPLETE.json').exists())


    def test_archived_boundary_labels_and_selector(self):
        raw = ev.load(ROOT/'native/context/legacy_g14.npz', sha(ROOT/'native/context/legacy_g14.npz'))
        rows = acquisition.boundary_records(P['legacy_block'], raw)
        sr_acquire.check_rows(rows, P['legacy_block'])
        chosen = sr_source.select_block(rows)
        self.assertEqual(len(rows), 64)
        self.assertEqual([sum(r['current_pass']==h for r in chosen) for h in [0,1]], [2,2])

    def test_only_acquisition_and_selection_namespaces_change(self):
        before = copy.deepcopy(bridge.P)
        try:
            namespaces = sr_acquire.configure('scientific')
            altered = copy.deepcopy(bridge.P)
            self.assertIn(P['namespace'], namespaces['acquisition'])
            for section in ['acquisition','selection']:
                altered[section]['namespace'] = sr_acquire.ORIGINAL[section]['namespace']
            self.assertEqual(altered, sr_acquire.ORIGINAL)
        finally:
            bridge.P.clear(); bridge.P.update(before)

    def test_fresh_acquisition_streams_differ_from_legacy_qualification_and_predecessor(self):
        before = copy.deepcopy(bridge.P)
        try:
            sr_acquire.configure('scientific')
            scientific = acquisition.stream('scientific','E016',0,'teach',0).standard_normal(16)
            legacy = acquisition.stream('scientific','E016',0,'teach',0,legacy=True).standard_normal(16)
            sr_acquire.configure('qualification')
            qualification = acquisition.stream('qualification','E016',0,'teach',0).standard_normal(16)
            prior_namespace = read(ROOT/'context/acquisition_source_protocol.json')['namespace']
            with patch.dict(P, namespace=prior_namespace):
                sr_acquire.configure('scientific')
                previous = acquisition.stream('scientific','E016',0,'teach',0).standard_normal(16)
            for comparator in [legacy, qualification, previous]:
                self.assertFalse(np.array_equal(scientific, comparator))
        finally:
            bridge.P.clear(); bridge.P.update(before)

    def test_boundary_selector_preserves_class_rule_and_order(self):
        rows = selection_fixture(0)
        chosen = sr_source.select_block(rows)
        self.assertEqual([(r['current_pass'], r['rule']) for r in chosen], [(0,-1),(0,1),(1,-1),(1,1)])
        self.assertEqual(sr_source.select_block(list(reversed(rows))), chosen)
        self.assertEqual(sr_source.select_block(selection_fixture(0, False)), [])
        one_rule = copy.deepcopy(rows)
        for row in one_rule: row['rule']=1
        self.assertEqual(len(sr_source.select_block(one_rule)), 4)

    def test_first_eligible_panel_retains_rejections_and_surplus(self):
        attempts = {b:selection_fixture(b, b not in [0,3]) for b in range(20)}
        panel = sr_source.select_panel(attempts)
        self.assertEqual(panel['blocks'], [b for b in range(18) if b not in [0,3]])
        self.assertEqual(panel['ineligible_blocks'], [0,3])
        self.assertEqual(panel['surplus_blocks'], [18,19])
        self.assertEqual(sr_source.verify_selection(attempts, panel)['status'], 'PASS')
        changed = copy.deepcopy(panel); changed['blocks'][-1]=19
        with self.assertRaises(ArithmeticError): sr_source.verify_selection(attempts, changed)

    def test_incomplete_nonprefix_and_overcap_waves_are_rejected(self):
        for ids in [list(range(5)), list(range(21)), list(range(1,5))]:
            with self.subTest(ids=ids), self.assertRaises(ValueError):
                sr_source.select_panel({b:selection_fixture(b) for b in ids})
        panel = sr_source.select_panel({b:selection_fixture(b, b>5) for b in range(20)})
        self.assertFalse(panel['complete'])
        self.assertEqual(sr_source.verify_selection({b:selection_fixture(b, b>5) for b in range(20)}, panel)['status'], 'PASS')

    def test_incomplete_cohort_cannot_seal_or_release_futures(self):
        run = WORK/'incomplete_cohort'; run.mkdir()
        with patch.object(sr_source.sr_acquire, 'verify', side_effect=lambda folder,stage,b:(selection_fixture(b),{})), patch.object(sr_source,'sha',return_value='fixture'):
            with self.assertRaises(ValueError): sr_source.seal_panel(run, list(range(4)))
        self.assertFalse((run/'COHORT.json').exists()); self.assertFalse((run/'scientific').exists())
        with self.assertRaises(FileNotFoundError): sr_source.load('scientific',0,run)

    def test_no_source_seal_after_scientific_futures(self):
        run = WORK/'future_before_source'; (run/'scientific').mkdir(parents=True)
        with self.assertRaises(ValueError): sr_source.seal_panel(run, list(range(16)))
        self.assertFalse((run/'COHORT.json').exists())

    def test_complete_boundary_seal_and_packet_loading(self):
        run = WORK/'mock_boundary'; run.mkdir()
        raw = ev.load(ROOT/'native/context/legacy_g14.npz', sha(ROOT/'native/context/legacy_g14.npz'))
        rows = acquisition.boundary_records(0,raw); selected = sr_source.select_block(rows)
        folder = run/'acquisition/b0'; folder.mkdir(parents=True)
        raw_hash = ev.save(folder/'boundary.npz', raw)
        write(folder/'COMMIT.json', {'sha256':{'boundary.npz':raw_hash}})
        fake_binding = {'fixture':'test_only'}
        write(run/'COHORT.json', dict(complete=True,binding=fake_binding,blocks=[0],rows=selected,
                                     acquisitions=[dict(block=0,path='acquisition/b0',commit_sha256=sha(folder/'COMMIT.json'))]))
        with patch.object(sr_source,'binding',return_value=fake_binding), patch.object(sr_source.sr_acquire,'verify',return_value=(rows,{})):
            chosen,packets = sr_source.load('scientific',0,run)
            self.assertEqual(chosen,selected); self.assertEqual(packets.shape,(4,2,16,16))
            for j,row in enumerate(chosen):
                self.assertEqual(hashlib.sha256(packets[j].tobytes()).hexdigest(),row['packet_sha256'])
            with self.assertRaises(ValueError): sr_source.load('scientific',1,run)


if __name__ == '__main__':
    unittest.main()
