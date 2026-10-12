# D162 literal adapter: new cohort/namespaces only; inherited physics unchanged.
"""Independent diagnostic/feature/model reconstruction; no production simulator calls."""
from __future__ import annotations
from dataclasses import asdict
import numpy as np
from laws_confirmation import l20_guide_renewal as old
from laws_confirmation import l15_repair_speed_run as io
from . import diagnostics as p

prior = old.checker()
physics = prior.physics
nested = physics.nested
GUIDE_SHA = '59459443afbb634446a72526c13d6dc2359a750aea3d923563793840e9998b4c'
TAG = 'l20-extension1-pilot64-v1:diagnostics'
CASES = ((0, 'translated'), (0, 'aligned'), (1, 'translated'), (1, 'aligned'))


def corr(field, templates):
    centered = field - field.mean()
    scale = np.sqrt(np.mean(centered**2))
    values = np.zeros((2, 16, 16))
    if scale:
        for role in (0, 1):
            target = templates[role] - templates[role].mean()
            values[role] = np.fft.ifft2(np.fft.fft2(centered) * np.conj(np.fft.fft2(target))).real / (256*scale*np.sqrt(np.mean(target**2)))
    return values


def record_features(packet, role, guide):
    field = prior.unpack(packet)
    templates = prior.prior.targets()
    best = corr(field, templates).max(axis=(1, 2))
    routed, guide_scores, _ = prior.prior.select(packet, guide)
    f = prior.unpack(routed); f = f-f.mean(); scale = np.sqrt(np.mean(f*f))
    canonical = np.sum(templates*f, axis=(1, 2))/(256*scale) if scale else np.zeros(2)
    guide_best = guide_scores.max(axis=(1, 2))
    return np.array([best[role], best[role]-best[1-role], guide_best[role]-guide_best[1-role], canonical[role]-canonical[1-role]])


def terminal_features(v, role):
    own = prior.prior.targets()[role]; alternative = prior.prior.targets()[1-role]
    own_count = np.count_nonzero(((v > 0) == (own > 0)) & (np.abs(v) > .2))
    alternative_count = np.count_nonzero(((v > 0) == (alternative > 0)) & (np.abs(v) > .2))
    return np.array([(own_count-alternative_count)/256, np.sqrt(np.sum(v*v)/256)])


