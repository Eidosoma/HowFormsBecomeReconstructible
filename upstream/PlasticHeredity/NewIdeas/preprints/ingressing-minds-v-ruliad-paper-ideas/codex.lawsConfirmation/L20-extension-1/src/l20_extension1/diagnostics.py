"""Development-only copies of already-observed F0 records; no test generator."""
from __future__ import annotations

from dataclasses import asdict
from functools import lru_cache
import hashlib
from pathlib import Path
import numpy as np

from laws_confirmation import l20_guide_renewal as old
from laws_confirmation import l20_fresh_founders as d140
from laws_confirmation import l15_repair_speed_run as io
from laws_confirmation.io import DEFAULT_EXTERNAL_ROOT, sha256_file

WS = old.WS / 'L20-extension-1'
BASE = DEFAULT_EXTERNAL_ROOT
ROOT = BASE / 'L20-extension-1'
RUN_ID = 'l20_extension1_development_v1_attempt1'
TAG = 'l20-extension1-diagnostics-v1'
CONFIG = old.CONFIG
DEVELOPMENT = tuple(('d135', i) for i in range(75000, 75008)) + tuple(('d140', i) for i in range(78000, 78008))
DISPOSABLE = ('disposable', 514240)
HELDOUT_RESERVED = tuple(range(90000, 90016))  # Never executable in this module.
CASES = tuple((r, m) for r in (0, 1) for m in ('translated', 'aligned'))
BRANCHES = ('U0', 'U1', 'C1')
INITIAL_FEATURES = ('own_best_correlation', 'own_minus_alternative_best_correlation',
                    'guide_own_minus_alternative', 'routed_own_minus_alternative_correlation')
CYCLE_FEATURES = INITIAL_FEATURES + ('terminal_qualified_preference', 'terminal_v_rms')
SCIENCE = ('PROTOCOL_V1.md', 'src/l20_extension1/__init__.py',
           'src/l20_extension1/diagnostics.py', 'src/l20_extension1/predictor.py',
           'src/l20_extension1/audit.py', 'src/l20_extension1/development_run.py',
           'tests/test_extension1.py', 'scripts/run_development.sh')


def validate_spec(cohort, index):
    if type(index) is not int or (cohort, index) not in DEVELOPMENT + (DISPOSABLE,):
        raise ValueError('declared development/disposable founder required; held-out generation forbidden')
    return index - 2000 if cohort == 'd135' else index


def source_paths(cohort, index):
    validate_spec(cohort, index)
    run = 'l20_serial_address_v1_attempt1' if cohort == 'd135' else d140.RUN_ID
    directory = BASE / ('tmp' if cohort == 'disposable' else 'outputs') / (run + '_benchmark' if cohort == 'disposable' else run)
    return directory / f'block_{index}.npz', directory / f'block_{index}.json'


def source_inputs(cohort, index):
    """Return strictly separated diagnostic inputs and already-observed labels."""
    host = validate_spec(cohort, index)
    a, b = source_paths(cohort, index)
    raw, meta = io.load_npz(a), io.read_json(b)
    assert meta['index'] == index and meta['config'] == asdict(CONFIG)
    f0, guides = raw['founder_packets'].copy(), raw['guide'].copy()
    assert f0.shape == (4, 2, 2048) and f0.dtype == np.uint8
    assert guides.shape == (4, 2, 16, 16) and guides.dtype == np.float64
    y = np.zeros((4, 4), dtype=np.float64)
    for life in range(4):
        validate_guide(guides[life])
        assert meta['lives'][life]['host']['index'] == host
        for ci, (role, mode) in enumerate(CASES):
            ki = d140.CASES.index((role, mode))
            np.testing.assert_array_equal(raw['incoming'][life, ki, 0], f0[life, role])
            ti = d140.PROBES.index((role, mode))
            value = terminal_features(raw['terminal_states'][life, ti, -1, 0], role)[0]
            assert value == raw['terminal_values'][life, ti, -1, 0] - raw['terminal_values'][life, ti, -1, 1]
            y[life, ci] = value
    return f0, guides, y, dict(cohort=cohort, index=index, host_index=host,
        source_sha256={str(a): sha256_file(a), str(b): sha256_file(b)})


