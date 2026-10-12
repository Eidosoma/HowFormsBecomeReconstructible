"""D173 isolated implementation of D172's fixed diagnostic feedback pulse."""
from dataclasses import asdict
import numpy as np
from laws_confirmation import l20_guide_renewal as old
from laws_confirmation.io import canonical_digest
from . import diagnostics as features, recovery_features as starting

CONFIG = old.CONFIG
CASES = ((0, 'translated'), (0, 'aligned'), (1, 'translated'), (1, 'aligned'))
ARMS = ('U1', 'P1')
CELLS = tuple((g, b) for g in range(4) for b in range(2))
WRITE_TIMES = (0, 1, 300, 301, 400, 401, 1000)
SHIFT = (2, 1)
BOUNDS = (301, 400)
BYTE_KEYS = ('founder_packets', 'input', 'routed', 'outgoing', 'terminal_packet')
SHAPES = dict(founder_packets=(2, 2048), guide=(2, 16, 16),
    input=(4, 2, 2048), routed=(4, 2, 2048), outgoing=(4, 2, 2048),
    terminal_packet=(4, 2, 2048), read_states=(4, 2, 5, 3, 16, 16),
    write_states=(4, 2, 7, 4, 16, 16), terminal_states=(4, 2, 4, 3, 16, 16),
    scores=(4, 2, 2, 2, 16, 16), shift=(4, 2, 2),
    starting_features=(4, 7), diagnostic_features=(4, 2, 6))


def namespace(cohort, index, life):
    legal = {'development': range(90000, 90016), 'disposable': (514240,)}
    if cohort not in legal or type(index) is not int or index not in legal[cohort]:
        raise ValueError('declared development or disposable founder required')
    if type(life) is not int or not 0 <= life < 4:
        raise ValueError('declared life required')
    return ('l20-extension1-heldout-v1:diagnostics:heldout' if cohort == 'development'
            else 'l20-extension1-pilot64-v1:diagnostics:disposable')


def draw(cohort, index, life, phase):
    if phase not in ('birth', 'read', 'shift', 'write', 'final_birth', 'final_read'):
        raise ValueError('diagnostic phase only')
    return old.generator(namespace(cohort, index, life), index, life, 'trial1:' + phase)


def applied(theta, mode, shift, step, pulse, offset=SHIFT):
    """Offset zero is a qualification alias, never a third diagnostic arm."""
    if mode not in ('translated', 'aligned') or type(pulse) is not bool:
        raise ValueError('writer mode and boolean pulse required')
    if type(step) is not int or not 1 <= step <= 1000 or offset not in (SHIFT, (0, 0)):
        raise ValueError('fixed pulse schedule/displacement')
    if theta.shape != (1, 16, 16) or theta.dtype != np.float64 or not np.isfinite(theta).all():
        raise ValueError('finite theta field')
    if shift.shape != (2,) or shift.dtype != np.int64 or not np.all((shift >= 0) & (shift < 16)):
        raise ValueError('periodic assigned displacement')
    base = theta if mode == 'aligned' else np.roll(theta, tuple(int(x) for x in shift), (-2, -1))
    return np.roll(base, offset, (-2, -1)) if pulse and 301 <= step <= 400 else base


def write_streams(start, ctx, random, mode, shift, pulse, *, offset=SHIFT):
    if start.shape != (3, 16, 16) or start.dtype != np.float64 or not np.isfinite(start).all():
        raise ValueError('finite reader-end body')
    state = tuple(x[None].copy() for x in start)
    theta = np.zeros((1, 16, 16))
    saved = [np.stack((*state, theta))[:, 0]]
    for step in range(1, 1001):
        feedback = applied(theta, mode, shift, step, pulse, offset)
        state = ctx['api']['blueprint_step'](*state, feedback, ctx['tissue'], ctx['ladder'], ctx['bp'], 'T', random)
        theta = ctx['api']['original'].project_theta((1 - CONFIG.lam) * theta + CONFIG.lam * np.tanh(state[2]), CONFIG.norm)
        if step in WRITE_TIMES:
            saved.append(np.stack((*state, theta))[:, 0])
    writer = dict(noise_rng=canonical_digest(random.bit_generator.state), mode=mode, shift=shift.tolist(),
        theta_start_zero=True, theta_writing=True, gain=.2, rho=.002, lam=.001, sigma=.3,
        incoming_packet_access=False, guide_access=False, target_labels=False,
        pulse_enabled=pulse, pulse_shift=list(offset), pulse_bounds=list(BOUNDS))
    return np.stack(saved), writer


