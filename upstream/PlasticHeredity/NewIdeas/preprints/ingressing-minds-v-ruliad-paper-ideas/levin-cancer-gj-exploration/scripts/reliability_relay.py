"""Two declared donor kicks per handover; native equations between kicks."""

import numpy as np

from memory_metrics import classify, opposite, perturb_recipient, regulatory_distance, recovery_decision
from run_memory_probe import Experiment, array_hash, write_json
from run_onward_transfer import retained_label


from robust_relay import setup


def donor_shock(state, factors):
    factors = np.asarray(factors, dtype=float)
    if factors.shape != (3, state.shape[1]) or not np.isfinite(factors).all() or np.any(factors < .75) or np.any(factors > 1.25):
        raise ValueError("Invalid bounded donor shock")
    changed = state.copy()
    changed[5:8] *= factors
    # Derived RNA is recomputed by native refresh; do not edit ions or targets.
    return changed


def round_worker(folder, config, case, incoming, ids, seen, fresh, later, indices, number, plan):
    if incoming.ndim != 2 or incoming.shape[0] != 17 or incoming.shape[1] not in (1, 2) or fresh.shape != (17, 2) or len(ids) != incoming.shape[1]:
        raise ValueError("Require one/two actual incumbents and two fresh recipients")
    columns, durations = plan["active_columns"], plan["contacts"]
    if columns not in ([0], [1], [0, 1]) or any(j >= incoming.shape[1] for j in columns) or durations != [1000, 1000]:
        raise ValueError("Invalid fixed survivor or contact schedule")
    if plan["write_kd"] != 2e-15 or plan["round"] != number or type(plan["connected"]) is not bool:
        raise ValueError("Invalid miRNA diffusion or round")
    if plan["nominal_end"] != plan["nominal_start"] + sum(durations) + 20000:
        raise ValueError("Incorrect nominal clock")
    if classify(fresh, indices).tolist() != [opposite(case["state"])] * 2:
        raise ValueError("Fresh recipients must start opposite the fixed target content")
    selected = incoming[:, columns].copy()
    active = donor_shock(selected, plan["shock_factors"][0])
    exp = Experiment(folder, dict(config, write_kd=plan["write_kd"]), fine=case["fine"])
    setups = []

    def build(state, name, connected=False):
        record = setup(exp, state, name, connected)
        if exp.indices != indices:
            raise RuntimeError("Changed native ion indices")
        setups.append(record)
        return record

    initial1 = np.concatenate((fresh[:, :1], active), axis=1)
    build(initial1, "write_1", plan["connected"])
    contact1, write1 = exp.phase("write_1", durations[0])
    after_second_shock = donor_shock(contact1[:, 1:], plan["shock_factors"][1])
    initial2 = np.concatenate((fresh[:, 1:2], after_second_shock), axis=1)
    build(initial2, "write_2", plan["connected"])
    contact2, write2 = exp.phase("write_2", durations[1])
    build(contact1[:, :1], "wait_1")
    waited, wait = exp.phase("wait_1", durations[1])
    firsts, checkpoints, holds = [], [], []
    for i, child in enumerate((waited, contact2[:, :1]), 1):
        build(child, f"child_{i}_hold_1")
        first, h1 = exp.phase(f"child_{i}_hold_1", 10000)
        final, h2 = exp.phase(f"child_{i}_hold_2", 10000)
        firsts.append(first)
        checkpoints.append(final)
        holds.append([h1, h2])
    new_ids = [f"{case['id']}:round_{number:02}:child_{i}" for i in (1, 2)]
    if set(new_ids) & seen or len(set(new_ids)) != 2:
        raise RuntimeError("Fresh relay identities reused")
    packet = np.concatenate(checkpoints, axis=1)
    before_diagnostics = array_hash(packet)
    scales = np.abs(later[exp.reg, 0] - later[exp.reg, 1])
    outcomes, diagnostics = [], []
    for j, (checkpoint, hold, write) in enumerate(zip(checkpoints, holds, (write1, write2))):
        i, before = j + 1, hold[-1]["recipient_label"]
        target = opposite(before if before in ("E", "M") else "E")
        changed = perturb_recipient(checkpoint, later[:, {"E": 0, "M": 1}[target]], exp.reg, .2)
        ss = build(checkpoint, f"child_{i}_shadow")
        shadow, shadow_record = exp.phase(f"child_{i}_shadow", 5000)
        cs = build(changed, f"child_{i}_challenge")
        challenged, challenge_record = exp.phase(f"child_{i}_challenge", 5000)
        if ss["environment_hash"] != cs["environment_hash"]:
            raise RuntimeError("Diagnostic environments differ")
        d0 = regulatory_distance(changed[exp.reg, 0], checkpoint[exp.reg, 0], scales)
        dfinal = regulatory_distance(challenged[exp.reg, 0], shadow[exp.reg, 0], scales)
        recovery = recovery_decision(d0, dfinal, before, shadow_record["recipient_label"], challenge_record["recipient_label"], config)
        written = write["recipient_label"]
        retained = retained_label(written, hold, shadow_record["recipient_label"], .95)
        waited_ok = i == 2 or (written in ("E", "M") and wait["recipient_label"] == written and wait["late_label_fractions"][written] >= .95)
        outcomes.append(dict(id=new_ids[j], contact_label=written, retained_label=before,
            wait_preserved_label=bool(waited_ok), retained_contact_label=retained, recovery=recovery,
            durable_transfer=bool(written == case["state"] and waited_ok and retained and recovery["recovered"]),
            settled_transfer=bool(all(h["recipient_label"] == case["state"] and h["late_label_fractions"][case["state"]] >= .95 for h in hold)
                and shadow_record["recipient_label"] == case["state"] and recovery["recovered"]),
            ion_hold_drift=float(np.max(np.abs(checkpoint[:4] - firsts[j][:4])))))
        diagnostics.append((changed, shadow, challenged))
    if array_hash(packet) != before_diagnostics:
        raise RuntimeError("Diagnostics contaminated forward packet")
    np.savez_compressed(folder / "endpoints.npz", incoming_packet=incoming, selected_packet=selected, active_packet=active, fresh_targets=fresh,
        after_second_shock=after_second_shock, shock_factors=np.asarray(plan["shock_factors"]),
        first_initial=initial1, second_initial=initial2, contact_1=contact1, contact_2=contact2,
        child_1_waited=waited, held_first=np.concatenate(firsts, axis=1), outgoing_packet=packet,
        perturbed_packet=np.concatenate([d[0] for d in diagnostics], axis=1),
        shadow_packet=np.concatenate([d[1] for d in diagnostics], axis=1),
        challenged_packet=np.concatenate([d[2] for d in diagnostics], axis=1), regulator_scales=scales)
    donor_history = []
    for name, contact in (("write_1", contact1), ("write_2", contact2)):
        with np.load(folder / (name + ".npz"), allow_pickle=False) as saved:
            late = classify(saved["concentrations"], indices)[saved["times"] >= .75 * durations[0], 1:]
            donor_history.append(dict(phase=name, entry_labels="".join(classify(saved["initial"][:, 1:], indices)),
                end_labels="".join(classify(contact[:, 1:], indices)),
                late_target_fractions=[float(np.mean(late[:, j] == case["state"])) for j in range(len(columns))],
                end_regulators=contact[exp.reg, 1:].tolist()))
    accounting = dict(active_donors=len(columns), total_contact_time=sum(durations),
        donor_contact_time=len(columns) * sum(durations),
        summed_miRNA_kd_time=len(columns) * (plan["write_kd"] if plan["connected"] else 0) * sum(durations),
        actual_molecular_flux_measured=False, energetic_cost_measured=False)
    row = dict(round=number, execution_pass=True, ion_indices=indices, plan=plan,
        incoming_ids=ids, active_ids=[ids[j] for j in columns], lost_ids=[ids[j] for j in range(len(ids)) if j not in columns],
        outgoing_ids=new_ids, children=outcomes, round_success=all(o["durable_transfer"] for o in outcomes),
        settled_round_success=all(o["settled_transfer"] for o in outcomes),
        donor_contact_history=donor_history, nominal_accounting=accounting,
        selected_labels="".join(classify(selected, indices)),
        after_first_shock_labels="".join(classify(active, indices)),
        after_second_shock_labels="".join(classify(after_second_shock, indices)),
        incoming_packet_hash=array_hash(incoming), outgoing_packet_hash=before_diagnostics,
        diagnostic_branches_enter_lineage=False, setups=setups, audits=exp.audits,
        nominal_round_start=plan["nominal_start"], nominal_round_end=plan["nominal_end"])
    write_json(folder / "result.json", row)
    return packet, new_ids, row

