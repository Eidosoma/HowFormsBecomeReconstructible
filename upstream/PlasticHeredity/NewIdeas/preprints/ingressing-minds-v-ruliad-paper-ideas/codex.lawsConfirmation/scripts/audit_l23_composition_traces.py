"""D082 preparation: independently rescore all saved D081 V checkpoints."""

import argparse
import json
from pathlib import Path
import time

import numpy as np

from laws_confirmation import l23_composition_budget as old
from laws_confirmation.io import external_root, sha256_file, utc_now, write_hash_manifest

RUN_ID = "l23_composition_trace_v1_attempt1"
TIMES = (0, 1, 50, 150, 300)


def statistics(v, forms, left):
    scores = old.half_scores(v, forms, left)
    means, alignments = [], []
    for mask in (left, ~left):
        z, f = v[..., mask], forms[:, mask]
        means.append(z.mean(axis=-1))
        z = z-z.mean(axis=-1, keepdims=True)
        f = f-f.mean(axis=-1, keepdims=True)
        dot = np.einsum("...i,fi->...f", z, f)
        scale = np.sqrt((z*z).sum(axis=-1)[..., None]*(f*f).sum(axis=-1))
        alignments.append(np.divide(dot, scale, out=np.zeros_like(dot), where=scale > 0))
    return dict(scores=scores, probabilities=old.probabilities(scores),
                centered_alignment=np.stack(alignments, axis=-2), half_mean=np.stack(means, axis=-1))


def check_statistics(v, forms, saved):
    assert set(saved) == {"scores", "probabilities", "centered_alignment", "half_mean"}
    for h, section in enumerate((slice(0, 8), slice(8, 16))):
        z = v[..., :, section].reshape(*v.shape[:-2], 128)
        mean = z.sum(axis=-1)/128
        np.testing.assert_allclose(saved["half_mean"][..., h], mean, rtol=0, atol=1e-12)
        z = z-mean[..., None]
        expected = []
        for i in range(4):
            f = forms[i, :, section].ravel()
            score = ((v[..., :, section] > 0) == (forms[i, :, section] > 0)).sum(axis=(-2, -1))/128
            np.testing.assert_array_equal(saved["scores"][..., h, i], score)
            f = f-f.sum()/128
            scale = np.linalg.norm(z, axis=-1)*np.linalg.norm(f)
            corr = np.divide((z*f).sum(axis=-1), scale, out=np.zeros_like(scale), where=scale > 0)
            np.testing.assert_allclose(saved["centered_alignment"][..., h, i], corr, rtol=0, atol=1e-12)
            expected.append(score)
        scores = np.stack(expected, axis=-1)
        tied = abs(scores-scores.max(axis=-1, keepdims=True)) <= 1e-12
        np.testing.assert_array_equal(saved["probabilities"][..., h, :], tied/tied.sum(axis=-1, keepdims=True))
    return True


def source_paths(root):
    directory = root/"outputs"/old.RUN_ID
    paths = []
    for name in ("input_hashes.sha256", "output_hashes.sha256"):
        manifest = directory/name
        old.checker().check_hashes(manifest)
        paths += [Path(line.split("  ", 1)[1]) for line in manifest.read_text().splitlines()]
        paths.append(manifest)
    ws = Path(__file__).resolve().parents[1]
    paths += [ws/p for p in ("scripts/audit_l23_composition_traces.py", "tests/test_l23_composition_traces.py",
        "protocols/L23_COMPOSITION_TRACE_AUDIT_V1.md", "reviews/L23_COMPOSITION_BUDGET_2026-09-09.md")]
    paths += [root/"runs"/old.RUN_ID/p for p in ("MANIFEST.json", "STATUS.json", "COMPLETE")]
    return sorted(set(p.resolve() for p in paths))


def aggregate(arrays):
    return {name: value.mean(axis=(0, 6)).tolist() for name, value in arrays.items()}


def run(root):
    old.preflight(root)
    out = root/"outputs"/RUN_ID
    if out.exists():
        raise FileExistsError("trace audit output is immutable")
    start = time.monotonic()
    source = root/"outputs"/old.RUN_ID
    status = json.loads((root/"runs"/old.RUN_ID/"STATUS.json").read_text())
    assert status["status"] == "COMPLETE" and status["verified_saved_analysis"] is True
    paths = source_paths(root)
    hashes = {str(p): sha256_file(p) for p in paths}
    out.mkdir(parents=True)
    data = {k: [] for k in ("scores", "probabilities", "centered_alignment", "half_mean")}
    checks = 0
    for tissue in old.TISSUES:
        d = source/f"tissue_{tissue}"
        with np.load(d/"instruments.npz", allow_pickle=False) as f:
            forms, left = f["forms"], f["left"]
        block = {k: [] for k in data}
        for n in range(2):
            norms = {k: [] for k in data}
            with np.load(d/f"panel_{n}.npz", allow_pickle=False) as f:
                for t in TIMES:
                    v = f[f"s{t}_V"]
                    row = statistics(v, forms, left)
                    assert check_statistics(v, forms, row)
                    checks += 1
                    for key in data:
                        norms[key].append(row[key].reshape(12, 3, 7, 8, *row[key].shape[2:]))
                    if t == 300:
                        for key in ("scores", "probabilities"):
                            np.testing.assert_array_equal(row[key], f[key])
            for key in data:
                block[key].append(np.array(norms[key]))
        for key in data:
            data[key].append(np.array(block[key]))
    data = {k: np.array(v) for k, v in data.items()}
    old.base.atomic_npz(out/"traces.npz", data, root)
    with np.load(out/"traces.npz", allow_pickle=False) as f:
        for key in data:
            np.testing.assert_array_equal(f[key], data[key])
    summary = aggregate(data)
    # Independent two-stage aggregate, preserving tissue/start axes.
    for key, value in data.items():
        np.testing.assert_allclose(summary[key], value.mean(axis=6).mean(axis=0), rtol=0, atol=1e-12)
    analysis = dict(run_id=RUN_ID, decision="D082", completed_utc=utc_now(), passes=True,
        elapsed_seconds=time.monotonic()-start, source_run=old.RUN_ID,
        tissues=list(old.TISSUES), norms=list(old.NORMS), times=list(TIMES), pairs=list(old.PAIRS),
        budgets=list(old.BUDGETS), readers=list(old.READERS),
        array_axes="tissue,norm,time,pair,budget,reader,start,half[,form]", means=summary,
        new_simulation_lives=0, outcome_informed=True, continuous_onset_identified=False)
    old.strict_json(out/"analysis.json", analysis, root)
    assert hashes == {str(p): sha256_file(p) for p in paths}
    old.strict_json(out/"verification.json", dict(passes=True, snapshot_batches=checks,
        endpoint_batches=32, independent_statistics=True, independent_aggregate=True,
        input_hashes=len(paths), input_hashes_unchanged=True), root)
    write_hash_manifest(paths, out/"input_hashes.sha256", root)
    write_hash_manifest([out/p for p in ("traces.npz", "analysis.json", "verification.json", "input_hashes.sha256")], out/"output_hashes.sha256", root)
    assert old.checker().check_hashes(out/"output_hashes.sha256") == 4
    print(json.dumps(dict(run_id=RUN_ID, passes=True, seconds=time.monotonic()-start,
                         input_hashes=len(paths), output_hashes=4, output=str(out)), indent=2), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--external-root", required=True)
    run(external_root(parser.parse_args().external_root))
