"""D081: express every source pair, crossing instruction with initial bulk mean."""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, dataclass
import hashlib
import importlib.util
import itertools
import json
import multiprocessing
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import traceback

import numpy as np

from . import l17_r_channel as base
from .io import (atomic_text, canonical_digest, environment_manifest, external_root,
                 require_beneath, sha256_file, utc_now, write_hash_manifest)

RUN_ID = "l23_composition_budget_v1_attempt1"
TAG = "l23-composition-budget-v1"
TISSUES, DISPOSABLES, WORKERS = tuple(range(31000, 31016)), (402083, 402084), 4
PAIRS = tuple("".join(p) for p in itertools.permutations("ABCD", 2))
NORMS, BUDGETS = (.15, .30), ("neutral", "matched", "opposite")
READERS = ("splice", "normalized", "left_single", "right_single", "scrambled", "wrong", "off")
MEASURED = (*READERS, "isolated_halves")
METRICS = ("half_accuracy", "joint_accuracy", "own_fidelity", "own_margin", "other_fidelity")
CAL_CASES = tuple((p, "neutral", r) for p in ("AB", "BA") for r in ("normalized", "off"))
CASES = tuple(itertools.product(PAIRS, BUDGETS, READERS))
GROUPS = {"all": PAIRS, "eligible": ("AB", "BA"), "excluded": tuple(p for p in PAIRS if p not in ("AB", "BA"))}


@dataclass(frozen=True)
class Config:
    draws: int = 8
    sweeps: int = 300
    times: tuple = (0, 1, 50, 150, 300)


CONFIG = Config()


def contrast_terms():
    terms = {}
    for b in BUDGETS:
        for name, control in (("expression_gain", "off"), ("organization", "scrambled"),
                              ("correct_address", "wrong"), ("normalization", "splice"),
                              ("composition_cost", "isolated_halves")):
            terms[f"{name}_{b}"] = ((b, "normalized", 1.), (b, control, -1.))
    for r in READERS:
        terms[f"budget_gain_{r}"] = (("matched", r, 1.), ("neutral", r, -1.))
        terms[f"budget_direction_{r}"] = (("matched", r, 1.), ("opposite", r, -1.))
    for kind in ("budget_gain", "budget_direction"):
        for control in ("off", "scrambled"):
            terms[f"{kind}_specificity_{control}"] = (*terms[f"{kind}_normalized"],
                *((b, r, -w) for b, r, w in terms[f"{kind}_{control}"]))
    return terms


TERMS = contrast_terms()
FOCAL = ("expression_gain_neutral", "expression_gain_matched", "budget_gain_specificity_off", "budget_direction_specificity_off")


def api():
    a = base.source_api()
    for package in ("writable_landlord", "alphabet"):
        p = str(base.sources_root()/package/"src")
        if p not in sys.path:
            sys.path.insert(0, p)
    from alphabet.config import AlphabetConfig
    from alphabet.pipeline import express, write_form
    from contract_bridge.artifacts import seed_rng
    from writable_landlord.pipeline import project_theta
    return a | locals()


def checker():
    p = Path(__file__).resolve().parents[2]/"scripts/audit_l23_composition_budget_outputs.py"
    spec = importlib.util.spec_from_file_location("d081_checker", p)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def strict_json(path, value, root):
    atomic_text(path, json.dumps(value, sort_keys=True, indent=2, allow_nan=False)+"\n", root)


def seeded(tissue, phase):
    seed = int.from_bytes(hashlib.sha256(f"{TAG}:{tissue}:{phase}".encode()).digest()[:16], "little")
    return np.random.default_rng(seed)


def context(index, cfg=CONFIG):
    a = api()
    rc = a["RewriteConfig"]()
    tissue = a["tissue_config"](index, rc.coupling_band, rc)
    forms = np.stack([a["launch_pattern"](i, tissue) for i in (1, 3, 5, 7)])
    mask = np.zeros((16, 16), bool)
    mask[:, :8] = True
    return dict(index=index, config=cfg, api=a, tissue=tissue, forms=forms, mask=mask,
                ladder=a["LadderConfig"](), bp=a["BlueprintConfig"]())


