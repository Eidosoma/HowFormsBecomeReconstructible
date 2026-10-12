"""Scientific checks for paid evidence, temporal information and adaptive alarms."""
from itertools import product
from math import exp, fsum, log
from pathlib import Path
import unittest
from unittest.mock import patch

from fep_model_learning.exact import solve as solve_v3
from fep_active_checking.exact import (
    ACTIONS, ALPHAS, CLOSED, EXTENDED, MODEL_TRUTHS, TARGETS, TRUTHS, Engine,
    bayesian_reference, evaluate, information_reference, path_trace,
    physical_paths, preference_constant, world_information_reference,
)


class ActiveCheckingTests(unittest.TestCase):
    def test_physical_paths_and_preferences_normalize(self):
        for h, truth in product((1, 2, 3, 4), TRUTHS):
            self.assertAlmostEqual(fsum(physical_paths(truth, h).values()), 1)
        for beta, c, d in ((1, .05, .02), (4, .2, .1), (16, .2, .3)):
            total = fsum(exp(beta*(g-c*k-d*a)-preference_constant(1, beta, c, d))
                         for g, k, a in product((0, 1), repeat=3))
            self.assertAlmostEqual(total, 1)

    def test_no_purchase_reveals_no_hidden_reward_or_mapping(self):
        e = Engine(EXTENDED, 3)
        tree = e.baseline('no_measurements')
        traces = {path_trace(s, tree)[0] for s in e.prior_paths()}
        self.assertEqual(traces, {((2, 2, 0, 0),)*3})
        for target in TARGETS:
            self.assertAlmostEqual(e.entropies(e.root)[target], e.entropies(tree.children[2, 2].mask)[target])

    def test_audit_occurs_after_report_and_cannot_improve_that_report(self):
        e = Engine(EXTENDED, 1)
        for target in TARGETS:
            s = e.solve(1, .05, .02, target)
            self.assertAlmostEqual(evaluate(e.prior_paths(), s.node, .05, .02)['expected_correct'], .5)

    def test_terminal_audit_distinguishes_task_efe_from_bayesian_control(self):
        e = Engine(EXTENDED, 1)
        for offset in (-1e-6, 0, 1e-6):
            d = log(2)/4+offset
            task = e.solve(4, 10, d, 'task')
            scored = evaluate(e.prior_paths(), task.node, 10, d)
            self.assertEqual(task.node.action.audit0, offset < 0)
            self.assertAlmostEqual(scored['expected_audits'], float(offset < 0), places=12)
            bayes = e.solve(4, 10, d, 'none')
            self.assertEqual(evaluate(e.prior_paths(), bayes.node, 10, d)['expected_audits'], 0)

    def test_bayesian_final_audit_is_always_absent(self):
        for prior in (CLOSED, EXTENDED):
            e = Engine(prior, 3)
            s = e.solve(4, .05, .02, 'none')
            self.assertAlmostEqual(evaluate(e.prior_paths(), s.node, .05, .02)['audits_by_round'][-1], 0)

    def test_no_audit_preserves_global_mapping_ambiguity(self):
        e = Engine(EXTENDED, 3)
        for schedule in product((ACTIONS[0], ACTIONS[2]), repeat=3):
            solution = e.solve(4, .05, .1, 'none', schedule=schedule)
            for truth in TRUTHS:
                self.assertAlmostEqual(evaluate(physical_paths(truth, 3), solution.node, .05, .1)['expected_correct'], 1.5)

    def test_mask_filter_order_does_not_change_posterior(self):
        e = Engine(EXTENDED, 3)
        a = e.filter_mask(e.filter_mask(e.root, 0, (0, 1)), 2, (1, 2))
        b = e.filter_mask(e.filter_mask(e.root, 2, (1, 2)), 0, (0, 1))
        self.assertEqual(a, b)
        self.assertEqual(e.entropies(a), e.entropies(b))

    def test_complete_world_information_matches_joint_trajectory_accounting(self):
        e = Engine(EXTENDED, 3)
        for target in TARGETS:
            s = e.solve(4, .05, .1, target)
            compact = information_reference(e, s.node)
            direct = world_information_reference(e, s.node)
            self.assertAlmostEqual(s.information, compact[target])
            for name in ('all', 'model', 'task'):
                self.assertAlmostEqual(compact[name], direct[name])
            self.assertEqual(direct, world_information_reference(e, s.node, y1=1))

    def test_later_audit_can_reveal_earlier_world_states(self):
        e = Engine((0, 0, 0, 1), 3)
        no = e.solve(4, .1, .1, 'none', schedule=(ACTIONS[0],)*3)
        late = e.solve(4, .1, .1, 'none', schedule=(ACTIONS[0], ACTIONS[0], ACTIONS[1]))
        self.assertAlmostEqual(information_reference(e, no.node)['task'], 2*log(2))
        self.assertAlmostEqual(information_reference(e, late.node)['task'], 3*log(2))
        self.assertLess(late.utility, no.utility)

    def test_compulsory_free_audits_reduce_to_v3(self):
        e = Engine(CLOSED, 3)
        for target in ('all', 'model', 'task', 'none'):
            new = e.solve(4, .1, 0, target, force_audits=True)
            old = solve_v3(CLOSED[:3], 3, 4, .1, target)
            self.assertAlmostEqual(new.utility, old.utility)
            self.assertAlmostEqual(new.information, old.information)

    def test_independent_bayesian_reference_and_fixed_schedule_bound(self):
        for prior in (CLOSED, EXTENDED):
            e = Engine(prior, 3)
            dynamic = e.solve(4, .05, .1, 'none')
            self.assertAlmostEqual(dynamic.utility, bayesian_reference(prior, 3, .05, .1))
            fixed, node = e.best_fixed(.05, .1)
            self.assertGreaterEqual(dynamic.utility+1e-12, fixed['utility'])
            self.assertAlmostEqual(evaluate(e.prior_paths(), node, .05, .1)['utility'], fixed['utility'])

    def test_closed_family_target_is_a_constant(self):
        e = Engine(CLOSED, 3)
        family = e.solve(4, .05, .1, 'family')
        bayes = e.solve(4, .05, .1, 'none')
        self.assertAlmostEqual(family.information, 0)
        self.assertAlmostEqual(family.utility, bayes.utility)

    def test_one_audit_memory_control_pays_for_its_acquisition(self):
        e = Engine(EXTENDED, 3)
        for truth in MODEL_TRUTHS:
            r = evaluate(physical_paths(truth, 3), e.baseline('one_audit_memory'), .05, .1)
            self.assertEqual(r['expected_audits'], 1)
            self.assertAlmostEqual(r['utility'], 2.4 if truth == MODEL_TRUTHS[3] else 1.4)

    def test_adaptive_alarm_calibration_and_finite_information_bound(self):
        e = Engine(EXTENDED, 3)
        for target in TARGETS:
            s = e.solve(1, .05, .02, target)
            for truth in MODEL_TRUTHS[:3]:
                r = evaluate(physical_paths(truth, 3), s.node, .05, .02, e)
                for alpha in ALPHAS:
                    self.assertLessEqual(r['alarm_probability'][str(alpha)], alpha+1e-12)
                self.assertLessEqual(r['maximum_family_ratio'], 4+1e-12)
                self.assertEqual(r['alarm_probability']['0.05'], 0)

    def test_late_alarm_is_not_a_timely_warning(self):
        e = Engine(EXTENDED, 3)
        tree = e.solve(1, .05, .02, 'none', schedule=(ACTIONS[1],)*3).node
        r = evaluate(physical_paths(MODEL_TRUTHS[3], 3), tree, .05, .02, e)
        self.assertEqual(r['alarm_probability']['0.25'], 1)
        self.assertEqual(r['timely_alarm_probability']['0.25'], 0)

    def test_unannounced_break_has_no_pre_report_warning(self):
        e = Engine(EXTENDED, 3)
        tree = e.solve(4, .05, .02, 'all').node
        visible = []
        for truth in (TRUTHS[0], TRUTHS[-1]):
            distribution = {}
            for state, p in physical_paths(truth, 3).items():
                trace = path_trace(state, tree)[0]
                before_last_report = trace[:-1]+((trace[-1][0],),)
                distribution[before_last_report] = distribution.get(before_last_report, 0)+p
            visible.append(distribution)
        self.assertEqual(visible[0], visible[1])

    def test_storage_guard_refuses_local_fallback(self):
        from fep_active_checking.verify import checked_destination
        with patch('fep_active_checking.verify.os.path.ismount', return_value=False):
            with self.assertRaises(RuntimeError):
                checked_destination(Path('/mnt/bioIce1/fep-ideas/never-created'))
        with patch('fep_active_checking.verify.os.path.ismount', return_value=True):
            with self.assertRaises(ValueError):
                checked_destination(Path('/tmp/no-fep-v5-data'))


if __name__ == '__main__':
    unittest.main()