def rng(cohort, index, life, phase):
    validate_spec(cohort, index)
    if type(life) is not int or not 0 <= life < 4:
        raise ValueError('declared life required')
    return old.generator(f'{TAG}:{cohort}', index, life, phase)


def validate_guide(guide):
    if guide.shape != (2, 16, 16) or guide.dtype != np.float64 or hashlib.sha256(guide.astype('<f8').tobytes()).hexdigest() != old.GUIDE_SHA256:
        raise ValueError('original frozen guide required')


def targets():
    y, x = np.indices((16, 16))
    return np.stack((np.where(y < 8, 1., -1.), np.where(x % 8 < 4, 1., -1.)))


@lru_cache(maxsize=1)
def template_bank():
    bank = np.stack([[np.roll(t, divmod(i, 16), (0, 1)) for i in range(256)] for t in targets()])
    bank.setflags(write=False)
    return bank


def record_features(packet, role, guide):
    if role not in (0, 1):
        raise ValueError('known family required')
    field = old.decode(packet)
    centered = field - field.mean()
    scale = centered.std()
    correlations = np.einsum('rnij,ij->rn', template_bank(), centered, optimize=False) / (256 * scale) if scale else np.zeros((2, 256))
    best = correlations.max(axis=1)
    routed, scores, _ = old.route(packet, 'learned', guide)
    rfield = old.decode(routed)
    normalized = (rfield - rfield.mean()) / scale if scale else np.zeros((16, 16))
    canonical = np.mean(targets() * normalized, axis=(1, 2))
    guide_best = scores.max(axis=(1, 2))
    return np.asarray((best[role], best[role] - best[1-role], guide_best[role] - guide_best[1-role],
                       canonical[role] - canonical[1-role]), dtype=np.float64)


def terminal_features(v, role):
    if v.shape != (16, 16) or not np.isfinite(v).all():
        raise ValueError('finite terminal field required')
    active = np.abs(v) > .2
    matches = np.mean(((v > 0) == (targets() > 0)) & active, axis=(1, 2))
    return np.asarray((matches[role] - matches[1-role], np.sqrt(np.mean(v*v))), dtype=np.float64)


def partial_shuffle(packet, sites, permutation):
    if sites.shape != (64,) or permutation.shape != (64,) or sites.dtype != np.int64 or permutation.dtype != np.int64:
        raise ValueError('64 integer positions and a 64-way permutation required')
    if len(set(sites.tolist())) != 64 or np.any(sites < 0) or np.any(sites >= 256) or sorted(permutation.tolist()) != list(range(64)):
        raise ValueError('valid unique positions and permutation required')
    original = old.decode(packet).ravel()
    changed = original.copy()
    changed[sites] = original[sites[permutation]]
    return old.encode(changed.reshape(16, 16))


def cycle(packet, cohort, index, life, trial, mode, guide):
    host = validate_spec(cohort, index)
    if type(trial) is not int or trial not in (0, 1) or mode not in ('translated', 'aligned'):
        raise ValueError('declared diagnostic trial/writer required')
    validate_guide(guide)
    random = lambda phase: rng(cohort, index, life, f'trial{trial}:{phase}')
    ctx = old.context(host)
    routed, first_scores, selection = old.route(packet, 'learned', guide)
    reads, reader = old.read_selected(routed, ctx, random('birth'), random('read'), CONFIG)
    shift = np.asarray(divmod(int(random('shift').integers(1, 256)), 16), dtype=np.int64)
    writes, writer = old.write_streams(reads[-1], ctx, random('write'), mode, shift, CONFIG)
    outgoing = old.encode(old.record(writes[-1, 2]))
    terminal_packet, last_scores, last_selection = old.route(outgoing, 'learned', guide)
    terminal, final_reader = old.read_selected(terminal_packet, ctx, random('final_birth'), random('final_read'), CONFIG, times=CONFIG.times)
    raw = dict(input=np.frombuffer(packet, np.uint8), routed=np.frombuffer(routed, np.uint8),
        outgoing=np.frombuffer(outgoing, np.uint8), terminal_packet=np.frombuffer(terminal_packet, np.uint8),
        read_states=reads, write_states=writes, terminal_states=terminal,
        scores=np.stack((first_scores, last_scores)), shift=shift)
    meta = dict(trial=trial, mode=mode, selector=selection, reader=reader, writer=writer,
                terminal_selector=last_selection, terminal_reader=final_reader)
    return raw, meta


