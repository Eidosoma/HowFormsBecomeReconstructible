"""Independent D081 instrument, saved-trajectory replay and score checks."""

from dataclasses import asdict
import hashlib
import itertools
import json
from pathlib import Path
import sys

import numpy as np

from laws_confirmation import l17_r_channel as base
from laws_confirmation.io import canonical_digest, sha256_file
from laws_confirmation.l23_audit import launch_pattern as reference_pattern

TISSUES, DISPOSABLES = tuple(range(31000, 31016)), (402083, 402084)
NORMS, BUDGETS = (.15, .30), ("neutral", "matched", "opposite")
PAIRS = tuple(a+b for a in "ABCD" for b in "ABCD" if a != b)
READERS = ("splice", "normalized", "left_single", "right_single", "scrambled", "wrong", "off")
MEASURED = (*READERS, "isolated_halves")
METRICS = ("half_accuracy", "joint_accuracy", "own_fidelity", "own_margin", "other_fidelity")
GROUPS = {"all": PAIRS, "eligible": ("AB", "BA"), "excluded": tuple(p for p in PAIRS if p not in ("AB", "BA"))}
CFG = dict(draws=8, sweeps=300, times=[0, 1, 50, 150, 300])
CASES = tuple(itertools.product(PAIRS, BUDGETS, READERS))
CAL_CASES = tuple((p, "neutral", r) for p in ("AB", "BA") for r in ("normalized", "off"))


def close(a, b):
    if isinstance(a, dict):
        assert isinstance(b, dict) and set(a) == set(b)
        for k in a:
            close(a[k], b[k])
    elif isinstance(a, (tuple, list)):
        assert isinstance(b, (tuple, list)) and len(a) == len(b)
        for x, y in zip(a, b):
            close(x, y)
    elif isinstance(a, bool) or a is None or isinstance(a, str):
        assert type(a) is type(b) and a == b
    else:
        assert np.isfinite(a) and np.isfinite(b) and abs(a-b) <= 1e-12, (a, b)


def arrays(path):
    with np.load(path, allow_pickle=False) as f:
        result = {k: f[k] for k in f.files}
    assert all(v.dtype.kind in "fiub" and np.isfinite(v).all() for v in result.values())
    return result


def api():
    a = base.source_api()
    for name in ("alphabet", "writable_landlord"):
        p = str(base.sources_root()/name/"src")
        if p not in sys.path:
            sys.path.insert(0, p)
    from alphabet.config import AlphabetConfig
    from alphabet.pipeline import express, write_form
    from contract_bridge.artifacts import seed_rng
    return a | locals()


def rng(index, phase):
    payload = f"l23-composition-budget-v1:{index}:{phase}".encode()
    return np.random.default_rng(int.from_bytes(hashlib.sha256(payload).digest()[:16], "little"))


def projection(theta, norm):
    t = theta-theta.mean()
    return t*(norm/max(t.std(), 1e-9))


