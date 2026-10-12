"""Independent algebraic and decision-theoretic checks of the finite model."""
from itertools import product
from math import exp, fsum, inf, log
import unittest

from fep_formal.exact import (
    Model, NULL, OUTCOMES, POLICIES, STATES, Policy, bayesian_plan, choose,
    entropy, kl, log_preference, misspecification_example, mutual_information,
    normalize, predictive_joint, score, vfe,
)


class ExactModelChecks(unittest.TestCase):
    def test_normalized_physical_branches(self):
        for model in (Model.independent(), Model.independent(0.2, 0.4, 0.1),
                      Model.independent(sham=True), Model.common_fault()):
            self.assertAlmostEqual(fsum(model.prior), 1.0)
            for s in STATES:
                for probe in (False, True):
                    self.assertAlmostEqual(fsum(model.diagnostic(s, probe, z)
                                               for z in (NULL, 0, 1)), 1.0)
            for y in (0, 1):
                if fsum(model.initial_joint(y)) == 0.0:
                    continue
                for policy in POLICIES:
                    self.assertAlmostEqual(fsum(predictive_joint(model, y, policy).values()), 1.0)

    def test_preferences_have_one_common_normalization(self):
        for beta, cost in product((1.0, 4.0, 16.0), (0.0, 0.1, 0.6)):
            self.assertAlmostEqual(fsum(exp(log_preference(o, beta, cost)) for o in OUTCOMES), 1.0)
            self.assertAlmostEqual(log_preference((0, 1, 0), beta, cost)
                                   - log_preference((0, 0, 0), beta, cost), beta)
            self.assertAlmostEqual(log_preference((0, 0, 1), beta, cost)
                                   - log_preference((0, 0, 0), beta, cost), -beta*cost)

    def test_vfe_identity_for_nonoptimal_and_exact_inference(self):
        model = Model.independent(0.3, 0.2, 0.1)
        joint = model.history_joint(0, 0)
        posterior = normalize(joint)
        trial = model.posterior(0)
        evidence = fsum(joint)
        self.assertAlmostEqual(vfe(posterior, joint), -log(evidence))
        self.assertAlmostEqual(vfe(trial, joint), kl(trial, posterior)-log(evidence))
        self.assertGreater(vfe(trial, joint), vfe(posterior, joint))

    def test_zero_support_is_not_replaced_by_a_floor(self):
        self.assertEqual(vfe((0.5, 0.5), (0.25, 0.0)), inf)
        self.assertEqual(kl((0.5, 0.5), (1.0, 0.0)), inf)
        self.assertAlmostEqual(vfe((1.0, 0.0), (0.25, 0.0)), -log(0.25))
        with self.assertRaises(ValueError):
            normalize((0.0, 0.0))
        with self.assertRaises(ValueError):
            Model.common_fault().posterior(1)

    def test_invalid_distributions_are_rejected(self):
        for weights in ((-0.1, 1.1), (float("nan"), 1.0)):
            with self.assertRaises(ValueError):
                normalize(weights)
        with self.assertRaises(ValueError):
            vfe((0.2, 0.2), (0.1, 0.3))
        with self.assertRaises(ValueError):
            Model.independent(noise=0.6)

    def test_three_efe_calculations_agree(self):
        for model in (Model.independent(0.3, 0.2, 0.1),
                      Model.independent(sham=True), Model.common_fault()):
            for policy in POLICIES:
                s = score(model, 0, policy, 4.0, 0.15)
                self.assertAlmostEqual(s.efe_all, s.efe_direct)
                self.assertAlmostEqual(s.efe_all, s.risk_plus_ambiguity)

    def test_bayesian_control_already_values_useful_information(self):
        policy = bayesian_plan(Model.independent(), 0, 0.1)
        self.assertEqual(policy, Policy(True, 0, 1))
        self.assertAlmostEqual(score(Model.independent(), 0, policy, 4.0, 0.1).utility, 0.9)

    def test_known_mapping_equivalence_with_nonuniform_prior_and_noise(self):
        for alpha, noise, cost, y in product((0.1, 0.5, 0.9), (0.0, 0.1), (0.0, 0.1, 0.6), (0, 1)):
            model = Model.independent(alpha=alpha, noise=noise)
            self.assertEqual(choose(model, y, 4.0, cost, "efe_all"), bayesian_plan(model, y, cost))

    def test_no_postdecision_feedback_leakage(self):
        model = Model.independent(rho=0.5)
        for policy in POLICIES:
            result = score(model, 0, policy, 4.0, 0.1)
            self.assertAlmostEqual(result.accuracy, 0.5)
            self.assertAlmostEqual(result.task_information, log(2))
        self.assertFalse(bayesian_plan(model, 0, 0.1).probe)
        self.assertTrue(choose(model, 0, 4.0, 0.1, "efe_all").probe)

    def test_information_gain_and_threshold_formulas(self):
        for rho, noise, beta in product((0.1, 0.25, 0.5), (0.0, 0.1), (1.0, 4.0, 16.0)):
            model = Model.independent(rho=rho, noise=noise)
            t = rho+noise-2*rho*noise
            delta = 0.5-t
            extra = entropy((t, 1-t))-entropy((noise, 1-noise))
            efe_boundary = delta+extra/beta
            for offset in (-1e-6, 0.0, 1e-6):
                cost = efe_boundary+offset
                self.assertEqual(choose(model, 0, beta, cost, "efe_all").probe, offset < 0)
            for offset in (0.0, 1e-6):
                self.assertFalse(bayesian_plan(model, 0, delta+offset).probe)
            if delta > 1e-6:
                self.assertTrue(bayesian_plan(model, 0, delta-1e-6).probe)

    def test_task_state_and_ablation_match_bayesian_optimum(self):
        for alpha, rho, noise, cost in product((0.1, 0.5, 0.9), (0.0, 0.25, 0.5), (0.0, 0.1), (0.0, 0.1, 0.3)):
            model = Model.independent(alpha, rho, noise)
            reference = bayesian_plan(model, 0, cost)
            for objective in ("efe_task", "preference_cross_entropy"):
                self.assertEqual(choose(model, 0, 4.0, cost, objective), reference)

    def test_sham_randomness_is_not_state_information(self):
        model = Model.independent(rho=0.5, sham=True)
        for policy in POLICIES:
            self.assertAlmostEqual(score(model, 0, policy, 4.0, 0.1).state_information, log(2))
        self.assertFalse(choose(model, 0, 4.0, 0.1, "efe_all").probe)

    def test_complemented_causes_have_equal_predecision_likelihoods(self):
        model = Model.independent(noise=0.1)
        for s in STATES:
            complement = tuple(1-bit for bit in s)
            self.assertEqual(s[0] ^ s[1], complement[0] ^ complement[1])
            for z in (0, 1):
                self.assertEqual(model.diagnostic(s, True, z), model.diagnostic(complement, True, z))

    def test_ambiguous_observations_preserve_prior_odds(self):
        prior = tuple(0.8 if s == (0, 0, 0) else 0.2 if s == (1, 1, 1) else 0.0 for s in STATES)
        model = Model(prior, noise=0.1)
        for z in (0, 1):
            posterior = normalize(model.history_joint(0, z))
            self.assertAlmostEqual(posterior[0]/posterior[-1], 4.0)

    def test_correct_common_fault_model_does_not_buy_useless_diagnosis(self):
        model = Model.common_fault()
        for objective in ("efe_all", "efe_task", "preference_cross_entropy"):
            self.assertFalse(choose(model, 0, 4.0, 0.1, objective).probe)

    def test_fixed_model_vfe_can_improve_while_external_log_loss_worsens(self):
        result = misspecification_example()
        self.assertAlmostEqual(result["vfe_before"], -log(0.25)+0.5*log(25/9))
        self.assertAlmostEqual(result["vfe_after"], -log(0.25))
        self.assertAlmostEqual(result["external_log_loss_before"], log(2))
        self.assertAlmostEqual(result["external_log_loss_after"], -0.5*log(0.09))
        self.assertAlmostEqual(result["assumed_world_after"][1], 0.1)
        self.assertEqual(result["true_world_posterior"], (0.5, 0.5))

    def test_full_state_information_is_invariant_to_bijective_relabeling(self):
        joint = predictive_joint(Model.independent(0.3, 0.4, 0.1), 0, Policy(True, 0, 1))
        relabeled = {(tuple(1-b for b in s), o): p for (s, o), p in joint.items()}
        self.assertAlmostEqual(mutual_information(joint), mutual_information(relabeled))


if __name__ == "__main__":
    unittest.main()
