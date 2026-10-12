"""Independent D077 packet-only provenance, functional scores and contrasts."""

import hashlib
import importlib.util
import json
import math
from pathlib import Path

import numpy as np

spec = importlib.util.spec_from_file_location("d077_frozen_body_source_checker", Path(__file__).with_name("audit_l22_body_source_outputs.py"))
prior = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prior)
common, readout, runtime = prior.common, prior.readout, prior.runtime
TISSUES = tuple(range(30040, 30056))
CFG = dict(parents=4, draws=16, sweeps=1000, times=[0, 1, 1000])
MAIN = ("donor_native", "scrambled_native", "donor_damaged", "scrambled_damaged")
PACKETS = (*MAIN, "parent", "damaged")
ARMS = (*PACKETS, "wrong", "reader_off")
ANCHORS = {"donor_damaged": "donor_fixed", "scrambled_damaged": "scrambled_fixed", "parent": "parent", "damaged": "damaged"}
TERMS = {
    "donor_minus_scrambled_native": (("donor_native", 1), ("scrambled_native", -1)),
    "donor_minus_scrambled_damaged": (("donor_damaged", 1), ("scrambled_damaged", -1)),
    "donor_specific_reader_interaction": (("donor_native", 1), ("scrambled_native", -1), ("donor_damaged", -1), ("scrambled_damaged", 1)),
    "donor_native_minus_damaged": (("donor_native", 1), ("donor_damaged", -1)),
    "scrambled_native_minus_damaged": (("scrambled_native", 1), ("scrambled_damaged", -1)),
}


