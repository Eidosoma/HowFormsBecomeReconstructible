"""Independent retained-parent and value/layout crossover checks (D080)."""

from dataclasses import asdict
import hashlib
import importlib.util
import json
import math
from pathlib import Path

import numpy as np

from laws_confirmation import l22_source_recovery as source
from laws_confirmation.io import canonical_digest

_spec = importlib.util.spec_from_file_location("d080_frozen_checker", Path(__file__).with_name("audit_l22_fresh_donor_reversal_outputs.py"))
previous = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(previous)
common, readout, runtime = previous.common, previous.readout, previous.runtime
exact = previous.previous.exact
TISSUES, DISPOSABLES = tuple(range(30056, 30072)), (402081, 402082)
CFG = dict(replicates=4, settle=120, imprint=1000, sweeps=1000, times=[0, 1, 50, 250, 500, 1000], norm=.3, lam=.001, damage=.3)
RCFG = dict(parents=4, draws=16, sweeps=1000, times=[0, 1, 1000])
BODIES = ("kept", "forward", "forwardshuffled", "reverse", "reverseshuffled", "forwardvalues", "reversevalues")
READERS, FIELDS = ("damaged", "native"), ("V", "R", "theta")
MAIN = tuple(f"{b}_{r}" for b in BODIES for r in READERS)
OFF = tuple(f"{b}_{r}_off" for b in BODIES[1:] for r in READERS)
RECOVERIES = (*MAIN, *OFF)
REPLAYS = ("forwardvalues_damaged", "forwardvalues_native", "reversevalues_damaged", "reversevalues_native")
PACKETS, ARMS = (*MAIN, "parent", "damaged"), (*MAIN, "parent", "damaged", "wrong_forward", "wrong_reverse", "reader_off")
METRICS = ("own_projection", "forward_projection", "reverse_projection", "own_accuracy", "forward_accuracy", "reverse_accuracy", "forward_minus_reverse")
FUNCTIONAL = METRICS[3:]
TERMS = {k: tuple(v) for k, v in previous.TERMS.items()}
for r in READERS:
    ff, fr, rf, rr = (f"{b}_{r}" for b in ("forward", "forwardvalues", "reversevalues", "reverse"))
    local = {
        "layout_at_forward_values": ((ff, 1), (fr, -1)),
        "layout_at_reverse_values": ((rf, 1), (rr, -1)),
        "values_at_forward_layout": ((ff, 1), (rf, -1)),
        "values_at_reverse_layout": ((fr, 1), (rr, -1)),
        "value_effect": ((ff, .5), (fr, .5), (rf, -.5), (rr, -.5)),
        "layout_effect": ((ff, .5), (fr, -.5), (rf, .5), (rr, -.5)),
        "value_layout_interaction": ((ff, 1), (fr, -1), (rf, -1), (rr, 1)),
        "crossed_preference": ((fr, 1), (rf, -1)),
        "forwardvalues_minus_forwardshuffled": ((fr, 1), (f"forwardshuffled_{r}", -1)),
        "reversevalues_minus_reverseshuffled": ((rf, 1), (f"reverseshuffled_{r}", -1)),
    }
    TERMS.update({f"{name}_{r}": terms for name, terms in local.items()})
for b in ("forwardvalues", "reversevalues"):
    TERMS[f"{b}_native_minus_damaged"] = ((f"{b}_native", 1), (f"{b}_damaged", -1))
for name in ("value_effect", "layout_effect", "value_layout_interaction"):
    TERMS[f"{name}_reader_interaction"] = TERMS[f"{name}_native"] + tuple((a, -w) for a, w in TERMS[f"{name}_damaged"])