def instruments(ctx):
    forms, mask = ctx["forms"], ctx["mask"]
    shuffled = np.array([seeded(ctx["index"], "shuffle:"+p).permutation(256) for p in PAIRS])
    targets = np.array([np.where(mask, forms[ord(p[0])-65], forms[ord(p[1])-65]) for p in PAIRS])
    packets = []
    for norm in NORMS:
        whole = np.array([ctx["api"]["write_form"](f, norm, 1.5) for f in forms])
        local = []
        for j, pair in enumerate(PAIRS):
            x, y = (ord(c)-65 for c in pair)
            splice = np.where(mask, whole[x], whole[y])
            normalized = ctx["api"]["project_theta"](splice[None], norm)[0]
            wrong = ctx["api"]["project_theta"](np.where(mask, whole[y], whole[x])[None], norm)[0]
            local.append(np.stack((splice, normalized, whole[x], whole[y],
                                  normalized.ravel()[shuffled[j]].reshape(16, 16), wrong, np.zeros((16, 16)))))
        packets.append(local)
    return dict(forms=forms, left=mask, targets=targets, target_means=targets.mean(axis=(1, 2)),
                permutations=shuffled, packets=np.array(packets))


def case_inputs(inst, norm_index, cases):
    theta, means, ids = [], [], []
    for p, b, r in cases:
        j, k, l = PAIRS.index(p), BUDGETS.index(b), READERS.index(r)
        theta.append(inst["packets"][norm_index, j, l])
        means.append(inst["target_means"][j]*(0, 1, -1)[k])
        ids.append((j, k, l))
    return np.array(theta), np.array(means), np.array(ids, dtype=np.int64)


class CoupledNoise:
    def __init__(self, generator, draws):
        self.generator, self.draws = generator, draws

    def standard_normal(self, shape):
        assert len(shape) == 4 and tuple(shape[1:]) == (self.draws, 16, 16)
        return np.broadcast_to(self.generator.standard_normal((self.draws, 16, 16)), shape)


def half_scores(v, forms, left):
    return np.stack([np.stack([((v > 0) == (f > 0))[..., m].mean(axis=-1)
                               for f in forms], axis=-1) for m in (left, ~left)], axis=-2)


def probabilities(scores):
    ties = np.isclose(scores, scores.max(axis=-1, keepdims=True), rtol=0., atol=1e-12)
    return ties/ties.sum(axis=-1, keepdims=True)


def simulate(ctx, inst, norm_index, cases):
    cfg = ctx["config"]
    theta, means, ids = case_inputs(inst, norm_index, cases)
    rng = seeded(ctx["index"], "expression")
    noise = .2*rng.standard_normal((cfg.draws, 16, 16))
    noise -= noise.mean(axis=(-2, -1), keepdims=True)
    v = noise[None]+means[:, None, None, None]
    ema, ref = v.copy(), v.copy()
    draws = CoupledNoise(rng, cfg.draws)
    raw = dict(theta=theta, case_ids=ids, offsets=means, birth_noise=noise)
    traces = {k: [] for k in ("mean", "rms", "boundary_fraction")}
    for t in range(cfg.sweeps+1):
        if t:
            v, ema, ref = ctx["api"]["blueprint_step"](v, ema, ref, theta[:, None],
                ctx["tissue"], ctx["ladder"], ctx["bp"], "T", draws, c_m=0.)
        if t in cfg.times:
            raw.update({f"s{t}_{k}": x.copy() for k, x in (("V", v), ("ema", ema), ("R", ref))})
        traces["mean"].append(v.mean(axis=(-2, -1)))
        traces["rms"].append(np.sqrt((v*v).mean(axis=(-2, -1))))
        traces["boundary_fraction"].append((abs(v) == 2.).mean(axis=(-2, -1)))
    raw.update({k: np.array(x) for k, x in traces.items()})
    raw["scores"] = half_scores(v, inst["forms"], inst["left"])
    raw["probabilities"] = probabilities(raw["scores"])
    return raw, canonical_digest(rng.bit_generator.state)


def metrics(scores, probs, pair):
    own, other, margin, fidelity = [], [], [], []
    for h, c in enumerate(pair):
        i, j = ord(c)-65, ord(pair[1-h])-65
        own.append(probs[..., h, i])
        other.append(scores[..., h, j])
        fidelity.append(scores[..., h, i])
        margin.append(scores[..., h, i]-np.delete(scores[..., h, :], i, axis=-1).max(axis=-1))
    own, other, margin, fidelity = [np.stack(x, axis=-1) for x in (own, other, margin, fidelity)]
    return np.stack((own.mean(axis=-1), own.prod(axis=-1), fidelity.mean(axis=-1),
                     margin.mean(axis=-1), other.mean(axis=-1)), axis=-1)