def check_instruments(saved, index):
    assert set(saved) == {"forms", "left", "targets", "target_means", "permutations", "packets"}
    forms = np.stack([reference_pattern(i) for i in (1, 3, 5, 7)])
    a = api()
    rc = a["RewriteConfig"]()
    tissue = a["tissue_config"](index, rc.coupling_band, rc)
    for i, seed in enumerate((1, 3, 5, 7)):
        np.testing.assert_array_equal(forms[i], a["launch_pattern"](seed, tissue))
    left = np.indices((16, 16))[1] < 8
    assert saved["left"].dtype == bool and saved["forms"].dtype == np.float64
    np.testing.assert_array_equal(saved["left"], left)
    np.testing.assert_array_equal(saved["forms"], forms)
    assert saved["packets"].shape == (2, 12, 7, 16, 16) and saved["packets"].dtype == np.float64
    assert saved["permutations"].shape == (12, 256) and saved["permutations"].dtype.kind in "iu"
    assert saved["targets"].shape == (12, 16, 16) and saved["target_means"].shape == (12,)
    eligible = []
    for j, pair in enumerate(PAIRS):
        x, y = (ord(c)-65 for c in pair)
        target = np.where(left, forms[x], forms[y])
        np.testing.assert_array_equal(saved["targets"][j], target)
        assert saved["target_means"][j] == target.mean()
        if abs(forms[x][left].mean()) < .15 and abs(forms[y][~left].mean()) < .15:
            eligible.append(pair)
        permutation = rng(index, "shuffle:"+pair).permutation(256)
        np.testing.assert_array_equal(saved["permutations"][j], permutation)
        for n, norm in enumerate(NORMS):
            whole = [projection(np.tanh(1.5*f), norm) for f in forms]
            splice = np.where(left, whole[x], whole[y])
            normal = projection(splice, norm)
            expected = (splice, normal, whole[x], whole[y], normal.ravel()[permutation].reshape(16, 16),
                        projection(np.where(left, whole[y], whole[x]), norm), np.zeros((16, 16)))
            for r, value in enumerate(expected):
                np.testing.assert_array_equal(saved["packets"][n, j, r], value)
            np.testing.assert_array_equal(np.sort(normal.ravel()), np.sort(saved["packets"][n, j, 4].ravel()))
            assert abs(normal.mean()) < 1e-12 and abs(normal.std()-norm) < 1e-12
    assert eligible == ["AB", "BA"]
    return tissue, a


def scores_of(v, forms):
    scores = np.empty((*v.shape[:-2], 2, 4))
    for h, sl in enumerate((slice(0, 8), slice(8, 16))):
        for f in range(4):
            scores[..., h, f] = ((v[..., :, sl] > 0) == (forms[f, :, sl] > 0)).sum(axis=(-2, -1))/128
    ties = abs(scores-scores.max(axis=-1, keepdims=True)) <= 1e-12
    return scores, ties/ties.sum(axis=-1, keepdims=True)


class GivenNoise:
    def __init__(self, noise, shape):
        self.noise, self.shape, self.used = noise, shape, 0

    def standard_normal(self, shape):
        assert tuple(shape) == tuple(self.shape) and self.used == 0
        self.used += 1
        return np.broadcast_to(self.noise, shape)


def check_raw(raw, inst, index, norm_index, cases, cfg):
    draws, steps, times = cfg["draws"], cfg["sweeps"], cfg["times"]
    assert isinstance(draws, int) and draws > 0 and isinstance(steps, int) and steps > 0
    assert times[0] == 0 and times[-1] == steps and sorted(set(times)) == list(times)
    expected_keys = {"theta", "case_ids", "offsets", "birth_noise", "mean", "rms", "boundary_fraction", "scores", "probabilities"}
    expected_keys |= {f"s{t}_{f}" for t in times for f in ("V", "ema", "R")}
    assert set(raw) == expected_keys
    shape = (len(cases), draws, 16, 16)
    ids = np.array([(PAIRS.index(p), BUDGETS.index(b), READERS.index(r)) for p, b, r in cases])
    theta = inst["packets"][norm_index, ids[:, 0], ids[:, 2]]
    offsets = np.array([inst["target_means"][j]*(0, 1, -1)[b] for j, b, _ in ids])
    assert raw["case_ids"].dtype.kind in "iu"
    np.testing.assert_array_equal(raw["case_ids"], ids)
    np.testing.assert_array_equal(raw["theta"], theta)
    np.testing.assert_array_equal(raw["offsets"], offsets)
    generator = rng(index, "expression")
    z = .2*generator.standard_normal((draws, 16, 16))
    z -= z.mean(axis=(-2, -1), keepdims=True)
    np.testing.assert_array_equal(raw["birth_noise"], z)
    v = z[None]+offsets[:, None, None, None]
    ema, reference = v.copy(), v.copy()
    a = api()
    rc = a["RewriteConfig"]()
    tissue = a["tissue_config"](index, rc.coupling_band, rc)
    for key in ("mean", "rms", "boundary_fraction"):
        assert raw[key].shape == (steps+1, len(cases), draws)
    for t in range(steps+1):
        if t:
            random_field = generator.standard_normal((draws, 16, 16))
            adapter = GivenNoise(random_field, shape)
            v, ema, reference = a["blueprint_step"](v, ema, reference, theta[:, None], tissue,
                a["LadderConfig"](), a["BlueprintConfig"](), "T", adapter, c_m=0.)
            assert adapter.used == 1
        for k, observed in (("mean", v.mean(axis=(-2, -1))), ("rms", np.sqrt((v*v).mean(axis=(-2, -1)))),
                            ("boundary_fraction", (abs(v) == 2.).mean(axis=(-2, -1)))):
            np.testing.assert_array_equal(raw[k][t], observed)
        if t in times:
            for name, value in (("V", v), ("ema", ema), ("R", reference)):
                assert raw[f"s{t}_{name}"].shape == shape and raw[f"s{t}_{name}"].dtype == np.float64
                np.testing.assert_array_equal(raw[f"s{t}_{name}"], value)
    scores, probs = scores_of(v, inst["forms"])
    np.testing.assert_array_equal(raw["scores"], scores)
    np.testing.assert_array_equal(raw["probabilities"], probs)
    return canonical_digest(generator.bit_generator.state)