def donors(raw, cfg):
    width = cfg["parents"]*cfg["draws"]
    return np.array([float(row[(i//width+1) % 4]) for i, row in enumerate(raw["probabilities"])]).reshape(4*cfg["parents"], cfg["draws"])


def extra(raw, cfg):
    values, own = donors(raw, cfg), raw["correctness"]
    means = [math.fsum(row)/len(row) for row in values]
    mean = math.fsum(means)/len(means)
    variances = [math.fsum((x-m)**2 for x in row)/len(row) for row, m in zip(values, means)]
    return dict(donor_accuracy=mean, own_minus_donor=math.fsum(own.ravel())/own.size-mean,
                donor_record_accuracy=means, donor_record_within_variance=variances,
                donor_within_variance=math.fsum(variances)/len(variances),
                donor_between_variance=math.fsum((x-mean)**2 for x in means)/len(means),
                donor_total_variance=math.fsum((x-mean)**2 for x in values.ravel())/values.size,
                donor_always_correct=sum(all(x == 1. for x in row) for row in values),
                donor_always_incorrect=sum(all(x == 0. for x in row) for row in values),
                donor_varying=sum(min(row) != max(row) for row in values),
                own_message_accuracy=[math.fsum(row)/len(row) for row in own.reshape(4, -1)],
                donor_message_accuracy=[math.fsum(row)/len(row) for row in values.reshape(4, -1)])


def exact(raw, expected):
    assert set(raw) == set(expected)
    for key in raw:
        assert raw[key].dtype == expected[key].dtype
        np.testing.assert_array_equal(raw[key], expected[key])


def check_calibration(original, output, tissue, cfg=CFG):
    assert tissue in TISSUES
    saved = json.loads((output/"calibration.json").read_text())
    assert saved["tissue"] == tissue
    value = readout.check_calibration(output, saved, cfg)
    common.close(saved, json.loads((original/"calibration.json").read_text()))
    for name in ("positive", "reader_off"):
        exact(common.arrays(output/f"calibration_{name}.npz"), common.arrays(original/f"calibration_{name}.npz"))
    return dict(tissue=tissue, passes=True, positive_accuracy=value, historical_calibration_anchors=2)


def check_cell(written, ancestor, output, tissue, cfg=CFG):
    assert tissue in TISSUES and cfg["parents"] == 4
    saved = json.loads((output/"experiment.json").read_text())
    assert saved["tissue"] == tissue and saved["passes"] is True
    assert saved["packet_origin"] == "frozen_D076_final_theta_and_D074_anchors"
    assert saved["two_new_packet_replays"] is True and saved["theta_unchanged_R_zero"] is True
    common.close(saved["config"], json.loads(json.dumps(cfg)))
    assert all(set(saved[k]) == set(ARMS) for k in ("arms", "packet_hashes", "expanded_hashes"))
    old = json.loads((written/"analysis.json").read_text())
    assert old["tissue"] == tissue and old["passes"] is True
    common.close(old["config"], prior.CFG)
    metadata = json.loads((ancestor/"writing/experiment.json").read_text())
    assert metadata["tissue"] == tissue and metadata["passes"] is True
    packets = common.arrays(output/"packets.npz")
    assert set(packets) == set(PACKETS)
    for arm in PACKETS:
        expected = (common.arrays(written/f"recovery_{arm}.npz")["s1000_theta"] if arm in MAIN else
                    common.arrays(ancestor/"writing/parent.npz")["theta"] if arm == "parent" else
                    common.arrays(ancestor/"writing/boundary.npz")["damaged_theta"])
        np.testing.assert_array_equal(packets[arm], expected)
        assert packets[arm].dtype == np.float64 and packets[arm].shape == (16,16,16) and np.isfinite(packets[arm]).all()
    packets["wrong"] = np.concatenate((packets["donor_native"][4:], packets["donor_native"][:4]))
    packets["reader_off"] = packets["donor_native"]
    raw, metrics = {}, {}
    for arm in ARMS:
        raw[arm] = common.arrays(output/f"readout_{arm}.npz")
        assert all(a.dtype == np.float64 and np.isfinite(a).all() for a in raw[arm].values())
        assert hashlib.sha256(packets[arm].tobytes()).hexdigest() == saved["packet_hashes"][arm]
        assert hashlib.sha256(np.repeat(packets[arm], cfg["draws"], axis=0).tobytes()).hexdigest() == saved["expanded_hashes"][arm]
        metrics[arm] = readout.check_readout(raw[arm], packets[arm], tissue, cfg, off=arm == "reader_off") | extra(raw[arm], cfg)
        common.close(saved["arms"][arm], metrics[arm])
    for arm, name in ANCHORS.items():
        exact(raw[arm], common.arrays(ancestor/"readout"/f"readout_{name}.npz"))
    # Historical native readouts pin both random streams in addition to the snapshots.
    historical = json.loads((ancestor/"readout/experiment.json").read_text())
    assert historical["tissue"] == tissue and historical["passes"] is True
    for key in ("rng_final", "birth_rng_final"):
        assert saved[key] == historical[key]
    off = common.arrays(output/"calibration_reader_off.npz")
    shift = 4*cfg["draws"]
    for s in cfg["times"]:
        for key in readout.KEYS:
            v = raw["donor_native"][f"s{s}_{key}"]
            np.testing.assert_array_equal(raw["wrong"][f"s{s}_{key}"], np.concatenate((v[shift:], v[:shift])))
        for key in ("V", "ema", "R"):
            np.testing.assert_array_equal(raw["reader_off"][f"s{s}_{key}"], off[f"s{s}_{key}"])
    assert metrics["reader_off"]["donor_accuracy"] == .25
    paired = {}
    for label, terms in TERMS.items():
        if len(terms) != 2:
            continue
        paired[label] = {}
        for metric in ("own", "donor"):
            d = sum(w*(raw[a]["correctness"] if metric == "own" else donors(raw[a], cfg)) for a, w in terms)
            paired[label][metric] = dict(improved=sum(x > 0 for x in d.ravel())/d.size,
                                         worsened=sum(x < 0 for x in d.ravel())/d.size, tied=sum(x == 0 for x in d.ravel())/d.size)
    common.close(saved["paired"], paired)
    return dict(tissue=tissue, passes=True, scored_arms=8, scored_readout_lives=8*16*cfg["draws"], historical_readout_anchors=4,
                wrong_permutation=True, disabled_calibration_alias=True, packet_origins_checked=6)


def check_pool(rows, saved):
    assert [r["tissue"] for r in rows] == list(TISSUES)
    assert set(saved) == {"arms", "contrasts", "parent_readability", "parent_readable"}
    mean = lambda values: math.fsum(values)/16
    arms = {a: {m: mean([r["arms"][a][m] for r in rows]) for m in ("accuracy", "donor_accuracy", "own_minus_donor")} for a in ARMS}
    common.close(saved["arms"], arms)
    parents = [r["arms"]["parent"]["accuracy"] for r in rows]
    common.close(saved["parent_readability"], parents)
    assert saved["parent_readable"] is (min(parents) > .25 and mean(parents) >= .75)
    assert set(saved["contrasts"]) == set(TERMS)
    for name, terms in TERMS.items():
        assert set(saved["contrasts"][name]) == {"accuracy", "donor_accuracy"}
        for metric, grouped in (("accuracy", "own_message_accuracy"), ("donor_accuracy", "donor_message_accuracy")):
            delta = [sum(w*r["arms"][a][metric] for a, w in terms) for r in rows]
            groups = [[sum(w*r["arms"][a][grouped][m] for a, w in terms) for m in range(4)] for r in rows]
            expected = dict(tissue_differences=delta, mean=mean(delta), minimum=min(delta), maximum=max(delta),
                positive=sum(v > 1e-12 for v in delta), negative=sum(v < -1e-12 for v in delta),
                tied=sum(abs(v) <= 1e-12 for v in delta), message_mean=[mean([g[m] for g in groups]) for m in range(4)])
            common.close(saved["contrasts"][name][metric], expected)
    return True