def panel_metrics(raw):
    scores = raw["scores"].reshape(12, 3, 7, -1, 2, 4)
    prob = raw["probabilities"].reshape(scores.shape)
    result = []
    for j, pair in enumerate(PAIRS):
        local = []
        for b in range(3):
            real = metrics(scores[j, b], prob[j, b], pair)
            isolated_scores = np.stack((scores[j, b, 2, :, 0], scores[j, b, 3, :, 1]), axis=1)
            isolated_prob = np.stack((prob[j, b, 2, :, 0], prob[j, b, 3, :, 1]), axis=1)
            local.append(np.concatenate((real, metrics(isolated_scores, isolated_prob, pair)[None]), axis=0))
        result.append(local)
    return np.array(result)


def qualification(rows):
    values = np.array([r["accuracy"] for r in rows])  # tissue, norm, normalized/off
    return bool(np.all(values[:, :, 0] > .25) and np.all(values[:, :, 0].mean(axis=0) >= .75)
                and np.all((values[:, :, 0]-values[:, :, 1]).mean(axis=0) > 0))


def execute_cell(root, index, stage, directory, cfg=CONFIG):
    if index not in (*TISSUES, *DISPOSABLES):
        raise ValueError("undeclared tissue")
    require_beneath(directory, root).mkdir(parents=True, exist_ok=True)
    ctx = context(index, cfg)
    inst = instruments(ctx)
    check = checker()
    if stage == "calibration":
        base.atomic_npz(directory/"instruments.npz", inst, root)
        accuracy, endpoints = [], []
        for n in range(2):
            raw, digest = simulate(ctx, inst, n, CAL_CASES)
            base.atomic_npz(directory/f"calibration_{n}.npz", raw, root)
            accu = [metrics(raw["scores"][j], raw["probabilities"][j], p)[:, 0].mean() for j, (p, _, _) in enumerate(CAL_CASES)]
            accuracy.append(np.array(accu).reshape(2, 2).mean(axis=0).tolist())
            endpoints.append(digest)
        record = dict(tissue=index, config=asdict(cfg), accuracy=accuracy, rng_final=endpoints, passes=True)
        strict_json(directory/"calibration.json", record, root)
        verified = check.check_calibration(directory, index, asdict(cfg))
    elif stage == "panel":
        arrays = []
        endpoints = []
        for n in range(2):
            raw, digest = simulate(ctx, inst, n, CASES)
            base.atomic_npz(directory/f"panel_{n}.npz", raw, root)
            arrays.append(panel_metrics(raw))
            endpoints.append(digest)
        record = dict(tissue=index, config=asdict(cfg), metrics=np.array(arrays).tolist(), rng_final=endpoints, passes=True)
        strict_json(directory/"panel.json", record, root)
        verified = check.check_panel(directory, index, asdict(cfg))
    else:
        raise ValueError("unknown stage")
    return record, verified


def legacy(root, directory):
    ctx = context(0)
    a, arrays, fits = ctx["api"], {}, []
    for n, norm in enumerate(NORMS):
        scores = []
        for pair in ("AB", "BA"):
            x, y = (ord(c)-65 for c in pair)
            theta = np.where(ctx["mask"], a["write_form"](ctx["forms"][x], norm, 1.5),
                             a["write_form"](ctx["forms"][y], norm, 1.5))
            rng = a["seed_rng"]("alphabet-v1", "comp", norm, *pair)
            v = a["express"](a["AlphabetConfig"](), ctx["tissue"], theta, rng)
            sc = half_scores(v, ctx["forms"], ctx["mask"])
            arrays.update({f"n{n}_{pair}_V": v, f"n{n}_{pair}_theta": theta, f"n{n}_{pair}_scores": sc})
            scores.append(sc.mean(axis=0))
        ys = np.array(scores).ravel()
        design = np.array([[1., float(i == ord(pair[h])-65), float(i == ord(pair[1-h])-65)]
                           for pair in ("AB", "BA") for h in range(2) for i in range(4)])
        beta = np.linalg.lstsq(design, ys, rcond=None)[0]
        residual = float(np.sum((ys-design@beta)**2)/np.sum((ys-ys.mean())**2))
        fits.append(dict(mu=float(beta[0]), a_own=float(beta[1]), b_other=float(beta[2]), residual_share=residual))
    base.atomic_npz(directory/"historical.npz", arrays, root)
    record = dict(passes=True, fits=fits, source_config_digest=a["AlphabetConfig"]().digest())
    strict_json(directory/"historical.json", record, root)
    return record, checker().check_historical(directory)