def paired_metrics(scores, probabilities, pair):
    result = []
    x, y = ord(pair[0])-65, ord(pair[1])-65
    for sc, pr in zip(scores, probabilities):
        acc = (pr[0, x]+pr[1, y])/2
        joint = pr[0, x]*pr[1, y]
        own = (sc[0, x]+sc[1, y])/2
        margin = (sc[0, x]-max(sc[0, k] for k in range(4) if k != x)
                  + sc[1, y]-max(sc[1, k] for k in range(4) if k != y))/2
        other = (sc[0, y]+sc[1, x])/2
        result.append((acc, joint, own, margin, other))
    return np.array(result)


def recompute_metrics(raw):
    result = []
    for pair in PAIRS:
        local = []
        for budget in BUDGETS:
            real = []
            for reader in READERS:
                j = CASES.index((pair, budget, reader))
                real.append(paired_metrics(raw["scores"][j], raw["probabilities"][j], pair))
            l, r = (CASES.index((pair, budget, name)) for name in ("left_single", "right_single"))
            sc = np.stack((raw["scores"][l, :, 0], raw["scores"][r, :, 1]), axis=1)
            pr = np.stack((raw["probabilities"][l, :, 0], raw["probabilities"][r, :, 1]), axis=1)
            real.append(paired_metrics(sc, pr, pair))
            local.append(real)
        result.append(local)
    return np.array(result)


def same_cases(a, ia, b, ib, cfg):
    for key in ("theta", "offsets", "scores", "probabilities", *(f"s{t}_{f}" for t in cfg["times"] for f in ("V", "ema", "R"))):
        np.testing.assert_array_equal(a[key][ia], b[key][ib])
    for key in ("mean", "rms", "boundary_fraction"):
        np.testing.assert_array_equal(a[key][:, ia], b[key][:, ib])


def check_calibration(directory, index, cfg=CFG):
    assert index in (*TISSUES, *DISPOSABLES)
    saved = json.loads((directory/"calibration.json").read_text())
    close(saved["config"], cfg)
    assert saved["tissue"] == index and saved["passes"] is True
    inst = arrays(directory/"instruments.npz")
    check_instruments(inst, index)
    accuracies, previous = [], None
    for n in range(2):
        raw = arrays(directory/f"calibration_{n}.npz")
        assert check_raw(raw, inst, index, n, CAL_CASES, cfg) == saved["rng_final"][n]
        acc = np.array([paired_metrics(raw["scores"][j], raw["probabilities"][j], p)[:, 0].mean() for j, (p, _, _) in enumerate(CAL_CASES)])
        accuracies.append(acc.reshape(2, 2).mean(axis=0).tolist())
        if previous is not None:
            same_cases(raw, [1, 3], previous, [1, 3], cfg)
        previous = raw
    close(accuracies, saved["accuracy"])
    return dict(passes=True, tissue=index, norms=2, replayed_expression_lives=8*cfg["draws"], accuracy=accuracies)


