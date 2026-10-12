"""Independent pulse replay: indexed feedback gathers and existing audited physics.

Never calls feedback_pulse's mapping, writer, simulation or feature functions.
"""
from dataclasses import asdict
import numpy as np
from laws_confirmation.io import canonical_digest
from . import heldout_diagnostic_audit as legacy
from .address_swap_check import same

prior, physics = legacy.prior, legacy.physics
TIMES = (0, 1, 300, 301, 400, 401, 1000)
SHAPES = dict(founder_packets=(2, 2048), guide=(2, 16, 16),
    input=(4, 2, 2048), routed=(4, 2, 2048), outgoing=(4, 2, 2048),
    terminal_packet=(4, 2, 2048), read_states=(4, 2, 5, 3, 16, 16),
    write_states=(4, 2, 7, 4, 16, 16), terminal_states=(4, 2, 4, 3, 16, 16),
    scores=(4, 2, 2, 2, 16, 16), shift=(4, 2, 2),
    starting_features=(4, 7), diagnostic_features=(4, 2, 6))


def namespace(cohort, index, life):
    assert type(index) is int and type(life) is int and 0 <= life < 4
    if cohort == 'development':
        assert index in range(90000, 90016)
        return 'l20-extension1-heldout-v1:diagnostics:heldout'
    assert cohort == 'disposable' and index == 514240
    return 'l20-extension1-pilot64-v1:diagnostics:disposable'


def trace(start, tissue, ladder, random, mode, shift, pulse, replay=True):
    cfg = legacy.p.CONFIG
    state = tuple(field[None].copy() for field in start)
    theta = np.zeros((1, 16, 16))
    saved = [np.stack((*state, theta))[:, 0]]
    y, x = np.indices((16, 16))
    dy, dx = (0, 0) if mode == 'aligned' else tuple(int(v) for v in shift)
    normal = ((y - dy) % 16, (x - dx) % 16)
    moved = ((y - dy - 2) % 16, (x - dx - 1) % 16)
    for t in range(1, 1001):
        noise = random.standard_normal((1, 16, 16))
        if replay:
            address = moved if pulse and t > 300 and t < 401 else normal
            feedback = theta[0][address][None]
            state = physics.step(*state, feedback, tissue, ladder, .2, .002, noise)
            theta = prior.project(.999 * theta + .001 * np.tanh(state[2]))
            if t in TIMES:
                saved.append(np.stack((*state, theta))[:, 0])
    return np.stack(saved), dict(noise_rng=canonical_digest(random.bit_generator.state), mode=mode,
        shift=shift.tolist(), theta_start_zero=True, theta_writing=True, gain=.2, rho=.002,
        lam=.001, sigma=.3, incoming_packet_access=False, guide_access=False, target_labels=False,
        pulse_enabled=pulse, pulse_shift=[2, 1], pulse_bounds=[301, 400])


def start_features(packet, role, guide):
    field = prior.unpack(packet)
    centered = field - np.sum(field) / 256
    rows = np.sum(centered, axis=1, keepdims=True) / 16
    columns = np.sum(centered, axis=0, keepdims=True) / 16
    residual = centered - rows - columns
    a, b = (rows, columns) if role == 0 else (columns, rows)
    rms = lambda v: np.sqrt(np.sum(v * v) / v.size)
    return np.r_[legacy.record_features(packet, role, guide), rms(a), rms(b), rms(residual)]