def check_life(raw, meta, founders, guide, replay=True):
    cohort, index, life = meta['cohort'], meta['index'], meta['life']
    legal = tuple(('heldout', i) for i in range(100000, 100064)) + (('disposable', 514240),)
    assert type(index) is int and (cohort, index) in legal and type(life) is int and 0 <= life < 4
    host = index
    assert meta['host']['index'] == host
    assert set(meta) in ({'cohort','index','life','host','tag','config','cases','branches','cycles','guide_sha256',
                         'predictor_has_parent_state','diagnostic_to_lineage'},
                        {'cohort','index','life','host','tag','config','cases','branches','cycles','guide_sha256',
                         'predictor_has_parent_state','diagnostic_to_lineage','replay'})
    assert meta['tag'] == f'{TAG}:{cohort}' and meta['guide_sha256'] == GUIDE_SHA
    assert meta['predictor_has_parent_state'] is False and meta['diagnostic_to_lineage'] is False
    nested(meta['config'], asdict(p.CONFIG)); nested(meta['cases'], [list(c) for c in CASES]); nested(meta['branches'], ['U0','U1','C1'])
    tissue, ladder, bp = physics.parameters(meta['host'])
    assert prior.sha(guide.astype('<f8').tobytes()) == GUIDE_SHA
    cfg = p.CONFIG
    shapes = dict(founder_packets=(2,2048), guide=(2,16,16), sites=(64,), permutation=(64,),
        input=(4,3,2048), routed=(4,3,2048), outgoing=(4,3,2048), terminal_packet=(4,3,2048),
        read_states=(4,3,len(cfg.read_times),3,16,16), write_states=(4,3,len(cfg.source_times),4,16,16),
        terminal_states=(4,3,len(cfg.times),3,16,16), scores=(4,3,2,2,16,16), shift=(4,3,2),
        initial_features=(4,4), diagnostic_features=(4,3,6), input_strength=(4,3,2), changed_sites=(4,))
    assert set(raw) == set(shapes)
    for key, shape in shapes.items():
        dtype = np.uint8 if key in ('founder_packets','input','routed','outgoing','terminal_packet') else np.int64 if key in ('sites','permutation','shift','changed_sites') else np.float64
        assert raw[key].shape == shape and raw[key].dtype == dtype and np.isfinite(raw[key]).all(), key
    np.testing.assert_array_equal(raw['founder_packets'], founders); np.testing.assert_array_equal(raw['guide'], guide)
    random = lambda phase: physics.generator(f'{TAG}:{cohort}', index, life, phase)
    sites = random('mask').permutation(256)[:64]; permutation = random('permutation').permutation(64)
    np.testing.assert_array_equal(raw['sites'], sites); np.testing.assert_array_equal(raw['permutation'], permutation)
    rmax = wmax = tmax = smax = fmax = 0.; entries = []
    for ci, (role, mode) in enumerate(CASES):
        packet = founders[role].tobytes(); f = prior.unpack(packet).ravel(); shuffled = f.copy()
        for destination, source in zip(sites, sites[permutation]):
            shuffled[destination] = f[source]
        challenged = prior.packet(shuffled.reshape(16,16))
        np.testing.assert_array_equal(np.sort(shuffled), np.sort(f))
        assert raw['changed_sites'][ci] == np.count_nonzero(shuffled != f)
        np.testing.assert_allclose(raw['initial_features'][ci], record_features(packet, role, guide), rtol=0, atol=1e-12)
        case_entries = []
        for bi, incoming in enumerate((packet, packet, challenged)):
            trial = 0 if bi == 0 else 1
            draw = lambda phase: random(f'trial{trial}:{phase}')
            assert raw['input'][ci, bi].tobytes() == incoming
            field = prior.unpack(incoming)
            np.testing.assert_allclose(raw['input_strength'][ci, bi], [np.sum(field)/256, np.sqrt(np.sum(field**2)/256)], atol=1e-14, rtol=0)
            routed, scores, selection = prior.prior.select(incoming, guide)
            assert raw['routed'][ci, bi].tobytes() == routed
            np.testing.assert_allclose(raw['scores'][ci, bi, 0], scores, atol=1e-12, rtol=0)
            smax = max(smax, float(abs(raw['scores'][ci,bi,0]-scores).max()))
            reads, reader = prior.read_trace(routed, tissue, ladder, bp, draw('birth'), draw('read'), cfg, replay=replay)
            np.testing.assert_array_equal(raw['read_states'][ci, bi, 0], reads[0])
            if replay: rmax = max(rmax, physics.compare(raw['read_states'][ci, bi], reads))
            shift = np.array(divmod(int(draw('shift').integers(1,256)),16), np.int64)
            np.testing.assert_array_equal(raw['shift'][ci,bi], shift)
            start = raw['read_states'][ci,bi,-1]
            writes, writer = prior.write_trace(start, tissue, ladder, draw('write'), mode, shift, cfg, replay=replay)
            np.testing.assert_array_equal(raw['write_states'][ci,bi,0], np.concatenate((start, np.zeros((1,16,16)))))
            if replay: wmax = max(wmax, physics.compare(raw['write_states'][ci,bi], writes))
            ref = raw['write_states'][ci,bi,-1,2]; assert np.tanh(ref).std() > 1e-9
            outgoing = prior.packet(prior.project(np.tanh(ref)))
            assert raw['outgoing'][ci,bi].tobytes() == outgoing
            final_packet, scores, final_selection = prior.prior.select(outgoing, guide)
            assert raw['terminal_packet'][ci,bi].tobytes() == final_packet
            np.testing.assert_allclose(raw['scores'][ci,bi,1], scores, atol=1e-12, rtol=0)
            smax = max(smax, float(abs(raw['scores'][ci,bi,1]-scores).max()))
            terminal, final_reader = prior.read_trace(final_packet, tissue, ladder, bp, draw('final_birth'), draw('final_read'), cfg, times=cfg.times, replay=replay)
            np.testing.assert_array_equal(raw['terminal_states'][ci,bi,0], terminal[0])
            if replay: tmax = max(tmax, physics.compare(raw['terminal_states'][ci,bi], terminal))
            expected = np.r_[record_features(outgoing, role, guide), terminal_features(raw['terminal_states'][ci,bi,-1,0], role)]
            np.testing.assert_allclose(raw['diagnostic_features'][ci,bi], expected, atol=1e-12, rtol=0)
            fmax = max(fmax, float(abs(raw['diagnostic_features'][ci,bi]-expected).max()))
            case_entries.append(dict(trial=trial, mode=mode, selector=selection, reader=reader, writer=writer,
                terminal_selector=final_selection, terminal_reader=final_reader))
        entries.append(case_entries)
        # Matched U1/C1 births; independent U0 and final-reader births.
        np.testing.assert_array_equal(raw['read_states'][ci,1,0], raw['read_states'][ci,2,0])
        np.testing.assert_array_equal(raw['terminal_states'][ci,1,0], raw['terminal_states'][ci,2,0])
        assert not np.array_equal(raw['read_states'][ci,0,0], raw['read_states'][ci,1,0])
        for bi in range(3):
            assert not np.array_equal(raw['read_states'][ci,bi,0], raw['terminal_states'][ci,bi,0])
    nested(meta['cycles'], entries)
    for a, b in ((0,1),(2,3)):
        np.testing.assert_array_equal(raw['read_states'][a], raw['read_states'][b])
        np.testing.assert_array_equal(raw['write_states'][a,:,0:2], raw['write_states'][b,:,0:2])
    return dict(diagnostic_cycles=12, reader_paths=24, selectors=24,
        reader_max_abs=rmax, writer_max_abs=wmax, terminal_max_abs=tmax,
        selector_max_abs=smax, feature_max_abs=fmax, full_dynamics_replayed=bool(replay))