def check_panel(directory, index, cfg=CFG):
    assert index in (*TISSUES, *DISPOSABLES)
    saved = json.loads((directory/"panel.json").read_text())
    close(saved["config"], cfg)
    assert saved["tissue"] == index and saved["passes"] is True and len(saved["rng_final"]) == 2
    inst = arrays(directory/"instruments.npz")
    check_instruments(inst, index)
    previous = None
    for n in range(2):
        raw = arrays(directory/f"panel_{n}.npz")
        assert check_raw(raw, inst, index, n, CASES, cfg) == saved["rng_final"][n]
        np.testing.assert_allclose(saved["metrics"][n], recompute_metrics(raw), rtol=0., atol=1e-12)
        calibration = arrays(directory/f"calibration_{n}.npz")
        for j, case in enumerate(CAL_CASES):
            same_cases(raw, CASES.index(case), calibration, j, cfg)
        for pair in ("AB", "BA"):
            for reader in READERS:
                for b in ("matched", "opposite"):
                    same_cases(raw, CASES.index((pair, b, reader)), raw, CASES.index((pair, "neutral", reader)), cfg)
        for pair in PAIRS:
            same_cases(raw, CASES.index((pair, "neutral", "wrong")), raw, CASES.index((pair[::-1], "neutral", "normalized")), cfg)
        if previous is not None:
            ix = [i for i, case in enumerate(CASES) if case[2] == "off"]
            same_cases(raw, ix, previous, ix, cfg)
        previous = raw
    return dict(passes=True, tissue=index, all_pairs=12, scored_cases=504, replayed_expression_lives=504*cfg["draws"],
                calibration_anchors=8, balanced_budget_aliases=56, wrong_neutral_aliases=24, off_norm_aliases=36)


def check_historical(directory):
    a = api()
    rc = a["RewriteConfig"]()
    tissue = a["tissue_config"](0, rc.coupling_band, rc)
    forms = np.stack([reference_pattern(i) for i in (1, 3, 5, 7)])
    left = np.indices((16, 16))[1] < 8
    raw = arrays(directory/"historical.npz")
    row = json.loads((directory/"historical.json").read_text())
    assert row["passes"] is True and row["source_config_digest"] == a["AlphabetConfig"]().digest()
    assert set(raw) == {f"n{n}_{p}_{f}" for n in range(2) for p in ("AB", "BA") for f in ("V", "theta", "scores")}
    cache = json.loads((base.sources_root()/"alphabet/results/full/work/composition.json").read_text())
    assert cache["config_digest"] == row["source_config_digest"]
    for n, label in enumerate(("primary", "secondary")):
        y, design = [], []
        for pair in ("AB", "BA"):
            x, z = (ord(c)-65 for c in pair)
            theta = np.where(left, projection(np.tanh(1.5*forms[x]), NORMS[n]), projection(np.tanh(1.5*forms[z]), NORMS[n]))
            np.testing.assert_array_equal(raw[f"n{n}_{pair}_theta"], theta)
            v = a["express"](a["AlphabetConfig"](), tissue, theta, a["seed_rng"]("alphabet-v1", "comp", NORMS[n], *pair))
            np.testing.assert_array_equal(raw[f"n{n}_{pair}_V"], v)
            scores, _ = scores_of(v, forms)
            np.testing.assert_array_equal(raw[f"n{n}_{pair}_scores"], scores)
            means = scores.mean(axis=0)
            for h in range(2):
                own, other = ord(pair[h])-65, ord(pair[1-h])-65
                assert means[h, own] > max(means[h, j] for j in range(4) if j != own)
                for f in range(4):
                    y.append(means[h, f])
                    design.append((1., float(f == own), float(f == other)))
        y, design = np.array(y), np.array(design)
        beta = np.linalg.lstsq(design, y, rcond=None)[0]
        fit = dict(mu=float(beta[0]), a_own=float(beta[1]), b_other=float(beta[2]),
                   residual_share=float(np.square(y-design@beta).sum()/np.square(y-y.mean()).sum()))
        close(fit, row["fits"][n])
        cached = cache["data"][label]["fit"]
        close(fit, {k: cached["interaction_share" if k == "residual_share" else k] for k in fit})
    return dict(passes=True, original_expressions=4, replayed_lives=16, fit_matches_retained=True, discarded_null_recreated=False)