def check_bodies(boundary, bodies, tissue, rep=4):
    kept, fresh = boundary["kept_V"], boundary["fresh"]
    assert kept.dtype == np.float64 and fresh.dtype == bool and kept.shape == fresh.shape == (4*rep, 16, 16)
    assert set(bodies) == {f"{b}_V" for b in BODIES} | {"forward_indices", "reverse_indices", "permutations", "forward_layout_order", "reverse_layout_order"}
    assert bodies["permutations"].dtype.kind in "iu" and bodies["permutations"].shape == (rep, 128)
    rng = common.seeded(tissue, "shuffle")
    permutations = np.array([rng.permutation(128) for _ in range(rep)])
    np.testing.assert_array_equal(bodies["permutations"], permutations)
    expected = {b: kept.copy() for b in BODIES}
    for name, shift in (("forward", 1), ("reverse", -1)):
        assert bodies[f"{name}_indices"].dtype.kind in "iu" and bodies[f"{name}_indices"].shape == (4*rep,)
        for i in range(4*rep):
            j = ((i//rep+shift) % 4)*rep + i % rep
            assert bodies[f"{name}_indices"][i] == j and j != i
            np.testing.assert_array_equal(fresh[i], fresh[j])
            positions = [p for p, f in enumerate(fresh[i].flat) if not f]
            assert len(positions) == 128
            for k, pos in enumerate(positions):
                expected[name][i].flat[pos] = kept[j].flat[pos]
                expected[name+"shuffled"][i].flat[pos] = kept[j].flat[positions[int(permutations[i % rep, k])]]
    for i in range(4*rep):
        positions = [p for p, f in enumerate(fresh[i].flat) if not f]
        donors = {d: [float(expected[d][i].flat[p]) for p in positions] for d in ("forward", "reverse")}
        orders = {d: sorted(range(128), key=lambda k: (donors[d][k], k)) for d in donors}
        for d in donors:
            order = bodies[f"{d}_layout_order"]
            assert order.dtype.kind in "iu" and order.shape == (4*rep, 128)
            assert order[i].tolist() == orders[d]
        for body, values_from, layout_from in (("forwardvalues", "forward", "reverse"), ("reversevalues", "reverse", "forward")):
            values = sorted(donors[values_from])
            for rank, k in enumerate(orders[layout_from]):
                expected[body][i].flat[positions[k]] = values[rank]
            assert sorted(float(bodies[f"{body}_V"][i].flat[p]) for p in positions) == values
    geometry = {}
    for body in BODIES:
        value = bodies[f"{body}_V"]
        assert value.dtype == np.float64 and np.isfinite(value).all()
        np.testing.assert_array_equal(value, expected[body])
        rows = []
        for i in range(4*rep):
            positions = [p for p, f in enumerate(fresh[i].flat) if not f]
            values = [float(value[i].flat[p]) for p in positions]
            mean = math.fsum(values)/128
            rows.append(dict(retained_mean=mean, retained_std=math.sqrt(math.fsum((v-mean)**2 for v in values)/128),
                retained_rms=math.sqrt(math.fsum(v*v for v in values)/128), retained_min=min(values), retained_max=max(values),
                changed_positions=sum(value[i].flat[p] != kept[i].flat[p] for p in positions),
                retained_delta_rms=math.sqrt(math.fsum((float(value[i].flat[p])-float(kept[i].flat[p]))**2 for p in positions)/128)))
        geometry[body] = {k: [r[k] for r in rows] for k in rows[0]}
    return geometry


def observer(trace, rep):
    assert trace.shape[1] == 4*rep
    rows = []
    for i in range(4*rep):
        sc = trace[:, i, :4]
        ties = abs(sc-sc.max(axis=1)[:, None]) <= 1e-12
        p = ties/ties.sum(axis=1)[:, None]
        m = i//rep
        labels = (m, (m+1) % 4, (m-1) % 4)
        rows.append(np.column_stack([*(sc[:, k] for k in labels), *(p[:, k] for k in labels), p[:, labels[1]]-p[:, labels[2]]]))
    return np.stack(rows, axis=1)


def rng_digest(tissue, phase, rep, draws, read=False):
    rng = readout.seeded(tissue, phase) if read else common.seeded(tissue, phase)
    for _ in range(draws):
        rng.standard_normal((rep, 16, 16))
    return canonical_digest(rng.bit_generator.state)


def check_calibration(original, output, tissue, cfg=RCFG):
    assert tissue in (*TISSUES, *DISPOSABLES)
    saved = json.loads((output/"calibration.json").read_text())
    assert saved["tissue"] == tissue
    positive = readout.check_calibration(output, saved, cfg)
    for name in ("positive", "reader_off"):
        exact(common.arrays(output/f"calibration_{name}.npz"), common.arrays(original/f"calibration_{name}.npz"))
    return dict(tissue=tissue, passes=True, positive_accuracy=positive, historical_calibration_anchors=2)


def check_writing(original, output, tissue, cfg=CFG):
    assert tissue in (*TISSUES, *DISPOSABLES)
    cfg = json.loads(json.dumps(cfg))
    saved = json.loads((output/"writing.json").read_text())
    common.close(saved["config"], cfg)
    assert saved["tissue"] == tissue and saved["passes"] is True
    assert saved["parent_origin"] == "retained_D079_parent"
    assert saved["four_crossover_replays"] is True and saved["twelve_writer_off_aliases"] is True
    legacy = json.loads((original/"writing.json").read_text())
    assert legacy["tissue"] == tissue and legacy["passes"] is True
    assert legacy["parent_origin"] == "fresh_source_preparation" and legacy["source_prepare_anchor"] is True
    common.close(legacy["config"], cfg)
    local = dict(cfg)
    local["times"] = tuple(local["times"])
    ctx = source.context(tissue, source.Config(**local))
    common.close(saved["tissue_config"], json.loads(json.dumps(asdict(ctx["tissue"]))))
    before, parent, boundary = (common.arrays(output/f"{name}.npz") for name in ("before", "parent", "boundary"))
    # Retained parents, not new training. Match all source state exactly.
    for name, value in (("before", before), ("parent", parent), ("boundary", boundary)):
        exact(value, common.arrays(original/f"{name}.npz"))
    common.close(saved["tissue_config"], legacy["tissue_config"])
    assert common.state_digest(parent) == saved["source_parent_sha256"] == legacy["source_parent_sha256"]
    native = np.ascontiguousarray(boundary["native_theta"])
    np.testing.assert_array_equal(native, ctx["native"])
    assert hashlib.sha256(f"{native.dtype}:{native.shape}:".encode()+native.tobytes()).hexdigest() == saved["source_native_sha256"] == legacy["source_native_sha256"]
    fresh = common.check_boundary(parent, boundary, tissue, cfg, saved["tissue_config"])
    damaged, realized = ctx["api"]["mix_theta"](parent["theta"], cfg["damage"], common.seeded(tissue, "damage"), cfg["norm"])
    np.testing.assert_array_equal(boundary["damaged_theta"], damaged)
    np.testing.assert_allclose(realized, cfg["damage"], rtol=0., atol=1e-12)
    assert set(boundary) == {f"kept_{k}" for k in common.KEYS} | {"scrambled_V", "fresh", "damaged_theta", "codes", "native_theta"}
    bodies = common.arrays(output/"bodies.npz")
    common.close(saved["geometry"], check_bodies(boundary, bodies, tissue, cfg["replicates"]))
    assert all(set(saved[k]) == set(RECOVERIES) for k in ("initial_hashes", "recovery", "recovery_rng_final"))
    expected_rng = rng_digest(tissue, "recovery", cfg["replicates"], cfg["sweeps"])
    raws = {}
    for arm in RECOVERIES:
        raw = common.arrays(output/f"recovery_{arm}.npz")
        raws[arm] = raw
        keys = {f"s{s}_{k}" for s in cfg["times"] for k in common.KEYS} | {
            "fixed_reader", "body_trace", "reference_trace", "theta_trace", "target_trace", "projection_scale", "target_energy", "theta_target_cross"}
        assert set(raw) == keys and all(v.dtype == np.float64 and np.isfinite(v).all() for v in raw.values())
        v = bodies[f"{arm.split('_')[0]}_V"]
        initial = dict(V=v, ema=v, R=np.zeros_like(v), theta=damaged)
        assert common.state_digest(initial) == saved["initial_hashes"][arm]
        np.testing.assert_array_equal(raw["fixed_reader"], native if arm.split("_")[1] == "native" else damaged)
        common.check_recovery(raw, initial, parent, fresh, dict(write=arm not in OFF, hold=False), cfg, saved["recovery"][arm])
        assert saved["recovery_rng_final"][arm] == expected_rng
    for arm in previous.RECOVERIES:
        exact(raws[arm], common.arrays(original/f"recovery_{arm}.npz"))
        assert saved["recovery_rng_final"][arm] == legacy["recovery_rng_final"][arm]
    for arm in OFF:
        for key in ("body_trace", "reference_trace", *(f"s{s}_{k}" for s in cfg["times"] for k in ("V", "ema", "R"))):
            np.testing.assert_array_equal(raws[arm][key], raws[arm[:-4]][key])
    data = common.arrays(output/"writing.npz")
    assert set(data) == {"curves", "strata"}
    assert data["curves"].shape == (14, cfg["sweeps"]+1, 3, 7) and data["strata"].shape == (14, len(cfg["times"]), 4, 3, 7)
    assert all(v.dtype == np.float64 and np.isfinite(v).all() for v in data.values())
    assert set(saved["arms"]) == set(MAIN)
    rep = cfg["replicates"]
    for i, arm in enumerate(MAIN):
        assert set(saved["arms"][arm]) == {str(s) for s in cfg["times"]}
        for f, key in enumerate(("body_trace", "reference_trace", "theta_trace")):
            values = observer(raws[arm][key], rep)
            np.testing.assert_allclose(data["curves"][i, :, f], sum(values[:, w] for w in range(4*rep))/(4*rep), rtol=0., atol=1e-11)
            for q, s in enumerate(cfg["times"]):
                groups = [sum(values[s, w] for w in range(g*rep, (g+1)*rep))/rep for g in range(4)]
                np.testing.assert_allclose(data["strata"][i, q, :, f], groups, rtol=0., atol=1e-11)
                common.close(saved["arms"][arm][str(s)][FIELDS[f]], dict(mean=dict(zip(METRICS, data["curves"][i, s, f].tolist())),
                    messages=[dict(zip(METRICS, g.tolist())) for g in groups]))
    return dict(tissue=tissue, passes=True, retained_parent_matched=True, transplanted_records=6*4*rep,
                body_variants_checked=7, recovery_arms=26, writer_off_aliases=12, recorded_batch_steps=26*cfg["sweeps"],
                historical_recovery_anchors=18, crossover_records=2*4*rep)


def target_values(raw, cfg):
    rows = {name: [] for name in FUNCTIONAL}
    for i, probabilities in enumerate(raw["probabilities"]):
        label = i//(cfg["parents"]*cfg["draws"])
        own, forward, reverse = [float(probabilities[k]) for k in (label, (label+1) % 4, (label-1) % 4)]
        for name, value in zip(FUNCTIONAL, (own, forward, reverse, forward-reverse)):
            rows[name].append(value)
    return {k: np.asarray(v).reshape(4*cfg["parents"], cfg["draws"]) for k, v in rows.items()}


def extra(raw, cfg):
    values = target_values(raw, cfg)
    result = {m: math.fsum(v.ravel())/v.size for m, v in values.items()}
    result["message_means"] = {m: [math.fsum(g)/len(g) for g in v.reshape(4, -1)] for m, v in values.items()}
    result["targets"] = {}
    for name in ("own", "forward", "reverse"):
        v = values[f"{name}_accuracy"]
        means = [math.fsum(row)/len(row) for row in v]
        variances = [math.fsum((x-m)**2 for x in row)/len(row) for row, m in zip(v, means)]
        avg = math.fsum(means)/len(means)
        result["targets"][name] = dict(record_accuracy=means, record_within_variance=variances,
            within_variance=math.fsum(variances)/len(variances), between_variance=math.fsum((m-avg)**2 for m in means)/len(means),
            total_variance=math.fsum((x-avg)**2 for x in v.ravel())/v.size,
            always_correct=sum(all(x == 1. for x in row) for row in v), always_incorrect=sum(all(x == 0. for x in row) for row in v),
            varying=sum(min(row) != max(row) for row in v))
    return result


def check_readout(original, output, tissue, wcfg=CFG, cfg=RCFG):
    assert tissue in (*TISSUES, *DISPOSABLES)
    saved = json.loads((output/"readout.json").read_text())
    assert saved["tissue"] == tissue and saved["passes"] is True
    assert saved["four_crossover_replays"] is True and saved["theta_unchanged_R_zero"] is True
    assert saved["packet_origin"] == "current_D080_writing_retained_D079_parent"
    common.close(saved["config"], json.loads(json.dumps(cfg)))
    assert all(set(saved[k]) == set(ARMS) for k in ("arms", "packet_hashes", "expanded_hashes"))
    packets = common.arrays(output/"packets.npz")
    assert set(packets) == set(PACKETS)
    for a in PACKETS:
        path, key = (output/f"recovery_{a}.npz", f"s{wcfg['sweeps']}_theta") if a in MAIN else (output/"parent.npz", "theta") if a == "parent" else (output/"boundary.npz", "damaged_theta")
        np.testing.assert_array_equal(packets[a], common.arrays(path)[key])
        assert packets[a].dtype == np.float64 and packets[a].shape == (4*cfg["parents"], 16, 16) and np.isfinite(packets[a]).all()
    for a in OFF:
        np.testing.assert_array_equal(common.arrays(output/f"recovery_{a}.npz")[f"s{wcfg['sweeps']}_theta"], packets["damaged"])
    rep = cfg["parents"]
    packets["wrong_forward"] = np.concatenate((packets["forwardvalues_native"][rep:], packets["forwardvalues_native"][:rep]))
    packets["wrong_reverse"] = np.concatenate((packets["reversevalues_native"][-rep:], packets["reversevalues_native"][:-rep]))
    packets["reader_off"] = packets["forwardvalues_native"]
    raw = {}
    for a in ARMS:
        raw[a] = common.arrays(output/f"readout_{a}.npz")
        assert all(v.dtype == np.float64 and np.isfinite(v).all() for v in raw[a].values())
        assert hashlib.sha256(packets[a].tobytes()).hexdigest() == saved["packet_hashes"][a]
        assert hashlib.sha256(np.repeat(packets[a], cfg["draws"], axis=0).tobytes()).hexdigest() == saved["expanded_hashes"][a]
        metrics = readout.check_readout(raw[a], packets[a], tissue, cfg, off=a == "reader_off") | extra(raw[a], cfg)
        common.close(saved["arms"][a], metrics)
    for arm in previous.PACKETS:
        exact(raw[arm], common.arrays(original/f"readout_{arm}.npz"))
    legacy = json.loads((original/"readout.json").read_text())
    for key in ("rng_final", "birth_rng_final"):
        assert saved[key] == legacy[key]
    assert saved["rng_final"] == rng_digest(tissue, "assay", rep*cfg["draws"], cfg["sweeps"], read=True)
    assert saved["birth_rng_final"] == rng_digest(tissue, "assay_birth", rep*cfg["draws"], 1, read=True)
    off, shift = common.arrays(output/"calibration_reader_off.npz"), rep*cfg["draws"]
    for s in cfg["times"]:
        for key in readout.KEYS:
            f, r = raw["forwardvalues_native"][f"s{s}_{key}"], raw["reversevalues_native"][f"s{s}_{key}"]
            np.testing.assert_array_equal(raw["wrong_forward"][f"s{s}_{key}"], np.concatenate((f[shift:], f[:shift])))
            np.testing.assert_array_equal(raw["wrong_reverse"][f"s{s}_{key}"], np.concatenate((r[-shift:], r[:-shift])))
        for key in ("V", "ema", "R"):
            np.testing.assert_array_equal(raw["reader_off"][f"s{s}_{key}"], off[f"s{s}_{key}"])
    assert all(saved["arms"]["reader_off"][m] == .25 for m in FUNCTIONAL[:3])
    values = {a: target_values(r, cfg) for a, r in raw.items()}
    paired = {}
    for name, terms in TERMS.items():
        paired[name] = {}
        for m in FUNCTIONAL:
            d = sum(w*values[a][m] for a, w in terms).ravel()
            paired[name][m] = dict(positive=sum(x > 1e-12 for x in d)/len(d), negative=sum(x < -1e-12 for x in d)/len(d),
                                   tied=sum(abs(x) <= 1e-12 for x in d)/len(d))
    common.close(saved["paired"], paired)
    return dict(tissue=tissue, passes=True, scored_arms=19, scored_readout_lives=19*4*rep*cfg["draws"],
        wrong_permutations=2, disabled_calibration_alias=True, packet_origins_checked=16, writer_off_packet_aliases=12,
        historical_readout_anchors=12)


def summary(delta, groups):
    d, g = np.array(delta), np.array(groups)
    return dict(tissue_differences=d.tolist(), mean=(sum(d)/len(d)).tolist(), minimum=np.minimum.reduce(d).tolist(), maximum=np.maximum.reduce(d).tolist(),
        positive=sum((v > 1e-12).astype(int) for v in d).tolist(), negative=sum((v < -1e-12).astype(int) for v in d).tolist(),
        tied=sum((abs(v) <= 1e-12).astype(int) for v in d).tolist(), message_mean=(sum(g)/len(g)).tolist())


def check_pool(rows, saved):
    assert [r["tissue"] for r in rows] == list(TISSUES)
    assert set(saved) == {"arms", "contrasts", "parent_readability", "parent_readable"}
    n = len(rows)
    common.close(saved["arms"], {a: {m: math.fsum(r["arms"][a][m] for r in rows)/n for m in FUNCTIONAL} for a in ARMS})
    parents = [r["arms"]["parent"]["accuracy"] for r in rows]
    common.close(saved["parent_readability"], parents)
    assert saved["parent_readable"] is (min(parents) > .25 and math.fsum(parents)/n >= .75)
    assert set(saved["contrasts"]) == set(TERMS)
    for name, terms in TERMS.items():
        assert set(saved["contrasts"][name]) == set(FUNCTIONAL)
        for metric in FUNCTIONAL:
            d = [sum(w*r["arms"][a][metric] for a, w in terms) for r in rows]
            g = [[sum(w*r["arms"][a]["message_means"][metric][m] for a, w in terms) for m in range(4)] for r in rows]
            common.close(saved["contrasts"][name][metric], summary(d, g))
    return True


def check_writing_pool(rows, saved, cfg=CFG):
    assert [r["tissue"] for r in rows] == list(TISSUES)
    assert set(saved) == {"arm_means", "contrasts"} and set(saved["contrasts"]) == set(TERMS)
    arms = [[[[math.fsum(r["arms"][a][str(s)][f]["mean"][m] for r in rows)/len(rows) for m in METRICS]
               for f in FIELDS] for s in cfg["times"]] for a in MAIN]
    common.close(saved["arm_means"], arms)
    for name, terms in TERMS.items():
        d = [[[[sum(w*r["arms"][a][str(s)][f]["mean"][m] for a, w in terms) for m in METRICS]
                for f in FIELDS] for s in cfg["times"]] for r in rows]
        g = [[[[[sum(w*r["arms"][a][str(s)][f]["messages"][q][m] for a, w in terms) for m in METRICS]
                 for f in FIELDS] for q in range(4)] for s in cfg["times"]] for r in rows]
        common.close(saved["contrasts"][name], summary(d, g))
    return True
