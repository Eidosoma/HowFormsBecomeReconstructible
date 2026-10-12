"""Algebra, causality, memory, and temporal accounting for the two-round model."""
from itertools import product
from math import exp, fsum, log
import unittest

from fep_formal.exact import Model as OneModel, POLICIES as ONE_POLICIES, score as one_score
from fep_persistence.exact import (
    Model, NULL, POLICIES, STATES, Policy, analytic_choice, analytic_schedules,
    bayesian_reference, entropy, evaluate, forgetting_plan, information,
    log_preference, normalize, outcome, partition, round_bits, schedule_plan,
    second_reading, solve, target_entropy, trajectory_joint, vfe,
)


class PersistenceChecks(unittest.TestCase):
    def test_normalized_trajectory_and_initial_evidence(self):
        for delta, nu in product((0.0, 0.1, 0.5), repeat=2):
            model = Model(delta, nu)
            self.assertEqual(len(model.prior()), 64)
            self.assertAlmostEqual(fsum(model.prior().values()), 1)
            for y1 in (0, 1):
                evidence = fsum(p for s, p in model.prior().items() if s[0] ^ s[1] == y1)
                self.assertAlmostEqual(evidence, 0.5)
                self.assertAlmostEqual(fsum(model.posterior(y1).values()), 1)

    def test_joint_preference_normalization_and_fixed_cost(self):
        for beta, cost in ((1, 0), (4, 0.1), (16, 0.6)):
            alphabet = product((NULL, 0, 1), (0, 1), (0, 1), (0, 1), (NULL, 0, 1), (0, 1), (0, 1))
            self.assertAlmostEqual(fsum(exp(log_preference(o, beta, cost)) for o in alphabet), 1)
            a, b = (NULL, 0, 0, 0, NULL, 0, 0), (NULL, 0, 0, 0, NULL, 0, 1)
            self.assertAlmostEqual(log_preference(b, beta, cost)-log_preference(a, beta, cost), -beta*cost)

    def test_first_round_matches_v1_with_no_future(self):
        # Physical process, utilities, and information must reduce to v1, not a relabeled task.
        model = Model(0.25, 0.1)
        for y1, old_policy, new_policy in product((0, 1), ONE_POLICIES, POLICIES):
            if (old_policy.probe, old_policy.d0, old_policy.d1) != (new_policy.probe, new_policy.d0, new_policy.d1):
                continue
            q = model.posterior(y1)
            branches = partition(q, lambda s: outcome(s, new_policy, 1))
            u = fsum(p*(o[1]-0.1*o[2]) for o, (p, post) in branches.items())
            previous = one_score(OneModel.independent(rho=0.5), y1, old_policy, 4, 0.1)
            self.assertAlmostEqual(u, previous.utility)
            self.assertAlmostEqual(information(q, branches, "all"), previous.state_information)
            self.assertAlmostEqual(information(q, branches, "task"), previous.task_information)

    def test_vfe_on_fixed_trajectory_model_and_history(self):
        model = Model(0.25, 0.1)
        joint = {s: p for s, p in model.prior().items() if s[0] ^ s[1] == 0}
        exact = normalize(joint)
        trial = {s: 1/len(exact) for s in exact}
        divergence = fsum(p*log(p/exact[s]) for s, p in trial.items())
        self.assertAlmostEqual(vfe(exact, joint), log(2))
        self.assertAlmostEqual(vfe(trial, joint), divergence+log(2))
        self.assertGreater(vfe(trial, joint), vfe(exact, joint))

    def test_no_first_round_information_advantage_from_future_feedback(self):
        model = Model(0.5, 0)
        for first, second in product((False, True), repeat=2):
            plan = schedule_plan(model, 0, first, second)
            result = evaluate(model, 0, plan, 4, 0.1)
            self.assertAlmostEqual(result["accuracy_round1"], 0.5)

    def test_ordinary_feedback_already_identifies_sensor_mapping(self):
        q = Model(0.25, 0.1).posterior(0)
        for policy in POLICIES:
            for o, (p, post) in partition(q, lambda s: outcome(s, policy, 1)).items():
                self.assertEqual(len({s[1] for s in post}), 1)
                self.assertEqual(len({s[2] for s in post}), 1 if policy.probe else 2)

    def test_information_chain_matches_full_trajectory(self):
        for model in (Model(0, 0), Model(0.25, 0.1), Model(0.5, 0.5)):
            for target in ("all", "task", "none"):
                solution = solve(model, 0, 4, 0.1, target)
                result = evaluate(model, 0, solution.plan, 4, 0.1)
                expected = 0.0 if target == "none" else result["state_information" if target == "all" else "task_information"]
                self.assertAlmostEqual(solution.utility, result["utility"])
                self.assertAlmostEqual(solution.information, expected)
                self.assertAlmostEqual(result["efe_all"], result["efe_direct"])
                self.assertAlmostEqual(result["efe_all"], result["risk_plus_ambiguity"])

    def test_all_four_schedule_formulas(self):
        for delta, nu in product((0, 0.1, 0.25, 0.5), repeat=2):
            model = Model(delta, nu)
            expected = analytic_schedules(model, 4, 0.1)
            for k1, k2 in product((False, True), repeat=2):
                result = evaluate(model, 0, schedule_plan(model, 0, k1, k2), 4, 0.1)
                theory = expected[f"{int(k1)}{int(k2)}"]
                self.assertAlmostEqual(result["utility"], theory["utility"])
                self.assertAlmostEqual(result["state_information"], theory["state_information"])
                self.assertAlmostEqual(result["task_information"], 2*log(2))

    def test_persistent_route_information_is_not_counted_twice(self):
        model = Model(0.5, 0)
        one = evaluate(model, 0, schedule_plan(model, 0, True, False), 4, 0.1)
        two = evaluate(model, 0, schedule_plan(model, 0, True, True), 4, 0.1)
        self.assertAlmostEqual(one["state_information"], two["state_information"])
        self.assertGreater(two["accuracy_round2"], one["accuracy_round2"])

    def test_bayesian_future_information_threshold_and_boundary(self):
        for delta, nu in ((0.5, 0), (0.25, 0.1), (0.5, 0.25)):
            model = Model(delta, nu)
            boundary = (delta-nu)/2
            for offset in (-1e-6, 0, 1e-6):
                cost = boundary+offset
                reference = evaluate(model, 0, bayesian_reference(model, 0, cost), 4, cost)
                dynamic = solve(model, 0, 4, cost, "none")
                self.assertEqual(reference["schedule"], "11" if offset < 0 else "00")
                self.assertAlmostEqual(dynamic.utility, reference["utility"])

    def test_full_tree_search_matches_analytic_efe_choice(self):
        for delta, nu, cost in product((0, 0.25, 0.5), (0, 0.1, 0.5), (0.0, 0.1, 0.3, 0.6)):
            model = Model(delta, nu)
            solution = solve(model, 0, 4, cost, "all")
            result = evaluate(model, 0, solution.plan, 4, cost)
            self.assertEqual(result["schedule"], analytic_choice(model, 4, cost))

    def test_task_efe_matches_strong_bayesian_reference(self):
        for delta, nu, cost in product((0, 0.25, 0.5), (0, 0.1, 0.5), (0.1, 0.3)):
            model = Model(delta, nu)
            full = solve(model, 0, 4, cost, "task")
            reference = evaluate(model, 0, bayesian_reference(model, 0, cost), 4, cost)
            self.assertAlmostEqual(full.utility, reference["utility"])
            self.assertAlmostEqual(full.information, 2*log(2))

    def test_useful_exploration_requires_both_costs(self):
        model = Model(0.5, 0)
        efe = solve(model, 0, 4, 0.1, "all")
        bayes = evaluate(model, 0, bayesian_reference(model, 0, 0.1), 4, 0.1)
        self.assertAlmostEqual(efe.utility, 1.3)
        self.assertAlmostEqual(bayes["utility"], 1.3)
        self.assertAlmostEqual(bayes["expected_probes"], 2)
        self.assertFalse(bayesian_reference(model, 0, 0.3).first.probe)

    def test_stable_sensor_does_not_need_extra_diagnostic_memory(self):
        model = Model(0, 0)
        bayes = evaluate(model, 0, bayesian_reference(model, 0, 0.1), 4, 0.1)
        efe = evaluate(model, 0, solve(model, 0, 4, 0.1, "all").plan, 4, 0.1)
        self.assertEqual(bayes["schedule"], "00")
        self.assertAlmostEqual(bayes["utility"], 1.5)
        self.assertEqual(efe["schedule"], "01")
        self.assertAlmostEqual(efe["utility"], 1.4)

    def test_fully_refreshing_route_rewards_information_without_utility(self):
        model = Model(0.5, 0.5)
        efe = evaluate(model, 0, solve(model, 0, 4, 0.1, "all").plan, 4, 0.1)
        bayes = evaluate(model, 0, bayesian_reference(model, 0, 0.1), 4, 0.1)
        self.assertEqual(efe["schedule"], "11")
        self.assertAlmostEqual(efe["utility"], 0.8)
        self.assertAlmostEqual(bayes["utility"], 1.0)

    def test_forgetting_is_separate_from_objective_comparison(self):
        for delta in (0, 0.1, 0.5):
            model = Model(delta, 0.1)
            result = evaluate(model, 0, forgetting_plan(model, 0), 4, 0.1)
            self.assertAlmostEqual(result["accuracy_round1"], 0.5)
            self.assertAlmostEqual(result["accuracy_round2"], 0.5)
            self.assertAlmostEqual(result["expected_probes"], 0)

    def test_wrong_persistence_harms_both_fixed_policies(self):
        assumed, truth = Model(0.5, 0), Model(0.5, 0.5)
        for plan in (solve(assumed, 0, 4, 0.1, "all").plan, bayesian_reference(assumed, 0, 0.1)):
            expected = evaluate(assumed, 0, plan, 4, 0.1)
            actual = evaluate(truth, 0, plan, 4, 0.1)
            self.assertAlmostEqual(expected["utility"], 1.3)
            self.assertAlmostEqual(actual["utility"], 0.8)
            self.assertAlmostEqual(actual["accuracy_round2"], 0.5)

    def test_shared_fault_preserves_marginals_but_changes_joint_information(self):
        shared = Model(0.5, 0.5, shared_flip=True)
        self.assertAlmostEqual(fsum(shared.prior().values()), 1)
        for index in (3, 4):
            self.assertAlmostEqual(fsum(p*s[index] for s, p in shared.prior().items()), 0.5)
        for s, p in shared.prior().items():
            if p > 0:
                self.assertEqual(s[1] ^ s[2], (s[1] ^ s[3]) ^ (s[2] ^ s[4]))
        once = evaluate(shared, 0, schedule_plan(shared, 0, False, True), 4, 0.1)
        twice = evaluate(shared, 0, schedule_plan(shared, 0, True, True), 4, 0.1)
        self.assertAlmostEqual(once["state_information"], twice["state_information"])
        selected = evaluate(shared, 0, solve(shared, 0, 4, 0.1, "all").plan, 4, 0.1)
        self.assertEqual(selected["schedule"], "01")
        self.assertAlmostEqual(selected["utility"], 0.9)

    def test_shared_fault_analytic_formulas_and_policy(self):
        for rate, cost in product((0, 0.1, 0.25, 0.5), (0.0, 0.1, 0.3)):
            model = Model(rate, rate, shared_flip=True)
            for k1, k2 in product((False, True), repeat=2):
                result = evaluate(model, 0, schedule_plan(model, 0, k1, k2), 4, cost)
                theory = analytic_schedules(model, 4, cost)[result["schedule"]]
                self.assertAlmostEqual(result["state_information"], theory["state_information"])
                self.assertAlmostEqual(result["utility"], theory["utility"])
            selected = evaluate(model, 0, solve(model, 0, 4, cost, "all").plan, 4, cost)
            self.assertEqual(selected["schedule"], analytic_choice(model, 4, cost))
        with self.assertRaises(ValueError):
            Model(0.1, 0.25, shared_flip=True)

    def test_initial_bit_relabeling_does_not_change_values(self):
        model = Model(0.25, 0.1)
        for target in ("all", "task", "none"):
            a, b = (solve(model, y, 4, 0.1, target) for y in (0, 1))
            self.assertAlmostEqual(a.utility, b.utility)
            self.assertAlmostEqual(a.information, b.information)

    def test_invalid_rates_and_policy_support_are_rejected(self):
        with self.assertRaises(ValueError):
            Model(0.6, 0)
        with self.assertRaises(ValueError):
            Model(float("nan"), 0)
        with self.assertRaises(ValueError):
            solve(Model(0, 0), 0, 0, 0.1, "all")
        plan = schedule_plan(Model(0, 0), 0, False, False)
        plan.second.clear()
        with self.assertRaises(ValueError):
            trajectory_joint(Model(0, 0), 0, plan)


if __name__ == "__main__":
    unittest.main()