def legacy_writer(meta):
    return {k: v for k, v in meta.items() if k not in ('pulse_enabled', 'pulse_shift', 'pulse_bounds')}


def cycle(packet, guide, cohort, index, life, mode, pulse):
    namespace(cohort, index, life)
    features.validate_guide(guide)
    if mode not in ('translated', 'aligned') or type(pulse) is not bool:
        raise ValueError('declared writer and pulse')
    old.decode(packet)
    ctx = old.context(index)
    random = lambda phase: draw(cohort, index, life, phase)
    routed, first_scores, selection = old.route(packet, 'learned', guide)
    reads, reader = old.read_selected(routed, ctx, random('birth'), random('read'), CONFIG)
    shift = np.array(divmod(int(random('shift').integers(1, 256)), 16), np.int64)
    writes, writer = write_streams(reads[-1], ctx, random('write'), mode, shift, pulse)
    outgoing = old.encode(old.record(writes[-1, 2]))
    terminal_packet, last_scores, last_selection = old.route(outgoing, 'learned', guide)
    terminal, final_reader = old.read_selected(terminal_packet, ctx, random('final_birth'), random('final_read'), CONFIG, times=CONFIG.times)
    raw = dict(input=np.frombuffer(packet, np.uint8), routed=np.frombuffer(routed, np.uint8),
        outgoing=np.frombuffer(outgoing, np.uint8), terminal_packet=np.frombuffer(terminal_packet, np.uint8),
        read_states=reads, write_states=writes, terminal_states=terminal,
        scores=np.stack((first_scores, last_scores)), shift=shift)
    return raw, dict(trial=1, mode=mode, selector=selection, reader=reader, writer=writer,
        terminal_selector=last_selection, terminal_reader=final_reader)


def validate(raw, lives=None):
    if set(raw) != set(SHAPES):
        raise ValueError('complete diagnostic schema only')
    for key, shape in SHAPES.items():
        want = shape if lives is None else (lives,) + shape
        dtype = np.uint8 if key in BYTE_KEYS else np.int64 if key == 'shift' else np.float64
        if raw[key].shape != want or raw[key].dtype != dtype or not np.isfinite(raw[key]).all():
            raise ValueError('invalid diagnostic array: ' + key)


def simulate_life(founders, guide, cohort, index, life, order=CELLS):
    tag = namespace(cohort, index, life)
    if founders.shape != (2, 2048) or founders.dtype != np.uint8:
        raise ValueError('only two declared F0 packets')
    if len(order) != 8 or set(order) != set(CELLS):
        raise ValueError('complete unique cell order')
    features.validate_guide(guide)
    paths, entries, endpoints = {}, {}, {}
    start = []
    for role, _ in CASES:
        packet = founders[role].tobytes()
        start.append(np.r_[features.record_features(packet, role, guide), starting.axis_rms(old.decode(packet), role)])
    for group, branch in order:
        role, mode = CASES[group]
        row, entry = cycle(founders[role].tobytes(), guide, cohort, index, life, mode, branch == 1)
        paths[group, branch], entries[group, branch] = row, entry
        endpoints[group, branch] = np.r_[features.record_features(row['outgoing'].tobytes(), role, guide),
            features.terminal_features(row['terminal_states'][-1, 0], role)]
    raw = {key: np.stack([np.stack([paths[g, b][key] for b in range(2)]) for g in range(4)])
           for key in paths[0, 0]}
    raw.update(founder_packets=founders.copy(), guide=guide.copy(), starting_features=np.stack(start),
        diagnostic_features=np.stack([np.stack([endpoints[g, b] for b in range(2)]) for g in range(4)]))
    validate(raw)
    ctx = old.context(index)
    meta = dict(cohort=cohort, index=index, life=life, tag=tag,
        host=dict(index=index, tissue=asdict(ctx['tissue']), ladder=asdict(ctx['ladder']), blueprint=asdict(ctx['bp'])),
        config=asdict(CONFIG), cases=[list(c) for c in CASES], branches=list(ARMS),
        write_times=list(WRITE_TIMES), pulse_shift=list(SHIFT), pulse_bounds=list(BOUNDS),
        guide_sha256=old.GUIDE_SHA256, predictor_has_parent_state=False,
        diagnostic_to_lineage=False, actual_outcomes_accessed=False,
        cycles=[[entries[g, b] for b in range(2)] for g in range(4)])
    return raw, meta
