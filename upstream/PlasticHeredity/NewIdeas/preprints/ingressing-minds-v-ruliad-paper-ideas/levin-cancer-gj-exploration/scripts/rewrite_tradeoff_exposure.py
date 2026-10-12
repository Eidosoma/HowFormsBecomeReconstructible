"""Reciprocal cue encounter; retain original incumbents, never cue cells."""

import numpy as np

from memory_metrics import classify
from robust_relay import setup
from run_memory_probe import Experiment, write_json


def exposure_steps(case):
    condition = case["condition"]
    rows = []
    for j in (1, 2):
        cue = condition in ("active2", "blocked", "same") or (condition == "active1" and j == 1)
        rows.append(dict(name=f"step_{j}", duration=1000, cue=cue,
            cue_label=("M" if condition == "same" else "E") if cue else None,
            connected=cue and condition != "blocked"))
    return rows


def expose_and_hold(folder, config, case, source, source_ids, seen, refs, indices):
    folder.mkdir()
    width = case["rewrite_width"]
    if width not in (1, 2) or source.shape[0] != 17 or source.shape[1] < width or len(source_ids) != source.shape[1]:
        raise ValueError("Invalid original source group")
    group = source[:, :width].copy()
    group_ids = source_ids[:width]
    removed_before = source_ids[width:]
    initial_group = group.copy()
    exp = Experiment(folder, config, fine=case["fine"])
    setups, steps, cue_ids = [], [], []
    saved = dict(source_packet=source, group_start=group.copy())
    last_contact = None

    def build(state, name, connected=False):
        record = setup(exp, state, name, connected)
        if exp.indices != indices:
            raise RuntimeError("Changed native indices")
        setups.append(record)

    for step in exposure_steps(case):
        name = step["name"]
        before = group.copy()
        if step["cue"]:
            cue_id = case["id"] + ":cue:" + name
            if cue_id in seen:
                raise ValueError("Cue identity reused")
            seen.add(cue_id)
            cue_ids.append(cue_id)
            cue_column = 0 if step["cue_label"] == "E" else 1
            cue = refs["prepared"][:, cue_column:cue_column+1]
            initial = np.concatenate((cue, group), axis=1)
        else:
            initial = group.copy()
        build(initial, name, step["connected"])
        final, phase = exp.phase(name, step["duration"])
        group = final[:, 1:].copy() if step["cue"] else final.copy()
        if step["cue"]:
            last_contact = "".join(classify(group, indices))
        saved[name+"_initial"] = initial
        saved[name+"_full"] = final
        saved[name+"_incumbents"] = group.copy()
        steps.append(dict(step, incumbent_labels_before="".join(classify(before, indices)),
            incumbent_labels_after="".join(classify(group, indices)),
            cue_id=cue_ids[-1] if step["cue"] else None))
    columns = list(range(width)) if case["background"] == "reference" else [0]
    selected = group[:, columns].copy()
    ids = [group_ids[j] for j in columns]
    removed_after = [i for j, i in enumerate(group_ids) if j not in columns]
    firsts, held, carriers = [], [], []
    for j in range(selected.shape[1]):
        name = f"incumbent_{j+1}"
        build(selected[:, j:j+1], name+"_hold_1")
        first, h1 = exp.phase(name+"_hold_1", 10000)
        final, h2 = exp.phase(name+"_hold_2", 10000)
        firsts.append(first)
        held.append(final)
        carriers.append(dict(id=ids[j], entry_label=str(classify(selected[:, j:j+1], indices)[0]),
            holds=[h1, h2], E_retained=all(h["recipient_label"] == "E" and h["late_label_fractions"]["E"] >= .95 for h in (h1, h2)),
            M_retained=all(h["recipient_label"] == "M" and h["late_label_fractions"]["M"] >= .95 for h in (h1, h2))))
    packet = np.concatenate(held, axis=1)
    saved.update(readout_entry=selected, held_first=np.concatenate(firsts, axis=1), continuing_packet=packet)
    np.savez_compressed(folder / "endpoints.npz", **saved)
    last_selected = None if last_contact is None else "".join(last_contact[j] for j in columns)
    record = dict(incoming_ids=source_ids, exposure_ids=group_ids, selected_ids=ids,
        removed_before=removed_before, removed_after=removed_after, removed_cue_ids=cue_ids,
        selected_columns=columns, source_labels="".join(classify(source, indices)),
        exposure_start_labels="".join(classify(initial_group, indices)),
        steps=steps, last_selected_contact_labels=last_selected, carriers=carriers,
        E_retained=all(c["E_retained"] for c in carriers), M_retained=all(c["M_retained"] for c in carriers),
        cue_instances=len(cue_ids), source_clone_count=0, new_reference_edits=0,
        nominal_start=0, nominal_exposure_end=2000, nominal_readout_start=22000,
        setups=setups, audits=exp.audits)
    write_json(folder / "result.json", record)
    return packet, ids, record
