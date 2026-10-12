import numpy as np

from laws_confirmation.doorkey_carrier import GermSchema, empty_germ, read_germ
from laws_confirmation.doorkey_causal_writer import (
    CausalWriterLedger,
    MIN_VERIFIED_EFFECTS,
    derive_causal_writer_decision,
    exact_interaction_opportunity,
    renew_germ_from_causal_evidence,
    router_context_numpy,
)
from laws_confirmation.doorkey_env import Action, DoorKeyEnv, make_layout, oracle_plan


def _ledger_with_effect(slot: int, action: int, count: int = MIN_VERIFIED_EFFECTS):
    ledger = CausalWriterLedger.empty()
    ledger.effect_action_counts[slot, action] = count
    ledger.context_action_counts[slot, action] = count
    ledger.birth_probability_sums[slot] = count / 8.0
    ledger.final_probability_sums[slot, action] = count
    ledger.transition_count = count
    return ledger


def _valid_probe_observations():
    env = DoorKeyEnv(make_layout(12345), max_steps=128)
    key_observation = door_observation = None
    for action in oracle_plan(env.layout):
        observation = env.observation().vector()
        if int(action) == int(Action.PICKUP):
            key_observation = observation.copy()
        if int(action) == int(Action.OPEN):
            door_observation = observation.copy()
        env.step(action)
    assert key_observation is not None and door_observation is not None
    return key_observation, door_observation


def test_router_and_exact_opportunity_match_valid_world_states():
    key, door = _valid_probe_observations()
    assert router_context_numpy(key) == 1
    assert router_context_numpy(door) == 3
    assert exact_interaction_opportunity(key, 1)
    assert exact_interaction_opportunity(door, 3)

    near_key = key.copy()
    near_key[10] = 0.0
    near_key[1] = DoorKeyEnv.KEY
    assert router_context_numpy(near_key) == 1
    assert not exact_interaction_opportunity(near_key, 1)


def test_ten_neutral_baseline_effects_clear_unchanged_trust_threshold():
    ledger = _ledger_with_effect(1, int(Action.PICKUP))
    decision = derive_causal_writer_decision(ledger)
    assert decision.confirmation_mask.tolist() == [[False, True, False, False]]
    assert decision.targets[1] == int(Action.PICKUP)
    assert decision.confidence[1] >= GermSchema().min_write_trust / 255.0
    renewal = renew_germ_from_causal_evidence(
        ledger, empty_germ(1, GermSchema())
    )
    decoded = read_germ(renewal.germ)
    assert renewal.new_write_mask.tolist() == [[False, True, False, False]]
    assert decoded.active.tolist() == [[False, True, False, False]]


def test_same_content_is_actively_renewed_and_changed_content_overwrites():
    pickup = _ledger_with_effect(1, int(Action.PICKUP))
    first = renew_germ_from_causal_evidence(pickup, empty_germ(1)).germ
    same = renew_germ_from_causal_evidence(pickup, first)
    assert same.same_content_renewal_mask[0, 1]
    assert same.germ.reshape(4, 16)[1, 13] == 0

    changed = _ledger_with_effect(1, int(Action.OPEN))
    overwritten = renew_germ_from_causal_evidence(changed, same.germ)
    assert overwritten.semantic_change_mask[0, 1]
    assert read_germ(overwritten.germ).prior_logits[0, 1].argmax() == Action.OPEN


def test_silence_ages_then_abstains_without_changing_payload_or_trust():
    written = renew_germ_from_causal_evidence(
        _ledger_with_effect(1, int(Action.PICKUP)), empty_germ(1)
    ).germ
    original = written.reshape(4, 16)[1].copy()
    silent = CausalWriterLedger.empty()
    current = written
    for _ in range(33):
        result = renew_germ_from_causal_evidence(silent, current)
        current = result.germ
    slot = current.reshape(4, 16)[1]
    assert np.array_equal(slot[4:13], original[4:13])
    assert slot[13] == 33
    assert not read_germ(current).active[0, 1]


def test_exact_failed_opportunities_revoke_but_near_misses_do_not():
    inherited = renew_germ_from_causal_evidence(
        _ledger_with_effect(1, int(Action.OPEN)), empty_germ(1)
    ).germ
    near_miss = CausalWriterLedger.empty()
    near_miss.context_action_counts[1, Action.OPEN] = MIN_VERIFIED_EFFECTS
    near_miss.transition_count = MIN_VERIFIED_EFFECTS
    held = renew_germ_from_causal_evidence(near_miss, inherited)
    assert not held.revocation_mask.any()
    assert read_germ(held.germ).active[0, 1]

    refuted = CausalWriterLedger.empty()
    refuted.context_action_counts[1, Action.OPEN] = MIN_VERIFIED_EFFECTS
    refuted.interaction_attempt_counts[1, Action.OPEN] = MIN_VERIFIED_EFFECTS
    refuted.transition_count = MIN_VERIFIED_EFFECTS
    revoked = renew_germ_from_causal_evidence(refuted, inherited)
    assert revoked.revocation_mask[0, 1]
    assert not read_germ(revoked.germ).active[0, 1]


def test_record_requires_real_before_after_effect_not_event_label_alone():
    key, _ = _valid_probe_observations()
    ledger = CausalWriterLedger.empty()
    probabilities = np.full(8, 1 / 8, dtype=np.float64)
    fake_after = key.copy()
    fired = ledger.record(
        key,
        int(Action.PICKUP),
        fake_after,
        {"events_fired": (), "acquired": True, "opened": False},
        probabilities,
        probabilities,
    )
    assert not fired
    assert ledger.effect_action_counts.sum() == 0
    assert ledger.interaction_attempt_counts[1, Action.PICKUP] == 1
