"""New relay wrapper: heterogeneous targets, unequal writes and explicit loss."""

import numpy as np

from memory_metrics import classify, opposite, perturb_recipient, regulatory_distance, recovery_decision
from run_memory_probe import Experiment, array_hash, write_json
from run_onward_transfer import retained_label


def setup(exp, state, name, active=False):
    record = exp.build(state.shape[1], state, active)
    record.update(phase=name, edges_list=[[int(e["from"]), int(e["to"])] for e in exp.sim.GJ_connects],
        all_gj_transport_zero=bool(not np.any(exp.sim.GJ_diffusion)))
    return record


def hold_pair(folder, config, case, initial, ids, indices):
    folder.mkdir()
    exp = Experiment(folder, config, fine=case["fine"])
    rows, setups, canonical, firsts, continuing = [], [], [], [], []
    for j in range(2):
        tag = f"carrier_{j + 1}"
        setups.append(setup(exp, initial[:, j:j + 1], tag + "_hold_1"))
        if exp.indices != indices:
            raise RuntimeError("Changed native ion indices")
        exp.refresh()
        canonical.append(exp.sim.cc_cells.copy())
        first, h1 = exp.phase(tag + "_hold_1", 10000)
        final, h2 = exp.phase(tag + "_hold_2", 10000)
        firsts.append(first)
        continuing.append(final)
        retained = all(h["recipient_label"] == "M" and h["late_label_fractions"]["M"] >= .95 for h in (h1, h2))
        rows.append(dict(id=ids[j], entry_label=str(classify(initial[:, j:j + 1], indices)[0]),
            holds=[h1, h2], M_retained=retained, ion_hold_drift=float(np.max(np.abs(final[:4] - first[:4])))))
    packet = np.concatenate(continuing, axis=1)
    np.savez_compressed(folder / "endpoints.npz", initial_before_refresh=initial,
        canonical_entry=np.concatenate(canonical, axis=1), held_first=np.concatenate(firsts, axis=1), continuing_packet=packet)
    record = dict(incoming_ids=ids, outgoing_ids=ids, carriers=rows, M_retained=all(r["M_retained"] for r in rows),
        setups=setups, audits=exp.audits, new_cue_instances=0, new_contacts=0)
    write_json(folder / "result.json", record)
    return packet, record


def round_worker(folder, config, case, incoming, ids, seen, fresh, later, indices, number, plan):
    if incoming.shape != (17, 2) or fresh.shape != (17, 2) or len(ids) != 2:
        raise ValueError("Require two actual incumbents and two specified fresh recipients")
    columns, durations = plan["active_columns"], plan["contacts"]
    if columns not in ([0], [1], [0, 1]) or len(durations) != 2 or sum(durations) != 2000 or min(durations) <= 0:
        raise ValueError("Invalid fixed survivor or contact schedule")
    if classify(fresh, indices).tolist() != ["E", "E"]:
        raise ValueError("Fresh recipients must start E; no resampling allowed")
    active = incoming[:, columns].copy()
    exp = Experiment(folder, config, fine=case["fine"])
    setups = []

    def build(state, name, connected=False):
        record = setup(exp, state, name, connected)
        if exp.indices != indices:
            raise RuntimeError("Changed native ion indices")
        setups.append(record)
        return record

    initial1 = np.concatenate((fresh[:, :1], active), axis=1)
    build(initial1, "write_1", True)
    contact1, write1 = exp.phase("write_1", durations[0])
    initial2 = np.concatenate((fresh[:, 1:2], contact1[:, 1:]), axis=1)
    build(initial2, "write_2", True)
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
            durable_transfer=bool(written == "M" and waited_ok and retained and recovery["recovered"]),
            ion_hold_drift=float(np.max(np.abs(checkpoint[:4] - firsts[j][:4])))))
        diagnostics.append((changed, shadow, challenged))
    if array_hash(packet) != before_diagnostics:
        raise RuntimeError("Diagnostics contaminated forward packet")
    np.savez_compressed(folder / "endpoints.npz", incoming_packet=incoming, active_packet=active, fresh_targets=fresh,
        first_initial=initial1, second_initial=initial2, contact_1=contact1, contact_2=contact2,
        child_1_waited=waited, held_first=np.concatenate(firsts, axis=1), outgoing_packet=packet,
        perturbed_packet=np.concatenate([d[0] for d in diagnostics], axis=1),
        shadow_packet=np.concatenate([d[1] for d in diagnostics], axis=1),
        challenged_packet=np.concatenate([d[2] for d in diagnostics], axis=1), regulator_scales=scales)
    row = dict(round=number, execution_pass=True, ion_indices=indices, plan=plan,
        incoming_ids=ids, active_ids=[ids[j] for j in columns], lost_ids=[ids[j] for j in range(2) if j not in columns],
        outgoing_ids=new_ids, children=outcomes, round_success=all(o["durable_transfer"] for o in outcomes),
        incoming_packet_hash=array_hash(incoming), outgoing_packet_hash=before_diagnostics,
        diagnostic_branches_enter_lineage=False, setups=setups, audits=exp.audits,
        nominal_round_start=20000 + (number - 4) * 22000, nominal_round_end=42000 + (number - 4) * 22000)
    write_json(folder / "result.json", row)
    return packet, new_ids, row
