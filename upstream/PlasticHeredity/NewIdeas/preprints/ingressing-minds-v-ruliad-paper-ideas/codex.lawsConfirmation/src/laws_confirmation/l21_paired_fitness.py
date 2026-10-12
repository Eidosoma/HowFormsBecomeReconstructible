"""D094 paired last-boundary fitness, not evolution.

The separate run harness requires source controls, a test proof, immutable
inputs and disposable timing. Public dynamics entry points enforce the
unchanged external-storage/CPU preflight.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import hashlib
import importlib.util
from itertools import product
import json
from pathlib import Path
import shutil
import sys

import numpy as np

from . import l24_descendant_pilot as source
from .io import canonical_digest, external_root


TAG = "l21-paired-fitness-v1"
RUN_ID = "l21_paired_fitness_v1_attempt1"
TISSUES = tuple(range(41000, 41008))
DISPOSABLE = 504121
RATES = (.001, .2, 1.)
FIELDS = ("V", "ema", "R", "theta")
# Factor order is explicit; zero denotes the intact/on/copied level.
ARMS = tuple(product(("copy", "native"), ("on", "off"), ("copy", "zero")))
METRICS = ("ever_amplitude", "fresh_amplitude", "ever_sign",
           "ever_projection", "whole_amplitude", "active_fraction")
SOURCE_DIGEST = "00591e27961e0153932653bfb3642207f6f21ef77834960d7c20737c9f42b010"
PRIMARY_KEY = 'theta/u=1.0/writer=0/R=0'
BOOTSTRAP_TAG = f'{TAG}:primary-bootstrap'
BOOTSTRAP_DRAWS = 20000
SCORE_SCHEMA = 'l21_paired_fitness_final_scores_v1'
SCIENCE = ("src/laws_confirmation/l21_paired_fitness.py",
           "scripts/audit_l21_paired_fitness_outputs.py",
           "tests/test_l21_paired_fitness.py", "protocols/L21_PAIRED_FITNESS_V1.md")


@dataclass(frozen=True)
class Config:
    replicates: int = 2
    settle: int = 120
    cycles: int = 8
    inter_fission: int = 500
    times: tuple[int, ...] = (0, 1, 50, 250, 500)
    rho: float = .002
    norm: float = .3
    amp_threshold: float = .2

    def __post_init__(self):
        for name in ("replicates", "settle", "cycles", "inter_fission"):
            value = getattr(self, name)
            if type(value) is not int or value < 1:
                raise ValueError(f"positive integer {name} required")
        if self.cycles < 2:
            raise ValueError("need a parent prefix and a final boundary")
        if (not self.times or any(type(t) is not int for t in self.times)
                or tuple(sorted(set(self.times))) != self.times
                or self.times[0] != 0 or self.times[-1] != self.inter_fission):
            raise ValueError("checkpoints must increase from birth to the final update")
        if (self.rho, self.norm, self.amp_threshold) != (.002, .3, .2):
            raise ValueError("native rho, theta norm and amplitude threshold are fixed")


CONFIG = Config()
SHORT = Config(replicates=1, settle=4, cycles=3, inter_fission=8, times=(0, 1, 4, 8))


def contract(cfg=CONFIG):
    return dict(
        stage="PAIRED_FIXED_U_FITNESS",
        run_id=RUN_ID, seed_tag=TAG, config=asdict(cfg), tissues=list(TISSUES),
        disposable=DISPOSABLE, rates=list(RATES), arms=[list(a) for a in ARMS],
        fields=list(FIELDS), metrics=list(METRICS), founder_writing=False,
        common_founder_target=True, reference_refresh=False,
        target_age_fissions=cfg.cycles, target_age_updates=cfg.cycles*cfg.inter_fission,
        parent_prefix_boundaries=cfg.cycles-1, intervened_boundaries=1,
        units=len(TISSUES)*cfg.replicates,
        parent_prefixes=len(TISSUES)*cfg.replicates*len(RATES),
        final_futures=len(TISSUES)*cfg.replicates*len(RATES)*len(ARMS),
        primary=dict(u=1., theta="copy_minus_native", writer="on", R="copy",
                     sweep=cfg.inter_fission, metric="ever_amplitude"),
        source_control=dict(tissue=0, rates=[.001, 1.], replicates=3,
                            known_outcomes=True, paired_across_u=False),
        R_zero_is_not_reader_off=True, V_fragment_inherited=True,
        theta_copy_bytes=16*16*8, R_copy_bytes=16*16*8,
        hard_reset=False, evolutionary_selection=False, target_age_manipulation=False,
        heritable_fraction=False, scientific_pass_threshold=None,
        max_cpus=4, detach_above_seconds=600, automatic_followup=False,
        storage_reserve_bytes=source.RESERVE, storage_allowance_bytes=source.ALLOWANCE,
        main_runner_enabled=True,
        analysis=analysis_contract() if cfg == CONFIG else None,
    )


def analysis_contract():
    return dict(
        endpoint_schema=SCORE_SCHEMA, primary_contrast=PRIMARY_KEY, primary_metric='ever_amplitude',
        primary_sweep=500, target_age_fissions=8, target_age_updates=4000,
        tissue_blocks=8, lives_per_block=2, bootstrap_unit='tissue',
        bootstrap_draws=BOOTSTRAP_DRAWS, bootstrap_tag=BOOTSTRAP_TAG,
        bootstrap_seed=int.from_bytes(hashlib.sha256(BOOTSTRAP_TAG.encode()).digest()[:16], 'little'),
        bootstrap_generator='PCG64', quantiles=[.025, .975], quantile_method='linear',
        secondary_intervals=False, tie_rule='exact_zero', scientific_pass_threshold=None,
        source_controls_in_main_pool=False, incomplete_panels_allowed=False,
        analysis_validation_atol=1e-14,
    )


def resource_report(root):
    root = external_root(root)
    free = shutil.disk_usage(root).free
    minimum = source.RESERVE + source.ALLOWANCE
    return dict(external_root=str(root), free_bytes=free, start_gate_bytes=minimum,
                shortfall_bytes=max(0, minimum-free), storage_allows_start=free >= minimum)


def seed(index, replicate, phase):
    if type(index) is not int or type(replicate) is not int or index < 0 or replicate < 0:
        raise ValueError("nonnegative integer public addresses required")
    return int.from_bytes(hashlib.sha256(f"{TAG}:{index}:{replicate}:{phase}".encode()).digest()[:16], "little")


class SharedNoise:
    """One event stream per tissue/life/phase; rate and arm labels are absent.

    Batch length cannot change stream consumption. Independent lives are
    separate calls, never additional entries in this coupled batch.
    """

    def __init__(self, index, replicate, phase):
        self.generator = np.random.default_rng(seed(index, replicate, phase))

    def standard_normal(self, shape):
        if len(shape) != 3 or shape[0] < 1 or tuple(shape[1:]) != (16, 16):
            raise ValueError("expected a positive batch of 16x16 fields")
        return np.broadcast_to(self.generator.standard_normal((1, 16, 16)), shape)

    def integers(self, low, high, size):
        if type(size) is not int or size < 1:
            raise ValueError("positive integer fission batch required")
        return np.repeat(self.generator.integers(low, high, 1), size)

    def digest(self):
        return canonical_digest(self.generator.bit_generator.state)


def context(index):
    ctx = source.context(index)
    if (ctx['tissue'].height, ctx['tissue'].width) != (16, 16):
        raise ValueError("native 16x16 sheet required")
    if (ctx['bp'].rho, ctx['bp'].c_m) != (.002, .2):
        raise ValueError("native R clock and reader must not change")
    return ctx


def advance(ctx, state, random, rates, cfg=CONFIG):
    """Source physics; theta hold is exact, without repeated projection."""
    if state.ndim != 4 or state.shape[0] != 4 or state.shape[-2:] != (16, 16):
        raise ValueError("state must be field,batch,row,column")
    rates = np.broadcast_to(np.asarray(rates, dtype=float), (state.shape[1],))
    if not np.isfinite(rates).all() or np.any((rates < 0) | (rates > 1)):
        raise ValueError("rates must be finite and in [0,1]")
    v, ema, ref = ctx['api']['blueprint_step'](
        *state[:3], state[3], ctx['tissue'], ctx['ladder'], ctx['bp'], 'T', random)
    theta = state[3].copy()
    enabled = rates > 0
    if enabled.any():
        lam = rates[enabled, None, None]*cfg.rho/2
        theta[enabled] = ctx['api']['project_theta'](
            (1-lam)*theta[enabled]+lam*np.tanh(ref[enabled]), cfg.norm)
    return np.stack((v, ema, ref, theta))


def cut(ctx, state, random):
    v, ref, fresh = ctx['api']['fission_with_mask'](state[0], state[2], ctx['tissue'], random)
    return np.stack((v, v.copy(), ref, state[3].copy())), fresh


def boundary_panel(parent, native):
    """Fork one already-cut parent per u, touching only declared fields.

    Axis order: field, u, arm, row, column. Input arrays are never mutated.
    R-zero is a birth intervention, not disabling subsequent R dynamics.
    """
    if parent.shape != (4, len(RATES), 16, 16) or native.shape != (16, 16):
        raise ValueError("unexpected parent/native dimensions")
    if not np.isfinite(parent).all() or not np.isfinite(native).all():
        raise ValueError("finite boundary fields required")
    panel = np.repeat(parent[:, :, None], len(ARMS), axis=2)
    for arm, (theta, _, ref) in enumerate(ARMS):
        if theta == "native":
            panel[3, :, arm] = native
        if ref == "zero":
            panel[2, :, arm] = 0
    return panel


def scores(v, target, ever, fresh, cfg=CONFIG):
    """Common, intervention-independent masks and one frozen founder target."""
    if v.shape[-2:] != (16, 16) or any(a.shape != (16, 16) for a in (target, ever, fresh)):
        raise ValueError("expected 16x16 score domain")
    if ever.dtype != bool or fresh.dtype != bool or not ever.any() or not fresh.any():
        raise ValueError("nonempty Boolean masks required; no silent zero scores")
    if np.any(fresh & ~ever) or not np.isfinite(v).all() or not np.isin(target, (-1, 0, 1)).all():
        raise ValueError("invalid score target, field or mask relationship")
    match = (v > 0) == (target > 0)
    active = np.abs(v) > cfg.amp_threshold
    return np.stack(((match & active)[..., ever].mean(-1),
                     (match & active)[..., fresh].mean(-1), match[..., ever].mean(-1),
                     (v*target)[..., ever].mean(-1), (match & active).mean((-2, -1)),
                     active.mean((-2, -1))), axis=-1)


def _pair(ctx, replicate, cfg):
    index, a = ctx['index'], ctx['api']
    native = a['project_theta'](a['make_thresholds'](ctx['tissue'])[None], cfg.norm)[0]
    random = SharedNoise(index, replicate, 'founder')
    v = a['launch_pattern'](0, ctx['tissue'])[None] + ctx['tissue'].copy_jitter*random.standard_normal((1, 16, 16))
    initial = np.stack((v, v.copy(), v.copy(), native[None].copy()))
    state = initial.copy()
    for _ in range(cfg.settle):
        state = advance(ctx, state, random, 0., cfg)
    founder = state[:, 0].copy()
    target = np.sign(founder[0])
    state = np.repeat(state, len(RATES), axis=1)
    ever = np.zeros((16, 16), bool)
    prefix_cuts, prefix_ends, masks, values, rngs = [], [], [], [], [random.digest()]
    for cycle in range(1, cfg.cycles):
        random = SharedNoise(index, replicate, f'cycle_{cycle}')
        state, fresh = cut(ctx, state, random)
        np.testing.assert_array_equal(fresh, np.broadcast_to(fresh[0], fresh.shape))
        ever |= fresh[0]
        masks.append(fresh[0].copy()); prefix_cuts.append(state.copy())
        for _ in range(cfg.inter_fission):
            state = advance(ctx, state, random, RATES, cfg)
        prefix_ends.append(state.copy())
        values.append(scores(state[0], target, ever, fresh[0], cfg))
        rngs.append(random.digest())

    random = SharedNoise(index, replicate, f'cycle_{cfg.cycles}')
    last_cut, fresh = cut(ctx, state, random)
    np.testing.assert_array_equal(fresh, np.broadcast_to(fresh[0], fresh.shape))
    masks.append(fresh[0].copy()); ever |= fresh[0]
    panel = boundary_panel(last_cut, native)
    panel_rates = np.array([[u if arm[1] == 'on' else 0. for arm in ARMS] for u in RATES])
    flat = panel.reshape(4, -1, 16, 16)
    snapshots, measurements = [], []
    for tick in range(cfg.inter_fission+1):
        if tick:
            flat = advance(ctx, flat, random, panel_rates.ravel(), cfg)
        if tick in cfg.times:
            snapshot = flat.reshape(panel.shape).copy()
            snapshots.append(snapshot)
            measurements.append(scores(snapshot[0], target, ever, fresh[0], cfg))
    rngs.append(random.digest())
    raw = dict(initial=initial[:, 0], founder=founder, native=native, target=target,
               prefix_cuts=np.stack(prefix_cuts), prefix_ends=np.stack(prefix_ends),
               fresh=np.stack(masks), ever=ever, last_cut=last_cut,
               descendants=np.stack(snapshots), prefix_scores=np.stack(values),
               descendant_scores=np.stack(measurements),
               prefix_age_fissions=np.arange(1, cfg.cycles),
               descendant_age_fissions=np.full(len(cfg.times), cfg.cycles),
               descendant_age_updates=(cfg.cycles-1)*cfg.inter_fission+np.array(cfg.times))
    if any(not np.isfinite(x).all() for x in raw.values()):
        raise RuntimeError("nonfinite payload; retain as failure, do not retry")
    meta = dict(tissue=index, replicate=replicate, config=asdict(cfg), rng_final=rngs,
                common_target=True, native_reset_is_not_zero=True,
                zero_R_relearns=True, inherited_body_fragment=True,
                result_bytes=sum(x.nbytes for x in raw.values()))
    return raw, meta


def execute_pair(index, replicate, *, root, cfg=CONFIG):
    root = external_root(root)
    source.preflight(root)
    if type(index) is not int or index < 0:
        raise ValueError("nonnegative integer tissue required")
    if type(replicate) is not int or not 0 <= replicate < cfg.replicates:
        raise ValueError("replicate outside the declared panel")
    return _pair(context(index), replicate, cfg)


def source_control_dependencies():
    """Load native dependencies before E69; no trajectory or output is run.

    A fresh CLI process has no source package paths installed by earlier
    disposable tests. E69 imports blueprint_web and its other dependencies
    at module import time, so context must be initialized first.
    """
    ctx = context(0)
    directory = str(source.base.sources_root()/'ancestry_world'/'src')
    if directory not in sys.path:
        sys.path.insert(0, directory)
    from ancestry_world.config import AncestryConfig
    from ancestry_world.pipeline import life_fitness
    from contract_bridge.artifacts import seed_rng
    config = AncestryConfig()
    if config.digest() != SOURCE_DIGEST:
        raise RuntimeError("E69 source configuration drift")
    return ctx, config, seed_rng, life_fitness


def source_control(u, replicate, *, root):
    """Known E69 pre-round endpoints, not a fresh or paired positive control.

    Retain a separate full trace and bridge to the unmodified original scalar
    evaluator. Its u-dependent targets/tail ages stay out of the main pool.
    """
    root = external_root(root); source.preflight(root)
    if (isinstance(u, bool) or u not in (.001, 1.)
            or type(replicate) is not int or replicate not in range(3)):
        raise ValueError("only the prespecified six known source lives")
    # Preserve the literal source seed component '1.0', even if called with 1.
    u = float(u)
    ctx, config, seed_rng, life_fitness = source_control_dependencies()
    a = ctx['api']
    random = seed_rng(config.trajectory_seed_tag, 'pre', u, replicate)
    native = a['project_theta'](a['make_thresholds'](ctx['tissue'])[None], config.norm)
    v = a['launch_pattern'](0, ctx['tissue'])[None]+ctx['tissue'].copy_jitter*random.standard_normal((1, 16, 16))
    state = np.stack((v, v.copy(), v.copy(), native))
    initial = state[:, 0].copy()
    for _ in range(config.settle_sweeps):
        state = advance(ctx, state, random, u)
    founder = state[:, 0].copy(); target = np.sign(founder[0])
    ever = np.zeros((16, 16), bool)
    cuts, ends, masks, values = [], [], [], []
    for _ in range(config.cycles):
        state, fresh = cut(ctx, state, random)
        ever |= fresh[0]; cuts.append(state[:, 0].copy()); masks.append(fresh[0].copy())
        for _ in range(config.inter_fission):
            state = advance(ctx, state, random, u)
        ends.append(state[:, 0].copy())
        values.append(scores(state[0], target, ever, fresh[0])[0])
    values = np.stack(values)
    traced = float(values[-3:, 0].mean())
    original_rng = seed_rng(config.trajectory_seed_tag, 'pre', u, replicate)
    original = life_fitness(config, ctx['tissue'], ctx['ladder'], ctx['bp'], u, 8, True, original_rng)
    if original != traced or canonical_digest(original_rng.bit_generator.state) != canonical_digest(random.bit_generator.state):
        raise AssertionError("source-control metric/randomness bridge failed")
    return dict(initial=initial, founder=founder, target=target, cuts=np.stack(cuts),
                ends=np.stack(ends), fresh=np.stack(masks), values=values,
                score_age_fissions=np.array([6, 7, 8])), dict(
                    tissue=0, u=u, replicate=replicate, source_fitness=original,
                    traced_fitness=traced, rng_final=canonical_digest(random.bit_generator.state),
                    source_config_digest=config.digest(), source_bridge_exact=True)


def contrasts(final_scores):
    """Per-unit conditional effects; never ratios or selection coefficients.

    Input ends in u,arm,metric. Outputs retain all leading unit dimensions.
    """
    if final_scores.shape[-3:] != (len(RATES), len(ARMS), len(METRICS)):
        raise ValueError("expected ... u,arm,metric")
    if not np.isfinite(final_scores).all():
        raise ValueError("finite scores required")
    f = final_scores.reshape(*final_scores.shape[:-3], len(RATES), 2, 2, 2, len(METRICS))
    rows = {}
    for i, u in enumerate(RATES):
        for w, r in product(range(2), repeat=2):
            rows[f'theta/u={u}/writer={w}/R={r}'] = f[..., i, 0, w, r, :]-f[..., i, 1, w, r, :]
        for t, r in product(range(2), repeat=2):
            rows[f'writer/u={u}/theta={t}/R={r}'] = f[..., i, t, 0, r, :]-f[..., i, t, 1, r, :]
        for t, w in product(range(2), repeat=2):
            rows[f'R/u={u}/theta={t}/writer={w}'] = f[..., i, t, w, 0, :]-f[..., i, t, w, 1, :]
        for r in range(2):
            rows[f'theta_x_writer/u={u}/R={r}'] = (
                f[..., i, 0, 0, r, :]-f[..., i, 1, 0, r, :]
                -f[..., i, 0, 1, r, :]+f[..., i, 1, 1, r, :])
    for i in (1, 2):
        rows[f'rate/u={RATES[i]}_minus_0.001/intact'] = f[..., i, 0, 0, 0, :]-f[..., 0, 0, 0, 0, :]
    return rows


def _checked_scores(value, shape):
    if not isinstance(value, np.ndarray) or value.shape != shape or value.dtype != np.float64:
        raise ValueError('complete float64 metric array required')
    if not np.isfinite(value).all():
        raise ValueError('nonfinite scores must not be silently dropped')
    fidelity = value[..., [0, 1, 2, 4, 5]]
    if np.any((fidelity < 0) | (fidelity > 1)) or np.any(abs(value[..., 3]) > 2):
        raise ValueError('scores outside their native ranges')
    if np.any(value[..., 0] > value[..., 2]) or np.any(value[..., 4] > value[..., 5]):
        raise ValueError('amplitude fidelity exceeds sign fidelity or active fraction')
    return value


def final_score_record(raw, meta):
    """Extract only the full main configuration's declared final checkpoint.

    This checks endpoint identity, not physical validity. The independent
    trajectory replay and immutable artifact audit remain separate obligations.
    """
    if canonical_digest(meta['config']) != canonical_digest(asdict(CONFIG)):
        raise ValueError('disposable or changed configurations cannot enter main pooling')
    for name, expected in (
            ('descendant_age_fissions', np.full(len(CONFIG.times), CONFIG.cycles)),
            ('descendant_age_updates', (CONFIG.cycles-1)*CONFIG.inter_fission+np.array(CONFIG.times))):
        ages = raw[name]
        if not isinstance(ages, np.ndarray) or ages.dtype.kind not in 'iu' or not np.array_equal(ages, expected):
            raise ValueError('missing, changed or mislabelled target-age sequence')
    values = _checked_scores(raw['descendant_scores'], (len(CONFIG.times), 3, 8, 6))
    record = dict(schema=SCORE_SCHEMA, seed_tag=TAG, tissue=meta['tissue'], replicate=meta['replicate'],
                  config_digest=canonical_digest(asdict(CONFIG)), sweep=CONFIG.times[-1],
                  target_age_fissions=CONFIG.cycles, target_age_updates=CONFIG.cycles*CONFIG.inter_fission,
                  scores=values[-1].copy())
    _validate_score_record(record)
    return record


def _validate_score_record(record):
    keys = {'schema', 'seed_tag', 'tissue', 'replicate', 'config_digest', 'sweep',
            'target_age_fissions', 'target_age_updates', 'scores'}
    if not isinstance(record, dict) or set(record) != keys:
        raise ValueError('exact final-score record schema required')
    for key, allowed in (('tissue', TISSUES), ('replicate', range(CONFIG.replicates)),
                         ('sweep', (500,)), ('target_age_fissions', (8,)),
                         ('target_age_updates', (4000,))):
        if type(record[key]) is not int or record[key] not in allowed:
            raise ValueError(f'invalid main endpoint identity: {key}')
    for key, expected in (('schema', SCORE_SCHEMA), ('seed_tag', TAG),
                          ('config_digest', canonical_digest(asdict(CONFIG)))):
        if record[key] != expected:
            raise ValueError(f'wrong main endpoint provenance: {key}')
    return _checked_scores(record['scores'], (3, 8, 6))


def ordered_final_scores(records):
    """Reject missing, duplicated, wrong-cohort and wrong-time lives outright."""
    records = list(records)
    expected = tuple(product(TISSUES, range(CONFIG.replicates)))
    if len(records) != len(expected):
        raise ValueError('all sixteen unique main lives required')
    cells = {}
    for record in records:
        value = _validate_score_record(record)
        key = record['tissue'], record['replicate']
        if key in cells:
            raise ValueError('duplicate main life; no reweighting or overwrite allowed')
        cells[key] = value.copy()
    if set(cells) != set(expected):
        raise ValueError('incomplete main panel')
    return np.stack([cells[key] for key in expected]).reshape(8, 2, 3, 8, 6)


def summarize(records):
    """Pure complete-panel arithmetic; never simulates or writes an artifact.

    All returned numbers concern supplied records. They are not evidence of
    source identity or successful dynamics until independently checked/hashed.
    """
    x = ordered_final_scores(records)
    absolute_blocks = x.mean(axis=1)
    effects = contrasts(x)
    rows = {}
    for name, lives in effects.items():
        blocks = lives.mean(axis=1)
        row = dict(per_life=lives.tolist(), per_tissue=blocks.tolist(), mean=blocks.mean(axis=0).tolist())
        for label, values, axes in (('tissues', blocks, (0,)), ('lives', lives, (0, 1))):
            for direction, mask in (('positive', values > 0), ('negative', values < 0), ('tied', values == 0)):
                row[f'{direction}_{label}'] = mask.sum(axis=axes).tolist()
        rows[name] = row
    settings = analysis_contract()
    generator = np.random.Generator(np.random.PCG64(settings['bootstrap_seed']))
    draws = generator.integers(0, len(TISSUES), size=(BOOTSTRAP_DRAWS, len(TISSUES)), dtype=np.int64)
    primary_blocks = effects[PRIMARY_KEY][..., 0].mean(axis=1)
    bootstrap = primary_blocks[draws].mean(axis=1)
    primary = dict(contrast=PRIMARY_KEY, metric='ever_amplitude', mean=float(primary_blocks.mean()),
                   interval95=np.quantile(bootstrap, [.025, .975], method='linear').tolist(),
                   bootstrap_means=bootstrap.tolist(),
                   draw_indices_sha256=hashlib.sha256(draws.astype('<i8', copy=False).tobytes()).hexdigest())
    result = dict(schema='l21_paired_fitness_summary_v1', analysis=settings,
                  unit_order=[dict(tissue=t, replicate=r) for t, r in product(TISSUES, range(CONFIG.replicates))],
                  axes=dict(rates=list(RATES), arms=[list(a) for a in ARMS], metrics=list(METRICS)),
                  absolute=dict(per_life=x.tolist(), per_tissue=absolute_blocks.tolist(),
                                mean=absolute_blocks.mean(axis=0).tolist()), contrasts=rows, primary=primary)
    # Explicitly prohibit NaN/Infinity in the future JSON artifact.
    json.dumps(result, allow_nan=False)
    return result


def checker():
    path = Path(__file__).resolve().parents[2]/SCIENCE[1]
    spec = importlib.util.spec_from_file_location('d094_checker', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--external-root', type=Path)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--resources', action='store_true')
    group.add_argument('--contract', action='store_true')
    args = parser.parse_args()
    # Read-only planning commands only. No silent simulation/benchmark/default.
    print(json.dumps(resource_report(args.external_root) if args.resources else contract(), indent=2))


if __name__ == '__main__':
    main()
