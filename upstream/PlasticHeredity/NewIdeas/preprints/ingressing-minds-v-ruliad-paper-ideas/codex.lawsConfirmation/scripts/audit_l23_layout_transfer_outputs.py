"""Independent D082 layout instruments, source replay and scoring checks."""

from dataclasses import asdict
import hashlib
import json
from pathlib import Path

import numpy as np

from laws_confirmation import l23_composition_budget as old
from laws_confirmation.io import canonical_digest

reference = old.checker()
close, arrays, api, GivenNoise, check_hashes = reference.close, reference.arrays, reference.api, reference.GivenNoise, reference.check_hashes
TISSUES, DISPOSABLES = tuple(range(31016, 31032)), (402085, 402086)
LAYOUTS = ("left_right", "above_below", "checker4")
PAIRS, NORMS, BUDGETS, READERS = reference.PAIRS, reference.NORMS, reference.BUDGETS, reference.READERS
MEASURED, GROUPS, CASES, CAL_CASES, CFG = reference.MEASURED, reference.GROUPS, reference.CASES, reference.CAL_CASES, reference.CFG
METRICS = (*reference.METRICS, "own_centered_alignment")
terms = reference.terms


def rng(index, phase):
    payload = f"l23-layout-transfer-v1:{index}:{phase}".encode()
    return np.random.default_rng(int.from_bytes(hashlib.sha256(payload).digest()[:16], "little"))


