"""Calibration, observable-history causality, objective and physical-path checks."""
from itertools import product
from math import exp, fsum, log
from pathlib import Path
import unittest
from unittest.mock import patch

from fep_model_learning.exact import (initial_belief as old_belief, solve as old_solve,
                                      mutual_information, preference_constant)
from fep_model_checking.exact import (
    CLOSED, EXTENDED, INDEX, MODELS, MODEL_TRUTHS, NULLS, PERSISTENT, POLICIES,
    STATES, TARGETS, TRUTHS, Choice, History, Truth, bayesian_reference, branches,
    choose, class_joint, class_marginal, class_posterior, copy_last, crossing_length,
    gate, histories, history_probability, kernel, monitor, normalize,
    physical_history_joint, physical_score, posterior_evidence, prediction,
    score, terminal_distribution, vfe,
)


class ModelCheckingTests(unittest.TestCase):
    def assertVector(self, a, b):
        self.assertEqual(len(a), len(b))
        for x, y in zip(a, b):
            self.assertAlmostEqual(x, y)

    def test_history_probability_normalizes_under_every_truth(self):
        for truth, n in product(TRUTHS, (1, 3, 5, 7)):
            self.assertAlmostEqual(fsum(history_probability(truth, h) for h in histories(n)), 1)

    def test_analytic_history_and_endpoint_match_physical_transitions(self):
        for truth, n in product(TRUTHS, (1, 3, 5)):
            physical = physical_history_joint(truth, n)
            for h in histories(n):
                group = physical.get(h, {})
                mass = fsum(group.values())
                self.assertAlmostEqual(mass, history_probability(truth, h))
                if mass:
                    predicted = terminal_distribution(truth, h)
                    for state in product((0, 1), repeat=2):
                        self.assertAlmostEqual(group.get(state, 0)/mass, predicted.get(state, 0))

    def test_class_posterior_and_prediction_match_mixture_paths(self):
        for prior in (CLOSED, EXTENDED):
            for h in histories(3):
                direct = [0.0]*16
                for m, truth in enumerate(MODEL_TRUTHS):
                    for (r, a), weight in physical_history_joint(truth, 3).get(h, {}).items():
                        direct[INDEX[m, r, a]] = prior[m]*weight
                self.assertVector(prediction(prior, h), normalize(direct))

    def test_posterior_average_recovers_both_supplied_priors(self):
        for prior in (CLOSED, EXTENDED):
            average = [0.0]*4
            for h in histories(5):
                joint = class_joint(prior, h)
                post = class_posterior(prior, h)
                for m in range(4):
                    average[m] += fsum(joint)*post[m]
            self.assertVector(average, prior)

    def test_full_null_family_never_has_zero_evidence(self):
        for h in histories(7):
            self.assertGreater(fsum(class_joint(CLOSED, h)), 0)

    def test_certain_class_posterior_can_coexist_with_adequacy_alarm(self):
        h = History((0,)*5, 1)
        self.assertVector(class_posterior(CLOSED, h), (0, 1, 0, 0))
        self.assertTrue(monitor(h, .05)['alarm'])
        self.assertEqual(monitor(h, .05)['terminal_value'], 32)

    def test_equal_null_evidence_and_vfe_need_not_mean_equal_monitor(self):
        constant = History((0, 0, 0, 0, 0), 1)
        varying = History((0, 1, 0, 0, 0), 1)
        a, b = (posterior_evidence(CLOSED, h) for h in (constant, varying))
        self.assertEqual(a, b)
        self.assertAlmostEqual(a['exact_vfe'], log(192))
        self.assertTrue(monitor(constant, .05)['alarm'])
        self.assertFalse(monitor(varying, .05)['alarm'])

    def test_exact_and_approximate_vfe_evidence_identity(self):
        h = History((0, 0, 0), 0)
        joint = class_joint(EXTENDED, h)
        exact = normalize(joint)
        trial = (.25,)*4
        divergence = fsum(q*log(q/p) for q, p in zip(trial, exact))
        self.assertAlmostEqual(vfe(exact, joint), -log(fsum(joint)))
        self.assertAlmostEqual(vfe(trial, joint), divergence-log(fsum(joint)))

    def test_monitor_false_alarms_are_calibrated_under_each_null(self):
        for truth, n, alpha in product(NULLS, (1, 3, 5, 7), (.05, .125, .25)):
            actual = fsum(history_probability(truth, h)*monitor(h, alpha)['alarm'] for h in histories(n))
            k = crossing_length(alpha)
            self.assertAlmostEqual(actual, 0 if n < k else 2**(-k))
            self.assertLessEqual(actual, alpha+1e-12)

    def test_monitor_has_unit_expectation_under_each_null(self):
        for truth, n in product(NULLS, (1, 3, 5, 7)):
            expected = fsum(history_probability(truth, h)*monitor(h, .05)['terminal_value'] for h in histories(n))
            self.assertAlmostEqual(expected, 1)

    def test_stopped_monitor_also_has_unit_expectation(self):
        for truth in NULLS:
            value = 0.0
            for h in histories(7):
                m = monitor(h, .05)
                stopped = m['trace'][m['first_crossing']] if m['alarm'] else m['terminal_value']
                value += history_probability(truth, h)*stopped
            self.assertAlmostEqual(value, 1)

    def test_crossing_is_latched_even_when_terminal_value_is_zero(self):
        h = History((0, 0, 0, 0, 0, 1, 0), 0)
        result = monitor(h, .05)
        self.assertTrue(result['alarm'])
        self.assertEqual(result['first_crossing'], 5)
        self.assertEqual(result['terminal_value'], 0)

    def test_early_change_kills_this_no_reset_monitor(self):
        h = History((1, 0, 0, 0, 0, 0, 0), 0)
        self.assertFalse(monitor(h, .05)['alarm'])
        self.assertEqual(monitor(h, .05)['terminal_value'], 0)

    def test_power_matches_declared_alternative_and_misspecification(self):
        for truth in TRUTHS[3:7]:
            actual = fsum(history_probability(truth, h)*monitor(h, .05)['alarm'] for h in histories(7))
            self.assertAlmostEqual(actual, (1-truth.rho)**5)

    def test_hidden_future_break_has_identical_observable_histories(self):
        for h in histories(5):
            self.assertEqual(history_probability(NULLS[0], h), history_probability(TRUTHS[-1], h))
        h = History((1, 0, 0, 0, 0), 0)
        self.assertNotEqual(terminal_distribution(NULLS[0], h), terminal_distribution(TRUTHS[-1], h))

    def test_targeted_information_and_direct_efe_identity(self):
        for prior, h, policy in product((CLOSED, EXTENDED), histories(3), POLICIES):
            q = prediction(prior, h)
            s = score(q, policy, 4, .1)
            self.assertAlmostEqual(s['efe']['all'], s['efe_direct_all'])
            self.assertGreaterEqual(s['information']['model'], -1e-12)
            self.assertAlmostEqual(s['information']['task'], score(q, POLICIES[0], 4, .1)['information']['task'])

    def test_preference_density_normalizes_on_the_common_alphabet(self):
        for beta, cost in product((1, 4, 16), (.05, .1, .25)):
            total = fsum(exp(beta*(g-cost*k)-preference_constant(1, beta, cost))
                         for z, g, k in product((0, 1, 2), (0, 1), (0, 1)))
            self.assertAlmostEqual(total, 1)

    def test_information_targets_match_joint_definition(self):
        for prior, h, policy in product((CLOSED, EXTENDED), histories(3), POLICIES):
            q = prediction(prior, h)
            joint = {}
            for state, p in zip(STATES, q):
                if p:
                    m, r, a = state
                    z = r ^ a if policy.probe else 2
                    joint[state, (z, int(policy.guess(z) == r))] = p
            scored = score(q, policy, 4, .1)
            for target in ('all', 'model', 'task'):
                self.assertAlmostEqual(scored['information'][target], mutual_information(joint, target))

    def test_task_efe_matches_independent_bayesian_choice(self):
        for prior, h in product((CLOSED, EXTENDED), histories(3)):
            q = prediction(prior, h)
            reference = bayesian_reference(q, .1)
            for target in ('task', 'none'):
                c = choose(q, 4, .1, target)
                actual = fsum(score(q, p, 4, .1)['utility'] for p in c.policies)/len(c.policies)
                self.assertAlmostEqual(actual, reference)

    def test_randomized_ties_do_not_credit_the_agents_own_randomness(self):
        h = History((0, 0, 0), 1)
        q = prediction(CLOSED, h)
        choice = choose(q, 4, .1, 'none')
        self.assertEqual(len(choice.policies), 2)
        self.assertFalse(choice.probe)
        for p in choice.policies:
            self.assertAlmostEqual(score(q, p, 4, .1)['information']['all'], log(2))
        # Averaging report choices keeps the wrong model at chance under either initial bit.
        for origin in product((0, 1), repeat=2):
            q = prediction(CLOSED, h, origin)
            self.assertAlmostEqual(physical_score(terminal_distribution(PERSISTENT, h, origin), choose(q, 4, .1, 'none'), .1)['accuracy'], .5)

    def test_full_efe_pays_for_useless_probe_under_known_volatile(self):
        h = History((0,)*5, 1)
        q = prediction(CLOSED, h)
        full = choose(q, 4, .1, 'all')
        bayes = choose(q, 4, .1, 'none')
        self.assertTrue(full.probe)
        self.assertFalse(bayes.probe)
        true = terminal_distribution(PERSISTENT, h)
        self.assertAlmostEqual(physical_score(true, full, .1)['utility'], .4)
        self.assertAlmostEqual(physical_score(true, bayes, .1)['utility'], .5)
        self.assertAlmostEqual(physical_score(true, gate(full, h, .05), .1)['utility'], 1)

    def test_extended_family_uses_persistence_before_alarm(self):
        h = History((0,), 1)
        self.assertFalse(monitor(h, .05)['alarm'])
        posterior = class_posterior(EXTENDED, h)
        self.assertGreater(posterior[3], .1)
        c = choose(prediction(EXTENDED, h), 4, .1, 'none')
        self.assertAlmostEqual(physical_score(terminal_distribution(PERSISTENT, h), c, .1)['accuracy'], 1)

    def test_feedback_is_used_only_after_a_past_report(self):
        h = History((0,), 1)
        distribution = terminal_distribution(NULLS[1], h)
        for prior, target in product((CLOSED, EXTENDED), TARGETS):
            result = physical_score(distribution, choose(prediction(prior, h), 4, .1, target), .1)
            self.assertAlmostEqual(result['accuracy'], .5)

    def test_memory_fallback_is_a_supplied_rule_with_a_blind_spot(self):
        h = History((0,)*5, 1)
        for truth in TRUTHS[3:7]:
            actual = physical_score(terminal_distribution(truth, h), copy_last(h), .1)
            self.assertAlmostEqual(actual['accuracy'], 1-truth.rho)
        self.assertAlmostEqual(physical_score(terminal_distribution(TRUTHS[6], h), copy_last(h), .1)['utility'], .25)

    def test_bit_relabeling_preserves_all_endpoint_scores(self):
        for h, target, prior in product((History((0, 0, 0), 0), History((1, 0, 1), 0)), TARGETS, (CLOSED, EXTENDED)):
            for truth in TRUTHS:
                if not history_probability(truth, h):
                    continue
                values = []
                for origin in product((0, 1), repeat=2):
                    choice = choose(prediction(prior, h, origin), 4, .1, target)
                    values.append(physical_score(terminal_distribution(truth, h, origin), choice, .1)['utility'])
                self.assertVector(values, [values[0]]*4)

    def test_known_volatile_last_decision_reduces_to_v3(self):
        h = History((0,)*3, 1)
        for target in TARGETS:
            # V3 had no separate adequacy target; its class index is already certain.
            previous = old_solve((0, 1, 0), 1, 4, .1, target, belief=old_belief((0, 1, 0)))
            choice = choose(prediction(CLOSED, h), 4, .1, target)
            result = physical_score(terminal_distribution(NULLS[1], h), choice, .1)
            self.assertEqual(choice.probe, previous.node.policy.probe)
            self.assertAlmostEqual(result['utility'], previous.utility)

    def test_common_audit_probe_cost_is_counted(self):
        h = History((0,)*5, 1)
        result = physical_score(terminal_distribution(PERSISTENT, h), copy_last(h), .1)
        self.assertAlmostEqual(result['utility'], 1)
        self.assertAlmostEqual(result['utility_including_audit_probes'], .8)

    def test_output_guard_rejects_missing_mount_and_local_fallback(self):
        from fep_model_checking.verify import checked_destination
        with patch('fep_model_checking.verify.os.path.ismount', return_value=False):
            with self.assertRaises(RuntimeError):
                checked_destination(Path('/mnt/bioIce1/fep-ideas/test-never-created'))
        with patch('fep_model_checking.verify.os.path.ismount', return_value=True):
            with self.assertRaises(ValueError):
                checked_destination(Path('/tmp/fep-v4-no-local-data'))


if __name__ == '__main__':
    unittest.main()