def terms():
    result = {}
    for b in BUDGETS:
        for name, r in zip(("expression_gain", "organization", "correct_address", "normalization", "composition_cost"),
                           ("off", "scrambled", "wrong", "splice", "isolated_halves")):
            result[f"{name}_{b}"] = [(b, "normalized", 1.), (b, r, -1.)]
    for prefix, b in (("budget_gain", "neutral"), ("budget_direction", "opposite")):
        for r in READERS:
            result[f"{prefix}_{r}"] = [("matched", r, 1.), (b, r, -1.)]
        for r in ("off", "scrambled"):
            result[f"{prefix}_specificity_{r}"] = [("matched", "normalized", 1.), (b, "normalized", -1.), ("matched", r, -1.), (b, r, 1.)]
    return result


def check_pool(rows, saved):
    data = np.asarray([r["metrics"] for r in rows])
    assert data.shape[:5] == (len(rows), 2, 12, 3, 8) and data.shape[-1] == 5 and np.isfinite(data).all()
    assert len({r["tissue"] for r in rows}) == len(rows)
    np.testing.assert_allclose(saved["arm_means"], data.mean(axis=0).mean(axis=4), rtol=0., atol=1e-12)
    assert set(saved) == {"arm_means", "contrasts"} and set(saved["contrasts"]) == set(terms())
    for name, weights in terms().items():
        delta = np.zeros((len(rows), 2, 12, data.shape[5], 5))
        for budget, reader, weight in weights:
            delta += weight*data[:, :, :, BUDGETS.index(budget), MEASURED.index(reader)]
        assert len(saved["contrasts"][name]) == 2
        for n in range(2):
            assert set(saved["contrasts"][name][n]) == set(GROUPS)
            for group, pairs in GROUPS.items():
                indices = [PAIRS.index(p) for p in pairs]
                assert set(saved["contrasts"][name][n][group]) == set(METRICS)
                for k, metric in enumerate(METRICS):
                    # Select the metric before the pair array: separating advanced
                    # indices with a slice otherwise moves the pair axis before tissue.
                    selected = delta[:, n, :, :, k][:, indices, :]
                    assert selected.shape == (len(rows), len(indices), data.shape[5])
                    values = selected.mean(axis=(1, 2))
                    expected = dict(mean=float(values.mean()), minimum=float(min(values)), maximum=float(max(values)),
                        positive=int(sum(values > 1e-12)), negative=int(sum(values < -1e-12)), tied=int(sum(abs(values) <= 1e-12)),
                        tissue_differences=values.tolist(), pair_mean=delta[:, n, :, :, k].mean(axis=(0, 2)).tolist(),
                        paired_positive=float(np.mean(selected > 1e-12)), paired_tied=float(np.mean(abs(selected) <= 1e-12)),
                        paired_negative=float(np.mean(selected < -1e-12)))
                    close(expected, saved["contrasts"][name][n][group][metric])
    return True


def check_hashes(path):
    rows = [line.split("  ", 1) for line in path.read_text().splitlines()]
    assert len(rows) == len({p for h, p in rows})
    for h, p in rows:
        assert Path(p).is_absolute() and sha256_file(Path(p)) == h
    return len(rows)