def check_life(raw, meta, original, original_meta, replay=True):
    assert set(raw) == set(SHAPES)
    for key, shape in SHAPES.items():
        dtype = np.uint8 if key in ('founder_packets', 'input', 'routed', 'outgoing', 'terminal_packet') else np.int64 if key == 'shift' else np.float64
        assert raw[key].shape == shape and raw[key].dtype == dtype and np.isfinite(raw[key]).all(), key
    co, index, life = meta['cohort'], meta['index'], meta['life']
    tag = namespace(co, index, life)
    assert meta['tag'] == original_meta['tag'] == tag
    assert (original_meta['index'], original_meta['life']) == (index, life)
    expected = dict(cohort=co, index=index, life=life, tag=tag, host=original_meta['host'],
        config=asdict(legacy.p.CONFIG), cases=[[0, 'translated'], [0, 'aligned'], [1, 'translated'], [1, 'aligned']],
        branches=['U1', 'P1'], write_times=list(TIMES), pulse_shift=[2, 1], pulse_bounds=[301, 400],
        guide_sha256=legacy.GUIDE_SHA, predictor_has_parent_state=False,
        diagnostic_to_lineage=False, actual_outcomes_accessed=False)
    same({k: v for k, v in meta.items() if k != 'cycles'}, expected)
    assert len(meta['cycles']) == 4 and all(len(cells) == 2 for cells in meta['cycles'])
    for key in ('founder_packets', 'guide'):
        np.testing.assert_array_equal(raw[key], original[key])
    assert prior.sha(raw['guide'].astype('<f8').tobytes()) == legacy.GUIDE_SHA
    tissue, ladder, bp = physics.parameters(meta['host'])
    cfg = legacy.p.CONFIG
    maxima = np.zeros(5)
    entries = []
    for g in range(4):
        role, mode = g // 2, 'aligned' if g % 2 else 'translated'
        packet = raw['founder_packets'][role].tobytes()
        same(raw['starting_features'][g], start_features(packet, role, raw['guide']))
        np.testing.assert_array_equal(raw['starting_features'][g, :4], original['initial_features'][g])
        cells = []
        for b in range(2):
            draw = lambda phase: physics.generator(tag, index, life, 'trial1:' + phase)
            assert raw['input'][g, b].tobytes() == packet
            routed, scores, selection = prior.prior.select(packet, raw['guide'])
            assert raw['routed'][g, b].tobytes() == routed
            same(raw['scores'][g, b, 0], scores)
            reads, reader = prior.read_trace(routed, tissue, ladder, bp, draw('birth'), draw('read'), cfg, replay=replay)
            np.testing.assert_array_equal(raw['read_states'][g, b, 0], reads[0])
            if replay:
                maxima[0] = max(maxima[0], physics.compare(raw['read_states'][g, b], reads))
            shift = np.array(divmod(int(draw('shift').integers(1, 256)), 16), np.int64)
            np.testing.assert_array_equal(raw['shift'][g, b], shift)
            writes, writer = trace(raw['read_states'][g, b, -1], tissue, ladder, draw('write'), mode, shift, b == 1, replay)
            np.testing.assert_array_equal(raw['write_states'][g, b, 0], writes[0])
            if replay:
                maxima[1] = max(maxima[1], physics.compare(raw['write_states'][g, b], writes))
            ref = raw['write_states'][g, b, -1, 2]
            assert np.tanh(ref).std() > 1e-9, 'retain failure, do not exclude the case'
            outgoing = prior.packet(prior.project(np.tanh(ref)))
            assert outgoing == raw['outgoing'][g, b].tobytes()
            final_packet, scores, final_selection = prior.prior.select(outgoing, raw['guide'])
            assert final_packet == raw['terminal_packet'][g, b].tobytes()
            same(raw['scores'][g, b, 1], scores)
            terminal, final_reader = prior.read_trace(final_packet, tissue, ladder, bp, draw('final_birth'), draw('final_read'), cfg, times=cfg.times, replay=replay)
            np.testing.assert_array_equal(raw['terminal_states'][g, b, 0], terminal[0])
            if replay:
                maxima[2] = max(maxima[2], physics.compare(raw['terminal_states'][g, b], terminal))
            wanted = np.r_[legacy.record_features(outgoing, role, raw['guide']), legacy.terminal_features(raw['terminal_states'][g, b, -1, 0], role)]
            np.testing.assert_allclose(raw['diagnostic_features'][g, b], wanted, atol=1e-12, rtol=0)
            maxima[3] = max(maxima[3], float(abs(raw['diagnostic_features'][g, b] - wanted).max()))
            entry = dict(trial=1, mode=mode, selector=selection, reader=reader, writer=writer,
                terminal_selector=final_selection, terminal_reader=final_reader)
            old = original_meta['cycles'][g][1]
            for section, key in (('reader', 'birth_rng'), ('reader', 'read_rng'), ('writer', 'noise_rng'),
                                 ('terminal_reader', 'birth_rng'), ('terminal_reader', 'read_rng')):
                assert entry[section][key] == old[section][key]
                assert entry[section][key] != original_meta['cycles'][g][0][section][key]
            if b == 0:
                for key in ('input', 'routed', 'outgoing', 'terminal_packet', 'read_states', 'terminal_states', 'scores', 'shift', 'diagnostic_features'):
                    np.testing.assert_array_equal(raw[key][g, 0], original[key][g, 1])
                np.testing.assert_array_equal(raw['write_states'][g, 0, [0, 1, 2, 6]], original['write_states'][g, 1])
                clean = dict(entry, writer={k: v for k, v in writer.items() if not k.startswith('pulse_')})
                same(clean, old)
            cells.append(entry)
        entries.append(cells)
        np.testing.assert_array_equal(raw['read_states'][g, 0], raw['read_states'][g, 1])
        np.testing.assert_array_equal(raw['write_states'][g, 0, :3], raw['write_states'][g, 1, :3])
        np.testing.assert_array_equal(raw['terminal_states'][g, 0, 0], raw['terminal_states'][g, 1, 0])
    same(meta['cycles'], entries)
    assert np.max(maxima[:3]) <= 1e-10
    return dict(passes=True, full_physics_replayed=bool(replay), diagnostic_cycles=8,
        writer_paths=8, reader_paths=16, original_U1_reproductions=4,
        matched_phase_fingerprints=40, initial_reader_max_abs=float(maxima[0]),
        writer_max_abs=float(maxima[1]), final_reader_max_abs=float(maxima[2]),
        feature_max_abs=float(maxima[3]), actual_lineage_outcomes_used=False)