def simulate_life(cohort, index, life, founders, guide, order=CASES):
    """Only F0 bytes/guide/public condition enter; no labels or parent states."""
    host = validate_spec(cohort, index)
    if type(life) is not int or not 0 <= life < 4 or founders.shape != (2, 2048) or founders.dtype != np.uint8:
        raise ValueError('declared life and two F0 packets required')
    if len(order) != 4 or set(order) != set(CASES):
        raise ValueError('complete unique condition order required')
    validate_guide(guide)
    sites = rng(cohort, index, life, 'mask').permutation(256)[:64].astype(np.int64)
    permutation = rng(cohort, index, life, 'permutation').permutation(64).astype(np.int64)
    paths, records, initial, features = {}, {}, {}, {}
    strengths, counts = {}, {}
    for role, mode in order:
        packet = founders[role].tobytes()
        challenged = partial_shuffle(packet, sites, permutation)
        copies = (packet, packet, challenged)
        rows, entries, values = [], [], []
        for bi, supplied in enumerate(copies):
            row, entry = cycle(supplied, cohort, index, life, 0 if bi == 0 else 1, mode, guide)
            rows.append(row); entries.append(entry)
            values.append(np.concatenate((record_features(row['outgoing'].tobytes(), role, guide),
                                          terminal_features(row['terminal_states'][-1, 0], role))))
        case = (role, mode)
        paths[case] = {k: np.stack([r[k] for r in rows]) for k in rows[0]}
        records[case] = entries
        initial[case] = record_features(packet, role, guide)
        features[case] = np.stack(values)
        strengths[case] = np.asarray([(old.decode(b).mean(), np.sqrt(np.mean(old.decode(b)**2))) for b in copies])
        counts[case] = np.count_nonzero(old.decode(packet) != old.decode(challenged))
    raw = {k: np.stack([paths[c][k] for c in CASES]) for k in paths[CASES[0]]}
    raw.update(founder_packets=founders.copy(), guide=guide.copy(), sites=sites, permutation=permutation,
        initial_features=np.stack([initial[c] for c in CASES]), diagnostic_features=np.stack([features[c] for c in CASES]),
        input_strength=np.stack([strengths[c] for c in CASES]), changed_sites=np.asarray([counts[c] for c in CASES], np.int64))
    ctx = old.context(host)
    meta = dict(cohort=cohort, index=index, life=life, host=dict(index=host, tissue=asdict(ctx['tissue']),
        ladder=asdict(ctx['ladder']), blueprint=asdict(ctx['bp'])), tag=f'{TAG}:{cohort}', config=asdict(CONFIG),
        cases=[list(c) for c in CASES], branches=list(BRANCHES), cycles=[records[c] for c in CASES],
        guide_sha256=old.GUIDE_SHA256, predictor_has_parent_state=False, diagnostic_to_lineage=False)
    return raw, meta


def observer_features(initial, first, second):
    """Two-copy interface; caller supplies ONLY the permitted two summaries."""
    if initial.shape[-1] != 4 or first.shape != second.shape or first.shape[-1] != 6 or initial.shape[:-1] != first.shape[:-1]:
        raise ValueError('four starting and two six-feature diagnostic summaries required')
    result = np.concatenate((initial, first, second), axis=-1)
    if not np.isfinite(result).all():
        raise ValueError('no missing/nonfinite features or exclusions')
    return result


def contract():
    return dict(stage='development_only', run_id=RUN_ID, development=[list(c) for c in DEVELOPMENT],
        disposable=list(DISPOSABLE), heldout_reserved=list(HELDOUT_RESERVED), heldout_generation=False,
        cases=[list(c) for c in CASES], branches=list(BRANCHES), config=asdict(CONFIG),
        guide_sha256=old.GUIDE_SHA256, shuffle_positions=64, shuffle_reprojection=False,
        full_features=16, initial_features=list(INITIAL_FEATURES), cycle_features=list(CYCLE_FEATURES),
        development_cases=256, diagnostic_cycles=768, diagnostic_readers=1536,
        selectors=1536, new_main_lineages=0, automatic_successor=False)