def distribution(values):
    values = np.asarray(values)
    return dict(mean=float(values.mean()), minimum=float(values.min()), maximum=float(values.max()),
                positive=int((values > 1e-12).sum()), tied=int((abs(values) <= 1e-12).sum()),
                negative=int((values < -1e-12).sum()), tissue_differences=values.tolist())


def pooled(rows):
    data = np.array([r["metrics"] for r in rows])  # tissue,norm,pair,budget,reader,draw,metric
    contrasts = {}
    for name, terms in TERMS.items():
        values = sum(w*data[:, :, :, BUDGETS.index(b), MEASURED.index(r)] for b, r, w in terms)
        by_norm = []
        for n in range(2):
            groups = {}
            for group, pairs in GROUPS.items():
                indices = [PAIRS.index(p) for p in pairs]
                selected = values[:, n, indices]
                groups[group] = {m: distribution(selected[..., k].mean(axis=(1, 2))) |
                    dict(pair_mean=values[:, n, :, :, k].mean(axis=(0, 2)).tolist(),
                         paired_positive=float((selected[..., k] > 1e-12).mean()),
                         paired_tied=float((abs(selected[..., k]) <= 1e-12).mean()),
                         paired_negative=float((selected[..., k] < -1e-12).mean())) for k, m in enumerate(METRICS)}
            by_norm.append(groups)
        contrasts[name] = by_norm
    return dict(arm_means=data.mean(axis=(0, 5)).tolist(), contrasts=contrasts)


def contract():
    return dict(run_id=RUN_ID, law="L23", decision="D081", tissues=list(TISSUES), config=asdict(CONFIG),
        norms=list(NORMS), pairs=list(PAIRS), budgets=list(BUDGETS), readers=list(READERS), measured=list(MEASURED),
        groups=GROUPS, metrics=list(METRICS), contrasts=TERMS, focal=list(FOCAL), focal_group="excluded",
        focal_metric="half_accuracy", workers=4, output_hashes=117, main_lives=64512, calibration_lives=1024,
        historical_lives=16, replay_lives=65552, total_executed_lives=131104, scientific_training_lives=0,
        learned_writing_lives=0, law_verdict_changes=0, known_forms=4, fresh_prototypes=False)


def input_paths(root):
    ws = Path(__file__).resolve().parents[2]
    own = ("src/laws_confirmation/l23_composition_budget.py", "scripts/audit_l23_composition_budget_outputs.py",
        "tests/test_l23_composition_budget.py", "scripts/run_l23_composition_budget.sh", "protocols/L23_COMPOSITION_BUDGET_V1.md",
        "reviews/L23_WORDS_BALANCE_BOOKS_AUDIT_2026-09-03.md", "src/laws_confirmation/l17_r_channel.py",
        "src/laws_confirmation/io.py", "src/laws_confirmation/__init__.py", "pyproject.toml",
        "src/laws_confirmation/l23_audit.py", "src/laws_confirmation/artifact_audit.py",
        "src/laws_confirmation/eca_math.py", "src/laws_confirmation/stats.py")
    paths = [ws/p for p in own]
    for package in (*base.PACKAGES, "writable_landlord", "alphabet"):
        directory = base.sources_root()/package
        paths.extend((directory/"src").rglob("*.py"))
        paths.extend((directory/"tests").rglob("*.py"))
        paths.extend(p for p in (directory/"pyproject.toml", directory/"EXPECTATIONS.md") if p.is_file())
    paths.extend(base.sources_root()/"alphabet"/p for p in ("results/full/work/composition.json", "results/full/alphabet_summary.json"))
    return sorted({p.resolve() for p in paths})


