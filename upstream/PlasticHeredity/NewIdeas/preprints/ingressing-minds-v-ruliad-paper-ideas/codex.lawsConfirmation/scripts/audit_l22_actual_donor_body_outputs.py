"""Independent D078 transplantation, writer recurrence and packet-reading checks."""

import hashlib
import importlib.util
import json
import math
from pathlib import Path

import numpy as np


def load(name):
    spec = importlib.util.spec_from_file_location(f"d078_{name}",Path(__file__).with_name(f"{name}.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


previous = load("audit_l22_residual_record_readout_outputs")
fixed = load("audit_l22_fixed_reader_intervention_outputs")
common, readout, runtime = previous.common, previous.readout, previous.runtime
extra, donors, exact = previous.extra, previous.donors, previous.exact
TISSUES = tuple(range(30040,30056))
CFG = dict(replicates=4,settle=120,imprint=1000,sweeps=1000,times=[0,1,50,250,500,1000],norm=.3,lam=.001,damage=.3)
RCFG = dict(parents=4,draws=16,sweeps=1000,times=[0,1,1000])
BODIES = ("kept","scrambled","ranked","actual","donorshuffled")
MAIN = ("kept_damaged","kept_native","scrambled_damaged","scrambled_native","ranked_damaged","ranked_native",
        "actual_damaged","actual_native","donorshuffled_damaged","donorshuffled_native")
OFF = ("actual_damaged_off","actual_native_off","donorshuffled_damaged_off","donorshuffled_native_off")
RECOVERIES = (*MAIN,*OFF)
PACKETS, ARMS = (*MAIN,"parent","damaged"),(*MAIN,"parent","damaged","wrong","reader_off")
RECOVERY_ANCHORS = dict(kept_damaged="kept_damaged",kept_native="kept_native",scrambled_damaged="scrambled_damaged",
                        scrambled_native="scrambled_native",ranked_damaged="donor_damaged",ranked_native="donor_native")
ANCHORS = dict(kept_damaged=("ancestor","kept_fixed"),scrambled_damaged=("previous","scrambled_damaged"),
               scrambled_native=("previous","scrambled_native"),ranked_damaged=("previous","donor_damaged"),
               ranked_native=("previous","donor_native"),parent=("previous","parent"),damaged=("previous","damaged"))
FIELDS, METRICS = fixed.FIELDS, fixed.METRICS
TERMS = {f"{left}_minus_{right}_{reader}": ((f"{left}_{reader}",1),(f"{right}_{reader}",-1))
         for left,right in (("actual","kept"),("actual","ranked"),("actual","donorshuffled"),
                            ("actual","scrambled"),("donorshuffled","scrambled")) for reader in ("damaged","native")}
TERMS.update(actual_specific_reader_interaction=(("actual_native",1),("donorshuffled_native",-1),
                                                ("actual_damaged",-1),("donorshuffled_damaged",1)))
TERMS.update({f"{b}_native_minus_damaged": ((f"{b}_native",1),(f"{b}_damaged",-1)) for b in ("actual","donorshuffled")})


def check_bodies(boundary,ranked,bodies,tissue,rep=4):
    kept,fresh = boundary["kept_V"],boundary["fresh"]
    assert kept.dtype == np.float64 and fresh.dtype == bool and kept.shape == fresh.shape == (4*rep,16,16)
    assert set(bodies) == {f"{b}_V" for b in BODIES} | {"donor_indices","permutations"}
    original_rank = previous.prior.rank_body(kept,fresh,rep)
    exact(ranked,original_rank)
    assert bodies["donor_indices"].dtype.kind in "iu" and bodies["permutations"].dtype.kind in "iu"
    assert bodies["donor_indices"].shape == (4*rep,) and bodies["permutations"].shape == (rep,128)
    seed = int.from_bytes(hashlib.sha256(f"l22-source-recovery-v1:{tissue}:shuffle".encode()).digest()[:16],"little")
    rng = np.random.default_rng(seed)
    permutations = np.array([rng.permutation(128) for _ in range(rep)])
    np.testing.assert_array_equal(bodies["permutations"],permutations)
    expected = {f"{b}_V":kept.copy() for b in BODIES}
    expected["ranked_V"] = original_rank["donor_V"]
    for i in range(4*rep):
        j = ((i//rep+1)%4)*rep+i%rep
        assert bodies["donor_indices"][i] == j
        np.testing.assert_array_equal(fresh[i],fresh[j])
        positions = [k for k,is_fresh in enumerate(fresh[i].flat) if not is_fresh]
        assert len(positions) == 128
        for k,pos in enumerate(positions):
            shifted = positions[int(permutations[i%rep,k])]
            expected["scrambled_V"][i].flat[pos] = kept[i].flat[shifted]
            expected["actual_V"][i].flat[pos] = kept[j].flat[pos]
            expected["donorshuffled_V"][i].flat[pos] = kept[j].flat[shifted]
    np.testing.assert_array_equal(expected["scrambled_V"],boundary["scrambled_V"])
    geometry = {}
    for b in BODIES:
        value = bodies[f"{b}_V"]
        assert value.dtype == np.float64 and np.isfinite(value).all()
        np.testing.assert_array_equal(value,expected[f"{b}_V"])
        metrics = {k:[] for k in ("retained_mean","retained_std","retained_rms","retained_min","retained_max","changed_positions","retained_delta_rms")}
        for i in range(4*rep):
            positions = [k for k,is_fresh in enumerate(fresh[i].flat) if not is_fresh]
            values = [float(value[i].flat[k]) for k in positions]
            mean = math.fsum(values)/128
            row = dict(retained_mean=mean,retained_std=math.sqrt(math.fsum((v-mean)**2 for v in values)/128),
                       retained_rms=math.sqrt(math.fsum(v*v for v in values)/128),retained_min=min(values),retained_max=max(values),
                       changed_positions=sum(value[i].flat[k] != kept[i].flat[k] for k in positions),
                       retained_delta_rms=math.sqrt(math.fsum((float(value[i].flat[k])-float(kept[i].flat[k]))**2 for k in positions)/128))
            for key,v in row.items():
                metrics[key].append(v)
        geometry[b] = metrics
    return geometry


def check_calibration(original,output,tissue,cfg=RCFG):
    assert tissue in TISSUES
    saved = json.loads((output/"calibration.json").read_text())
    assert saved["tissue"] == tissue
    value = readout.check_calibration(output,saved,cfg)
    common.close(saved,json.loads((original/"calibration.json").read_text()))
    for name in ("positive","reader_off"):
        exact(common.arrays(output/f"calibration_{name}.npz"),common.arrays(original/f"calibration_{name}.npz"))
    return dict(tissue=tissue,passes=True,positive_accuracy=value,historical_calibration_anchors=2)


def check_writing(original,writer,output,tissue,cfg=CFG):
    assert tissue in TISSUES
    cfg = json.loads(json.dumps(cfg))
    saved = json.loads((output/"writing.json").read_text())
    assert saved["tissue"] == tissue and saved["passes"] is True
    assert saved["two_actual_replays"] is True and saved["four_writer_off_aliases"] is True
    common.close(saved["config"],cfg)
    parent = common.arrays(original/"writing/parent.npz")
    boundary = common.arrays(original/"writing/boundary.npz")
    ranked = common.arrays(original/"intervention/bodies.npz")
    bodies = common.arrays(output/"bodies.npz")
    metadata = json.loads((original/"writing/experiment.json").read_text())
    assert metadata["tissue"] == tissue and metadata["passes"] is True and all(v is True for v in metadata["gates"].values())
    common.close(metadata["config"],cfg)
    assert common.state_digest(parent) == metadata["source_parent_sha256"] == saved["source_parent_sha256"]
    native = np.ascontiguousarray(boundary["native_theta"])
    digest = hashlib.sha256(f"{native.dtype}:{native.shape}:".encode()+native.tobytes()).hexdigest()
    assert digest == metadata["source_native_sha256"] == saved["source_native_sha256"]
    common.close(saved["geometry"],check_bodies(boundary,ranked,bodies,tissue,cfg["replicates"]))
    assert all(set(saved[k]) == set(RECOVERIES) for k in ("recovery","initial_hashes","recovery_rng_final"))
    raws = {}
    for arm in RECOVERIES:
        raw = common.arrays(output/f"recovery_{arm}.npz")
        raws[arm] = raw
        v = bodies[f"{arm.split('_')[0]}_V"]
        initial = dict(V=v,ema=v,R=np.zeros_like(v),theta=boundary["damaged_theta"])
        assert common.state_digest(initial) == saved["initial_hashes"][arm]
        keys = {f"s{s}_{k}" for s in cfg["times"] for k in common.KEYS} | {
            "fixed_reader","body_trace","reference_trace","theta_trace","target_trace","projection_scale","target_energy","theta_target_cross"}
        assert set(raw) == keys and all(v.dtype == np.float64 and np.isfinite(v).all() for v in raw.values())
        reader = native if arm.split("_")[1] == "native" else boundary["damaged_theta"]
        np.testing.assert_array_equal(raw["fixed_reader"],reader)
        common.check_recovery(raw,initial,parent,boundary["fresh"],dict(write=arm not in OFF,hold=False),cfg,saved["recovery"][arm])
        assert saved["recovery_rng_final"][arm] == metadata["recovery_rng_final"]
    for arm,old in RECOVERY_ANCHORS.items():
        exact(raws[arm],common.arrays(writer/f"recovery_{old}.npz"))
    for arm in OFF:
        for key in ("body_trace","reference_trace",*(f"s{s}_{k}" for s in cfg["times"] for k in ("V","ema","R"))):
            np.testing.assert_array_equal(raws[arm][key],raws[arm[:-4]][key])
    data = common.arrays(output/"writing.npz")
    assert set(data) == {"curves","strata"}
    assert data["curves"].shape == (10,cfg["sweeps"]+1,3,5) and data["strata"].shape == (10,len(cfg["times"]),4,3,5)
    assert all(v.dtype == np.float64 and np.isfinite(v).all() for v in data.values())
    assert set(saved["arms"]) == set(MAIN)
    for i,arm in enumerate(MAIN):
        assert set(saved["arms"][arm]) == {str(s) for s in cfg["times"]}
        for f,key in enumerate(("body_trace","reference_trace","theta_trace")):
            values = fixed.diagnostic.observer(raws[arm][key])
            np.testing.assert_allclose(data["curves"][i,:,f],sum(values[:,w] for w in range(16))/16,rtol=0.,atol=1e-11)
            for q,s in enumerate(cfg["times"]):
                groups = [sum(values[s,w] for w in range(4*g,4*g+4))/4 for g in range(4)]
                np.testing.assert_allclose(data["strata"][i,q,:,f],groups,rtol=0.,atol=1e-11)
                common.close(saved["arms"][arm][str(s)][FIELDS[f]],dict(mean=dict(zip(METRICS,data["curves"][i,s,f].tolist())),
                    messages=[dict(zip(METRICS,g.tolist())) for g in groups]))
    return dict(tissue=tissue,passes=True,recovery_arms=14,historical_recovery_anchors=6,writer_off_aliases=4,
                recorded_batch_steps=14*cfg["sweeps"],transplanted_records=16,body_variants_checked=5)


def check_readout(original,previous,output,tissue,wcfg=CFG,cfg=RCFG):
    assert tissue in TISSUES
    cfg = json.loads(json.dumps(cfg))
    saved = json.loads((output/"readout.json").read_text())
    assert saved["tissue"] == tissue and saved["passes"] is True
    assert saved["two_new_packet_replays"] is True and saved["theta_unchanged_R_zero"] is True
    assert saved["packet_origin"] == "current_D078_writing_and_D074_anchors"
    common.close(saved["config"],cfg)
    assert all(set(saved[k]) == set(ARMS) for k in ("arms","packet_hashes","expanded_hashes"))
    packets = common.arrays(output/"packets.npz")
    assert set(packets) == set(PACKETS)
    for arm in PACKETS:
        path,key = ((output/f"recovery_{arm}.npz",f"s{wcfg['sweeps']}_theta") if arm in MAIN else
                    (original/"writing/parent.npz","theta") if arm == "parent" else
                    (original/"writing/boundary.npz","damaged_theta"))
        np.testing.assert_array_equal(packets[arm],common.arrays(path)[key])
        assert packets[arm].dtype == np.float64 and packets[arm].shape == (16,16,16) and np.isfinite(packets[arm]).all()
    for arm in OFF:
        np.testing.assert_array_equal(common.arrays(output/f"recovery_{arm}.npz")[f"s{wcfg['sweeps']}_theta"],packets["damaged"])
    packets["wrong"] = np.concatenate((packets["actual_native"][4:], packets["actual_native"][:4]))
    packets["reader_off"] = packets["actual_native"]
    raw, metrics = {}, {}
    for arm in ARMS:
        raw[arm] = common.arrays(output/f"readout_{arm}.npz")
        assert all(a.dtype == np.float64 and np.isfinite(a).all() for a in raw[arm].values())
        assert hashlib.sha256(packets[arm].tobytes()).hexdigest() == saved["packet_hashes"][arm]
        assert hashlib.sha256(np.repeat(packets[arm], cfg["draws"], axis=0).tobytes()).hexdigest() == saved["expanded_hashes"][arm]
        metrics[arm] = readout.check_readout(raw[arm], packets[arm], tissue, cfg, off=arm == "reader_off") | extra(raw[arm], cfg)
        common.close(saved["arms"][arm], metrics[arm])
    for arm,(folder,name) in ANCHORS.items():
        path = original/"readout" if folder == "ancestor" else previous
        exact(raw[arm],common.arrays(path/f"readout_{name}.npz"))
    # Historical native readouts pin both random streams in addition to the snapshots.
    historical = json.loads((previous/"experiment.json").read_text())
    assert historical["tissue"] == tissue and historical["passes"] is True
    for key in ("rng_final", "birth_rng_final"):
        assert saved[key] == historical[key]
    off = common.arrays(output/"calibration_reader_off.npz")
    shift = 4*cfg["draws"]
    for s in cfg["times"]:
        for key in readout.KEYS:
            v = raw["actual_native"][f"s{s}_{key}"]
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
    return dict(tissue=tissue, passes=True, scored_arms=14, scored_readout_lives=14*16*cfg["draws"], historical_readout_anchors=7,
                wrong_permutation=True, disabled_calibration_alias=True, packet_origins_checked=12, writer_off_packet_aliases=4)


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


def check_writing_pool(rows,saved,cfg=CFG):
    assert [r["tissue"] for r in rows] == list(TISSUES)
    assert set(saved) == {"arm_means","contrasts"} and set(saved["contrasts"]) == set(TERMS)
    mean = lambda xs: math.fsum(xs)/16
    arms = [[[[mean([r["arms"][a][str(s)][f]["mean"][m] for r in rows]) for m in METRICS]
              for f in FIELDS] for s in cfg["times"]] for a in MAIN]
    common.close(saved["arm_means"],arms)
    for name,terms in TERMS.items():
        delta = np.array([[[[sum(w*r["arms"][a][str(s)][f]["mean"][m] for a,w in terms)
                            for m in METRICS] for f in FIELDS] for s in cfg["times"]] for r in rows])
        group = np.array([[[[[sum(w*r["arms"][a][str(s)][f]["messages"][g][m] for a,w in terms)
                             for m in METRICS] for f in FIELDS] for g in range(4)] for s in cfg["times"]] for r in rows])
        expected = dict(tissue_differences=delta.tolist(),mean=(sum(delta)/16).tolist(),
            minimum=np.minimum.reduce(delta).tolist(),maximum=np.maximum.reduce(delta).tolist(),
            positive=sum((d>1e-12).astype(int) for d in delta).tolist(),
            negative=sum((d< -1e-12).astype(int) for d in delta).tolist(),
            tied=sum((abs(d)<=1e-12).astype(int) for d in delta).tolist(),message_mean=(sum(group)/16).tolist())
        common.close(saved["contrasts"][name],expected)
    return True