def expected_maps():
    out = np.empty((3, 256), dtype=np.int64)
    for r in range(16):
        for c in range(16):
            out[0, 16*r+c] = 16*r+c
            out[1, 16*r+c] = 16*(15-c)+r
            ty, tx = r//4, c//4
            source_column = 4*(2*((ty+tx) % 2)+tx//2)+c % 4
            out[2, 16*r+c] = 16*r+source_column
    return out


def remap(value, mapping):
    return np.take(value.reshape(-1, 256), mapping, axis=1).reshape(value.shape)


def check_instruments(inst, index):
    assert set(inst) == {"forms", "left", "targets", "target_means", "permutations", "packets", "layout_maps"}
    reference.check_instruments({k: v for k, v in inst.items() if k != "layout_maps"}, index)
    assert inst["layout_maps"].dtype.kind in "iu"
    np.testing.assert_array_equal(inst["layout_maps"], expected_maps())
    edges = []
    for g, mapping in enumerate(inst["layout_maps"]):
        np.testing.assert_array_equal(np.sort(mapping), np.arange(256))
        mask = remap(inst["left"], mapping)
        assert mask.sum() == 128
        edges.append(int(sum(np.sum(mask != np.roll(mask, -1, axis=axis)) for axis in (0, 1))))
        forms, targets, packets = [remap(inst[k], mapping) for k in ("forms", "targets", "packets")]
        np.testing.assert_array_equal(targets.mean(axis=(-2, -1)), inst["target_means"])
        for name, value in (("forms", forms), ("targets", targets), ("packets", packets)):
            for selected, original in ((mask, inst["left"]), (~mask, ~inst["left"])):
                np.testing.assert_array_equal(np.sort(value[..., selected], axis=-1), np.sort(inst[name][..., original], axis=-1))
        if g == 1:
            np.testing.assert_array_equal(mask, np.indices((16, 16))[0] < 8)
        if g == 2:
            rr, cc = np.indices((16, 16))
            np.testing.assert_array_equal(mask, (rr//4+cc//4) % 2 == 0)
    assert edges == [32, 32, 128]
    return edges


def scores_of(v, forms, mask):
    scores = np.empty((*v.shape[:-2], 2, 4))
    for h, selected in enumerate((mask, ~mask)):
        ix = np.flatnonzero(selected)
        pixels = v.reshape(*v.shape[:-2], 256)[..., ix]
        for i in range(4):
            scores[..., h, i] = ((pixels > 0) == (forms[i].ravel()[ix] > 0)).sum(axis=-1)/128
    ties = abs(scores-scores.max(axis=-1, keepdims=True)) <= 1e-12
    return scores, ties/ties.sum(axis=-1, keepdims=True)


def alignment_of(v, forms, mask):
    out = np.empty((*v.shape[:-2], 2, 4))
    for h, selected in enumerate((mask, ~mask)):
        ix = np.flatnonzero(selected)
        pixels = v.reshape(*v.shape[:-2], 256)[..., ix]
        z = pixels-pixels.sum(axis=-1, keepdims=True)/128
        for i in range(4):
            f = forms[i].ravel()[ix]
            f = f-f.sum()/128
            denominator = np.linalg.norm(z, axis=-1)*np.linalg.norm(f)
            out[..., h, i] = np.divide((z*f).sum(axis=-1), denominator,
                out=np.zeros_like(denominator), where=denominator > 0)
    return out


def check_raw(raw, inst, index, geometry, norm_index, cases, cfg):
    draws, steps, times = cfg["draws"], cfg["sweeps"], cfg["times"]
    assert isinstance(draws, int) and draws > 0 and isinstance(steps, int) and steps > 0
    assert times[0] == 0 and times[-1] == steps and sorted(set(times)) == list(times)
    expected_keys = {"theta", "case_ids", "offsets", "birth_noise", "mean", "rms", "boundary_fraction", "scores", "probabilities", "alignment"}
    expected_keys |= {f"s{t}_{f}" for t in times for f in ("V", "ema", "R")}
    assert set(raw) == expected_keys
    shape = (len(cases), draws, 16, 16)
    ids = np.array([(PAIRS.index(p), BUDGETS.index(b), READERS.index(r)) for p, b, r in cases])
    mapping = inst["layout_maps"][geometry]
    theta = remap(inst["packets"][norm_index, ids[:, 0], ids[:, 2]], mapping)
    offsets = np.array([inst["target_means"][j]*(0, 1, -1)[b] for j, b, _ in ids])
    assert raw["case_ids"].dtype.kind in "iu"
    np.testing.assert_array_equal(raw["case_ids"], ids)
    np.testing.assert_array_equal(raw["theta"], theta)
    np.testing.assert_array_equal(raw["offsets"], offsets)
    generator = rng(index, "expression")
    z = .2*generator.standard_normal((draws, 16, 16))
    z -= z.mean(axis=(-2, -1), keepdims=True)
    z = remap(z, mapping)
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
            random_field = remap(generator.standard_normal((draws, 16, 16)), mapping)
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
    forms, mask = remap(inst["forms"], mapping), remap(inst["left"], mapping)
    scores, probs = scores_of(v, forms, mask)
    np.testing.assert_allclose(raw["alignment"], alignment_of(v, forms, mask), rtol=0, atol=1e-12)
    np.testing.assert_array_equal(raw["scores"], scores)
    np.testing.assert_array_equal(raw["probabilities"], probs)
    return canonical_digest(generator.bit_generator.state)


def paired_metrics(scores, probabilities, alignment, pair):
    first = reference.paired_metrics(scores, probabilities, pair)
    extra = [(row[0, ord(pair[0])-65]+row[1, ord(pair[1])-65])/2 for row in alignment]
    return np.column_stack((first, extra))


def recompute_metrics(raw):
    result = []
    for pair in PAIRS:
        budgets = []
        for budget in BUDGETS:
            real = []
            for reader in READERS:
                j = CASES.index((pair, budget, reader))
                real.append(paired_metrics(raw["scores"][j], raw["probabilities"][j], raw["alignment"][j], pair))
            l, r = (CASES.index((pair, budget, name)) for name in ("left_single", "right_single"))
            fields = [np.stack((raw[k][l, :, 0], raw[k][r, :, 1]), axis=1)
                      for k in ("scores", "probabilities", "alignment")]
            real.append(paired_metrics(*fields, pair))
            budgets.append(real)
        result.append(budgets)
    return np.array(result)


def check_calibration(directory, index, cfg=CFG):
    assert index in (*TISSUES, *DISPOSABLES)
    saved = json.loads((directory/"calibration.json").read_text())
    close(saved["config"], cfg)
    assert saved["tissue"] == index and saved["passes"] is True
    inst = arrays(directory/"instruments.npz")
    check_instruments(inst, index)
    accuracy, previous = [], None
    for n in range(2):
        raw = arrays(directory/f"calibration_{n}.npz")
        assert check_raw(raw, inst, index, 0, n, CAL_CASES, cfg) == saved["rng_final"][n]
        acc = [paired_metrics(raw["scores"][j], raw["probabilities"][j], raw["alignment"][j], p)[:, 0].mean()
               for j, (p, _, _) in enumerate(CAL_CASES)]
        accuracy.append(np.array(acc).reshape(2, 2).mean(axis=0).tolist())
        if previous is not None:
            same_cases(raw, [1, 3], previous, [1, 3], cfg)
        previous = raw
    close(accuracy, saved["accuracy"])
    return dict(passes=True, tissue=index, norms=2, replayed_expression_lives=8*cfg["draws"], accuracy=accuracy)


def check_isometry(raw, original, mapping, cfg):
    for key in ("theta", "birth_noise"):
        np.testing.assert_array_equal(raw[key], remap(original[key], mapping))
    for key in ("scores", "probabilities", "offsets", "case_ids"):
        np.testing.assert_array_equal(raw[key], original[key])
    np.testing.assert_allclose(raw["alignment"], original["alignment"], rtol=0, atol=1e-12)
    maximum = 0.
    for t in cfg["times"]:
        for field in ("V", "ema", "R"):
            key = f"s{t}_{field}"
            wanted = remap(original[key], mapping)
            np.testing.assert_allclose(raw[key], wanted, rtol=0, atol=1e-10)
            maximum = max(maximum, float(np.max(abs(raw[key]-wanted))))
    for key in ("mean", "rms"):
        np.testing.assert_allclose(raw[key], original[key], rtol=0, atol=1e-10)
    return maximum


def check_panel(directory, index, cfg=CFG):
    assert index in (*TISSUES, *DISPOSABLES)
    saved = json.loads((directory/"panel.json").read_text())
    close(saved["config"], cfg)
    assert saved["tissue"] == index and saved["passes"] is True
    assert np.asarray(saved["rng_final"]).shape == (3, 2)
    inst = arrays(directory/"instruments.npz")
    edges = check_instruments(inst, index)
    canonical, isometry_max = {}, 0.
    for g in range(3):
        previous = None
        for n in range(2):
            raw = arrays(directory/f"panel_{g}_{n}.npz")
            assert check_raw(raw, inst, index, g, n, CASES, cfg) == saved["rng_final"][g][n]
            assert saved["rng_final"][g][n] == saved["rng_final"][0][0]
            np.testing.assert_allclose(saved["metrics"][g][n], recompute_metrics(raw), rtol=0, atol=1e-12)
            if g == 0:
                canonical[n] = raw
                calibration = arrays(directory/f"calibration_{n}.npz")
                for j, case in enumerate(CAL_CASES):
                    same_cases(raw, CASES.index(case), calibration, j, cfg)
            elif g == 1:
                isometry_max = max(isometry_max, check_isometry(raw, canonical[n], inst["layout_maps"][1], cfg))
            for pair in ("AB", "BA"):
                for reader in READERS:
                    for budget in ("matched", "opposite"):
                        same_cases(raw, CASES.index((pair, budget, reader)), raw, CASES.index((pair, "neutral", reader)), cfg)
            for pair in PAIRS:
                same_cases(raw, CASES.index((pair, "neutral", "wrong")), raw,
                           CASES.index((pair[::-1], "neutral", "normalized")), cfg)
            if previous is not None:
                ix = [i for i, case in enumerate(CASES) if case[2] == "off"]
                same_cases(raw, ix, previous, ix, cfg)
            previous = raw
    return dict(passes=True, tissue=index, layouts=3, all_pairs=12, scored_cases=1512,
        replayed_expression_lives=1512*cfg["draws"], calibration_anchors=8,
        balanced_budget_aliases=168, wrong_neutral_aliases=72, off_norm_aliases=108,
        interface_edges=edges, isometry_max_abs_state_difference=isometry_max,
        isometry_probability_arrays_equal=True)


def same_cases(a, ia, b, ib, cfg):
    for key in ("theta", "offsets", "scores", "probabilities", "alignment", *(f"s{t}_{f}" for t in cfg["times"] for f in ("V", "ema", "R"))):
        np.testing.assert_array_equal(a[key][ia], b[key][ib])
    for key in ("mean", "rms", "boundary_fraction"):
        np.testing.assert_array_equal(a[key][:, ia], b[key][:, ib])


def check_one(rows, saved):
    data = np.asarray([r["metrics"] for r in rows])
    assert data.shape[:5] == (len(rows), 2, 12, 3, 8) and data.shape[-1] == 6 and np.isfinite(data).all()
    assert len({r["tissue"] for r in rows}) == len(rows)
    np.testing.assert_allclose(saved["arm_means"], data.mean(axis=0).mean(axis=4), rtol=0., atol=1e-12)
    assert set(saved) == {"arm_means", "contrasts"} and set(saved["contrasts"]) == set(terms())
    for name, weights in terms().items():
        delta = np.zeros((len(rows), 2, 12, data.shape[5], 6))
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


def check_pool(rows, saved):
    data = np.asarray([r["metrics"] for r in rows])
    assert data.shape[:6] == (len(rows), 3, 2, 12, 3, 8) and data.shape[-1] == 6
    assert set(saved) == {"by_layout", "minus_left_right"}
    assert set(saved["by_layout"]) == set(LAYOUTS)
    assert set(saved["minus_left_right"]) == set(LAYOUTS[1:])
    for g, layout in enumerate(LAYOUTS):
        entries = [dict(tissue=r["tissue"], metrics=data[t, g].tolist()) for t, r in enumerate(rows)]
        assert check_one(entries, saved["by_layout"][layout])
        if g:
            differences = [dict(tissue=r["tissue"], metrics=(data[t, g]-data[t, 0]).tolist()) for t, r in enumerate(rows)]
            assert check_one(differences, saved["minus_left_right"][layout])
    return True