def preflight(root):
    cpus = sorted(os.sched_getaffinity(0))
    if not cpus or len(cpus) > 4:
        raise RuntimeError("at most four logical CPUs required")
    if any(os.environ.get(k) != "1" for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")):
        raise RuntimeError("numerical thread limits must all equal one")
    if shutil.disk_usage(root).free < 4*1024**3:
        raise RuntimeError("external free space is below four GiB")
    return cpus


def timing_path(root):
    return root/"tmp"/f"{RUN_ID}_benchmark.json"


def benchmark(root):
    cpus = preflight(root)
    path = timing_path(root)
    if path.exists():
        raise FileExistsError("benchmark is immutable")
    hashes = {str(p): sha256_file(p) for p in input_paths(root)}
    directory = Path(tempfile.mkdtemp(prefix="l23-composition-budget-benchmark-", dir=root/"tmp"))
    start = time.monotonic()
    for stage in ("calibration", "panel"):
        _, checked = execute_cell(root, DISPOSABLES[1], stage, directory)
        assert checked["passes"] is True
    elapsed = time.monotonic()-start
    assert hashes == {str(p): sha256_file(p) for p in input_paths(root)}
    estimate = 24*elapsed+120
    record = dict(run_id=RUN_ID, completed_utc=utc_now(), passes=True, effects_not_reported=True,
        disposable_tissue=DISPOSABLES[1], directory=str(directory), tissue_seconds=elapsed,
        projected_seconds=estimate, must_detach=estimate > 600, input_sha256=hashes, cpu_affinity=cpus)
    strict_json(path, record, root)
    print(json.dumps({k: v for k, v in record.items() if k != "input_sha256"}, indent=2), flush=True)
    return record


def prepare(root):
    run, out = root/"runs"/RUN_ID, root/"outputs"/RUN_ID
    if run.exists() or out.exists():
        raise FileExistsError("immutable run already exists")
    cpus = preflight(root)
    timing = json.loads(timing_path(root).read_text())
    hashes = {str(p): sha256_file(p) for p in input_paths(root)}
    assert timing["run_id"] == RUN_ID and timing["passes"] is True and timing["effects_not_reported"] is True
    assert timing["disposable_tissue"] == DISPOSABLES[1] and timing["input_sha256"] == hashes
    assert np.isfinite(timing["tissue_seconds"]) and timing["tissue_seconds"] > 0
    assert timing["projected_seconds"] == 24*timing["tissue_seconds"]+120
    assert timing["must_detach"] is (timing["projected_seconds"] > 600)
    hashes[str(timing_path(root))] = sha256_file(timing_path(root))
    manifest = contract() | dict(prepared_utc=utc_now(), input_sha256=hashes, hash_contract=canonical_digest(hashes),
        benchmark=timing, cpu_affinity=cpus, environment=environment_manifest())
    run.mkdir(parents=True)
    out.mkdir(parents=True)
    strict_json(run/"MANIFEST.json", manifest, root)
    write_hash_manifest([Path(p) for p in hashes], out/"input_hashes.sha256", root)
    strict_json(run/"STATUS.json", dict(status="PREPARED", run_id=RUN_ID), root)
    print(json.dumps(dict(status="PREPARED", input_hashes=len(hashes), estimated_seconds=timing["projected_seconds"])), flush=True)
    return manifest


def verify(root):
    run = root/"runs"/RUN_ID
    manifest = json.loads((run/"MANIFEST.json").read_text())
    assert json.loads((run/"STATUS.json").read_text())["status"] == "PREPARED"
    assert not (run/"COMPLETE").exists() and not (run/"FAILED").exists()
    for k, v in contract().items():
        assert canonical_digest(v) == canonical_digest(manifest[k]), k
    hashes = manifest["input_sha256"]
    assert set(hashes) == {str(p) for p in input_paths(root)+[timing_path(root)]}
    assert canonical_digest(hashes) == manifest["hash_contract"]
    assert all(sha256_file(Path(p)) == h for p, h in hashes.items())
    assert manifest["benchmark"] == json.loads(timing_path(root).read_text())
    assert manifest["benchmark"]["must_detach"] is (manifest["benchmark"]["projected_seconds"] > 600)
    return manifest


def detach(root):
    if not (root/"runs"/RUN_ID).exists():
        prepare(root)
    manifest = verify(root)
    run = root/"runs"/RUN_ID
    (run/"LAUNCH.lock").mkdir()
    logs = [root/"logs"/f"{RUN_ID}.{k}.log" for k in ("stdout", "stderr")]
    logs[0].parent.mkdir(exist_ok=True)
    with logs[0].open("xb") as out, logs[1].open("xb") as err:
        child = subprocess.Popen([sys.executable, "-m", "laws_confirmation.l23_composition_budget", "--external-root", str(root), "--run"],
            cwd=Path(__file__).resolve().parents[2], stdin=subprocess.DEVNULL, stdout=out, stderr=err, start_new_session=True)
    record = dict(run_id=RUN_ID, pid=child.pid, launched_utc=utc_now(), polling_owner="user",
        estimated_seconds=manifest["benchmark"]["projected_seconds"], status=str(run/"STATUS.json"),
        stdout_log=str(logs[0]), stderr_log=str(logs[1]))
    strict_json(run/"LAUNCH.json", record, root)
    atomic_text(run/"RUN.pid", f"{child.pid}\n", root)
    print(json.dumps(record, indent=2), flush=True)
    return record  # No wait or polling.


def cells(root, out, stage):
    with ProcessPoolExecutor(max_workers=WORKERS, mp_context=multiprocessing.get_context("spawn")) as pool:
        futures = {pool.submit(execute_cell, root, t, stage, out/f"tissue_{t}"): t for t in TISSUES}
        for future in as_completed(futures):
            yield futures[future], future.result()


def run_study(root):
    manifest = verify(root)
    run, out = root/"runs"/RUN_ID, root/"outputs"/RUN_ID
    if manifest["benchmark"]["must_detach"] and not (run/"LAUNCH.lock").is_dir():
        raise RuntimeError("detached execution required above ten minutes")
    (run/"EXECUTION.lock").mkdir()
    start = time.monotonic()
    try:
        preflight(root)
        strict_json(run/"STATUS.json", dict(status="RUNNING", stage="historical", run_id=RUN_ID, updated_utc=utc_now()), root)
        historical, historical_check = legacy(root, out)
        values, checks = {}, {}
        for stage in ("calibration", "panel"):
            values[stage], checks[stage] = {}, {}
            strict_json(run/"STATUS.json", dict(status="RUNNING", stage=stage, checked_tissues=0, updated_utc=utc_now(), run_id=RUN_ID), root)
            for t, (record, check) in cells(root, out, stage):
                assert record["tissue"] == check["tissue"] == t and record["passes"] is True and check["passes"] is True
                values[stage][t], checks[stage][t] = record, check
                strict_json(run/"STATUS.json", dict(status="RUNNING", stage=stage, checked_tissues=len(checks[stage]), updated_utc=utc_now(), run_id=RUN_ID), root)
                print(f"D081 {stage} and saved-data replay verified: tissue {t}", flush=True)
            assert sorted(values[stage]) == list(TISSUES)
            if stage == "calibration" and not qualification([values[stage][t] for t in TISSUES]):
                raise RuntimeError("positive-control calibration failed; full pair panel not permitted")
        rows = [values["panel"][t] for t in TISSUES]
        summary = pooled(rows)
        assert checker().check_pool(rows, summary)
        assert all(sha256_file(Path(p)) == h for p, h in manifest["input_sha256"].items())
        analysis = contract() | dict(completed_cleanly=True, verified_saved_analysis=True, calibration_qualified=True,
            historical=historical, calibrations=[values["calibration"][t] for t in TISSUES], results=rows, pooled=summary)
        strict_json(out/"analysis.json", analysis, root)
        strict_json(out/"verification.json", dict(passes=True, historical=historical_check, pooled_verified=True,
            checks={s: [checks[s][t] for t in TISSUES] for s in checks}, checked_utc=utc_now()), root)
        published = json.loads((out/"analysis.json").read_text())
        assert checker().check_pool(published["results"], published["pooled"])
        paths = [out/p for p in ("historical.npz", "historical.json", "input_hashes.sha256", "analysis.json", "verification.json")]
        paths.extend(p for t in TISSUES for p in (out/f"tissue_{t}").iterdir())
        assert len(paths) == 117
        write_hash_manifest(paths, out/"output_hashes.sha256", root)
        assert checker().check_hashes(out/"output_hashes.sha256") == 117
        status = dict(status="COMPLETE", run_id=RUN_ID, completed_utc=utc_now(), elapsed_seconds=time.monotonic()-start,
            completed_cleanly=True, verified_saved_analysis=True, checked_tissues=16, scored_expression_lives=64512,
            new_training_lives=0, learned_writing_lives=0)
        strict_json(run/"STATUS.json", status, root)
        atomic_text(run/"COMPLETE", status["completed_utc"]+"\n", root)
        print(json.dumps(status, indent=2), flush=True)
        return 0
    except Exception as error:
        status = dict(status="FAILED", run_id=RUN_ID, failed_utc=utc_now(), error=str(error), traceback=traceback.format_exc())
        strict_json(run/"STATUS.json", status, root)
        atomic_text(run/"FAILED", status["failed_utc"]+"\n", root)
        raise


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--external-root", required=True)
    g = p.add_mutually_exclusive_group(required=True)
    for op in ("benchmark", "prepare", "detach", "run"):
        g.add_argument(f"--{op}", action="store_true")
    args = p.parse_args()
    root = external_root(args.external_root)
    if args.benchmark:
        benchmark(root)
    elif args.prepare:
        prepare(root)
    elif args.detach:
        detach(root)
    else:
        return run_study(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
