"""Independent probability, causal-history and objective checks for model learning."""
from itertools import product
from math import exp, fsum, log
from pathlib import Path
import unittest
from unittest.mock import patch

from fep_model_learning.exact import (
    INDEX, KERNELS, MODELS, NULL, POLICIES, STATES, Policy, best_fixed_schedule,
    entropy, evaluate, initial_belief, model_marginal, normalize,
    observable_trajectory, path_observation, posterior_from_transition,
    preference_constant, round_branches, solve, trajectories,
    trajectory_bayesian_reference, transition, update, validate_prior, vfe,
)
from fep_persistence.exact import Model as V2Model, evaluate as evaluate_v2, solve as solve_v2

UNIFORM = (1/3,)*3
PROBE = Policy(True, 0, 0)


def after_changes(b, v):
    first = update(initial_belief(UNIFORM), PROBE, (0, 1))  # r1=a1=0
    second = update(transition(first), PROBE, (b ^ v, int(b == 0)))
    return second


class ModelLearningChecks(unittest.TestCase):
    def assertVector(self, a, b):
        self.assertEqual(len(a), len(b))
        for x, y in zip(a, b):
            self.assertAlmostEqual(x, y)

    def test_trajectory_and_transition_normalization(self):
        for prior in (UNIFORM, (.8, .1, .1), (1, 0, 0), (0, 1, 0), (0, 0, 1)):
            q = initial_belief(prior)
            self.assertAlmostEqual(fsum(q), 1)
            self.assertVector(model_marginal(transition(q)), prior)
            for horizon in (1, 2, 3):
                for y in (0, 1):
                    self.assertAlmostEqual(fsum(trajectories(prior, horizon, y).values()), 1)
        self.assertEqual(len(trajectories(UNIFORM, 3)), 384)

    def test_preferences_normalize_on_common_alphabet(self):
        for beta, cost in ((1, 0), (4, .1), (16, .25)):
            # The product measure for H rounds normalizes if each factor does.
            total = fsum(exp(beta*(g-cost*k)-preference_constant(1, beta, cost))
                         for z, g, k in product((NULL, 0, 1), (0, 1), (0, 1)))
            self.assertAlmostEqual(total, 1)
            self.assertAlmostEqual(preference_constant(3, beta, cost),
                                   3*preference_constant(1, beta, cost)+2*log(2))

    def test_analytic_transition_posteriors_and_calibration(self):
        expected = {(0, 0): (5/12, (.4, .2, .4)), (0, 1): (1/12, (0, 1, 0)),
                    (1, 0): (3/12, (2/3, 1/3, 0)), (1, 1): (3/12, (0, 1/3, 2/3))}
        average = [0.0]*3
        for (b, v), (probability, posterior) in expected.items():
            actual = posterior_from_transition(UNIFORM, b, v)
            self.assertVector(actual, posterior)
            self.assertVector(model_marginal(after_changes(b, v)), posterior)
            for m in range(3):
                average[m] += probability*actual[m]
        self.assertVector(average, UNIFORM)

    def test_observed_history_filter_matches_physical_paths(self):
        paths = trajectories(UNIFORM, 3)
        for first_obs, (_, first_post) in round_branches(initial_belief(UNIFORM), PROBE).items():
            prediction = transition(first_post)
            for second_obs, (_, post) in round_branches(prediction, PROBE).items():
                direct = [0.0]*12
                for state, p in paths.items():
                    if path_observation(state, PROBE, 0) == first_obs and path_observation(state, PROBE, 1) == second_obs:
                        m, xs, rs, aas = state
                        direct[INDEX[m, rs[1], aas[1]]] += p
                self.assertVector(post, normalize(direct))

    def test_passive_and_single_probe_cannot_learn_class(self):
        for schedule in product((False, True), repeat=3):
            if sum(schedule) > 1:
                continue
            solution = solve(UNIFORM, 3, 4, .1, "none", schedule=schedule)
            result = evaluate(UNIFORM, 3, solution.node, 4, .1)
            self.assertAlmostEqual(result["information"]["model"], 0)
            distributions = []
            for m in range(3):
                distribution = {}
                for state, p in trajectories(tuple(int(i == m) for i in range(3)), 3).items():
                    o = observable_trajectory(state, solution.node)
                    distribution[o] = distribution.get(o, 0)+p
                distributions.append(distribution)
            self.assertEqual(distributions[0], distributions[1])
            self.assertEqual(distributions[1], distributions[2])

    def test_model_class_remains_fixed_instead_of_redrawn(self):
        # Class uncertainty induces dependence between successive route changes.
        p_two_stable = fsum(p for s, p in trajectories(UNIFORM, 3).items()
                           if s[3][0] == s[3][1] == s[3][2])
        self.assertAlmostEqual(p_two_stable, .5)
        self.assertNotAlmostEqual(p_two_stable, (2/3)**2)

    def test_shared_and_independent_have_equal_marginals_different_joint(self):
        for kernel in KERNELS[1:]:
            self.assertAlmostEqual(fsum(b*p for b, v, p in kernel), .5)
            self.assertAlmostEqual(fsum(v*p for b, v, p in kernel), .5)
        self.assertAlmostEqual(fsum(p for b, v, p in KERNELS[1] if b == v), .5)
        self.assertAlmostEqual(fsum(p for b, v, p in KERNELS[2] if b == v), 1)

    def test_vfe_matches_evidence_and_posterior_divergence(self):
        joint = (1/6, 1/12, 0)
        exact, trial = normalize(joint), (.5, .5, 0)
        evidence_cost = -log(fsum(joint))
        divergence = fsum(a*log(a/b) for a, b in zip(trial, exact) if a)
        self.assertAlmostEqual(vfe(exact, joint), evidence_cost)
        self.assertAlmostEqual(vfe(trial, joint), evidence_cost+divergence)
        self.assertGreater(vfe(trial, joint), vfe(exact, joint))

    def test_zero_support_does_not_silently_restore_excluded_model(self):
        with self.assertRaises(ValueError):
            posterior_from_transition((1, 0, 0), 0, 1)
        first = update(initial_belief((1, 0, 0)), PROBE, (0, 1))
        with self.assertRaises(ValueError):
            update(transition(first), PROBE, (1, 1))

    def test_feedback_is_not_available_for_current_report(self):
        for target in ("all", "model", "task", "none"):
            s = solve(UNIFORM, 3, 4, .1, target)
            result = evaluate(UNIFORM, 3, s.node, 4, .1)
            self.assertAlmostEqual(result["accuracy_by_round"][0], .5)

    def test_bayesian_contingent_policy_beats_best_fixed(self):
        solution = solve(UNIFORM, 3, 4, .1, "none")
        fixed, fixed_solution, _ = best_fixed_schedule(UNIFORM, 3, .1)
        self.assertEqual(fixed, "111")
        self.assertAlmostEqual(solution.utility, 47/30)
        self.assertAlmostEqual(fixed_solution.utility, 23/15)
        self.assertGreater(solution.utility, fixed_solution.utility)
        scored = evaluate(UNIFORM, 3, solution.node, 4, .1)
        self.assertAlmostEqual(scored["expected_probes"], 8/3)
        self.assertVector(scored["accuracy_by_round"], (.5, 2/3, 2/3))

    def test_adaptive_exploration_pays_when_no_fixed_schedule_does(self):
        solution = solve(UNIFORM, 3, 4, .12, "none")
        label, fixed, _ = best_fixed_schedule(UNIFORM, 3, .12)
        self.assertAlmostEqual(solution.utility, 1.5+1/3-(8/3)*.12)
        self.assertEqual(label, "000")
        self.assertAlmostEqual(fixed.utility, 1.5)

    def test_bayesian_root_boundary_with_skip_tie(self):
        for offset in (-1e-6, 0, 1e-6):
            cost = .125+offset
            solution = solve(UNIFORM, 3, 4, cost, "none")
            self.assertEqual(solution.node.policy.probe, offset < 0)
            self.assertAlmostEqual(solution.utility, max(1.5, 1.5+1/3-(8/3)*cost))

    def test_final_probe_depends_on_learned_stable_probability(self):
        for b, v in product((0, 1), repeat=2):
            q = transition(after_changes(b, v))
            stable = model_marginal(q)[0]
            best = solve(UNIFORM, 1, 4, .1, "none", belief=q)
            self.assertEqual(best.node.policy.probe, stable/2 > .1)
            yes = solve(UNIFORM, 1, 4, .1, "none", belief=q, schedule=(True,))
            no = solve(UNIFORM, 1, 4, .1, "none", belief=q, schedule=(False,))
            self.assertAlmostEqual(yes.utility-no.utility, stable/2-.1)

    def test_known_volatile_last_round_separates_epistemic_targets(self):
        q = transition(after_changes(0, 1))
        self.assertVector(model_marginal(q), (0, 1, 0))
        full = solve(UNIFORM, 1, 4, .1, "all", belief=q)
        self.assertTrue(full.node.policy.probe)
        self.assertAlmostEqual(full.utility, .4)
        for target in ("model", "task", "none"):
            result = solve(UNIFORM, 1, 4, .1, target, belief=q)
            self.assertFalse(result.node.policy.probe)
            self.assertAlmostEqual(result.utility, .5)

    def test_full_efe_final_probe_threshold(self):
        q = transition(after_changes(0, 1))
        for offset in (-1e-6, 0, 1e-6):
            s = solve(UNIFORM, 1, 4, log(2)/4+offset, "all", belief=q)
            self.assertEqual(s.node.policy.probe, offset < 0)

    def test_information_chain_and_direct_efe_agree(self):
        for horizon, target in product((1, 2, 3), ("all", "model", "task", "none")):
            s = solve((.8, .1, .1), horizon, 4, .1, target)
            e = evaluate((.8, .1, .1), horizon, s.node, 4, .1)
            self.assertAlmostEqual(s.utility, e["utility"])
            self.assertAlmostEqual(s.information, 0 if target == "none" else e["information"][target])
            self.assertAlmostEqual(e["efe"]["all"], e["efe_direct_all"])
            self.assertAlmostEqual(e["efe"]["all"], e["risk_plus_ambiguity_all"])
            self.assertAlmostEqual(e["information"]["task"], horizon*log(2))

    def test_matched_bayesian_reference_and_task_efe(self):
        for prior, horizon, cost in product((UNIFORM, (.8, .1, .1)), (1, 2, 3), (.1, .15)):
            reference = trajectory_bayesian_reference(prior, horizon, cost)
            for target in ("none", "task"):
                self.assertAlmostEqual(solve(prior, horizon, 4, cost, target).utility, reference)

    def test_model_target_can_still_purchase_unusable_terminal_learning(self):
        # In two rounds the information about M arrives after its last possible use.
        bayes = solve(UNIFORM, 2, 4, .1, "none")
        model = solve(UNIFORM, 2, 4, .1, "model")
        self.assertAlmostEqual(bayes.utility, 1)
        self.assertGreater(model.information, 0)
        self.assertLess(model.utility, bayes.utility)

    def test_fixed_class_horizon_two_reduces_to_v2(self):
        for m, old in enumerate((V2Model(.5, 0), V2Model(.5, .5), V2Model(.5, .5, True))):
            prior = tuple(int(m == i) for i in range(3))
            for target in ("all", "task", "none"):
                new = solve(prior, 2, 4, .1, target)
                prev = solve_v2(old, 0, 4, .1, target)
                a = evaluate(prior, 2, new.node, 4, .1)
                b = evaluate_v2(old, 0, prev.plan, 4, .1)
                self.assertAlmostEqual(a["utility"], b["utility"])
                self.assertAlmostEqual(a["information"]["all"], b["state_information"])
                self.assertAlmostEqual(a["efe"]["all"], b["efe_all"])

    def test_initial_reading_relabeling_preserves_every_score(self):
        for target in ("all", "model", "task", "none"):
            s = solve(UNIFORM, 3, 4, .1, target)
            a, b = (evaluate(UNIFORM, 3, s.node, 4, .1, y) for y in (0, 1))
            self.assertEqual(a, b)

    def test_true_class_evaluation_uses_fixed_policy_without_oracle_label(self):
        for target in ("all", "model", "none"):
            s = solve(UNIFORM, 3, 4, .1, target)
            utility = fsum(evaluate(tuple(int(m == i) for i in range(3)), 3, s.node, 4, .1)["utility"]/3
                           for m in range(3))
            self.assertAlmostEqual(utility, s.utility)

    def test_class_oracle_is_only_an_extra_information_bound(self):
        oracle = fsum(solve(tuple(int(m == i) for i in range(3)), 3, 4, .1, "none").utility/3
                      for m in range(3))
        ordinary = solve(UNIFORM, 3, 4, .1, "none")
        self.assertGreater(oracle, ordinary.utility)
        self.assertAlmostEqual(oracle, (2.2+1.5+1.5)/3)

    def test_invalid_probability_and_policy_contracts(self):
        for prior in ((0, 0, 0), (.5, .5), (.5, .6, -.1), (float('nan'), 0, 1)):
            with self.assertRaises(ValueError):
                validate_prior(prior)
        with self.assertRaises(ValueError):
            Policy(False, 0, 1)

    def test_output_guard_refuses_local_fallback_and_missing_mount(self):
        from fep_model_learning.verify import checked_destination
        with patch('fep_model_learning.verify.os.path.ismount', return_value=False):
            with self.assertRaises(RuntimeError):
                checked_destination(Path('/mnt/bioIce1/fep-ideas/test-no-write'))
        with patch('fep_model_learning.verify.os.path.ismount', return_value=True):
            with self.assertRaises(ValueError):
                checked_destination(Path('/tmp/fep-data-not-allowed'))
            with self.assertRaises(ValueError):
                checked_destination(Path('/mnt/bioIce1/fep-ideas'))


if __name__ == '__main__':
    unittest.main()
