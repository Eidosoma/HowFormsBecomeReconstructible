"""Independent D177 serial replay and saved-only checks; no production stepping."""
from dataclasses import asdict
import hashlib
import numpy as np
from laws_confirmation import l20_guide_renewal as old
from laws_confirmation.io import canonical_digest

old.context(514240)  # Resolve native dependency paths in a fresh audit process.
prior = old.checker()
physics = prior.physics
TAG = 'l20-extension1-recipient-identity-v1'
CASES = ((0, 'translated'), (0, 'aligned'), (1, 'translated'), (1, 'aligned'))
HOSTS = (514240, 90000, 90015)
GUIDE = '59459443afbb634446a72526c13d6dc2359a750aea3d923563793840e9998b4c'


def check(raw, meta, founders, guide, replay):
    cfg = old.CONFIG
    assert type(replay) is bool
    host, role, writer = (meta[k] for k in ('recipient', 'role', 'writer'))
    assert host in HOSTS and (role, writer) in CASES and meta['host']['index'] == host
    tissue, ladder, bp = physics.parameters(meta['host'])
    assert set(meta) == {'schema', 'source_index', 'life', 'recipient', 'role', 'writer', 'namespace',
        'config', 'host', 'generations', 'terminal', 'guide_sha256', 'record_bytes', 'source_later_states_used',
        'recipient_identity_in_seed', 'new_main_founders', 'new_predictors'}
    assert meta['schema'] == 'd177_disposable_path_v1'
    assert meta['source_index'] == 514240 and meta['life'] == 0 and meta['namespace'] == TAG
    assert meta['guide_sha256'] == GUIDE == hashlib.sha256(guide.astype('<f8').tobytes()).hexdigest()
    assert meta['record_bytes'] == 2048
    assert meta['source_later_states_used'] is meta['recipient_identity_in_seed'] is False
    assert meta['new_main_founders'] == meta['new_predictors'] == 0
    prior.nested(meta['config'], asdict(cfg))
    shapes = dict(founder_packet=(2048,), guide=(2,16,16), targets=(2,16,16),
        incoming=(3,2048), routed=(3,2048), outgoing=(3,2048), scores=(3,2,16,16),
        read_states=(3,len(cfg.read_times),3,16,16), write_states=(3,len(cfg.source_times),4,16,16),
        shift=(3,2), terminal_input=(2048,), terminal_packet=(2048,),
        terminal_scores=(2,16,16), terminal_states=(len(cfg.times),3,16,16),
        values=(3,len(cfg.read_times),12), terminal_values=(len(cfg.times),12))
    assert set(raw) == set(shapes)
    bytekeys = ('founder_packet', 'incoming', 'routed', 'outgoing', 'terminal_input', 'terminal_packet')
    for k, shape in shapes.items():
        dtype = np.uint8 if k in bytekeys else np.int64 if k == 'shift' else np.float64
        assert raw[k].shape == shape and raw[k].dtype == dtype and np.isfinite(raw[k]).all()
    np.testing.assert_array_equal(raw['founder_packet'], founders[role])
    np.testing.assert_array_equal(raw['guide'], guide)
    np.testing.assert_array_equal(raw['targets'], prior.prior.targets())
    random = lambda phase: physics.generator(TAG, 514240, 0, phase)
    worst = dict(reader_max_abs=0., writer_max_abs=0., terminal_max_abs=0., selector_max_abs=0., metric_max_abs=0.)
    entries = []
    packet = founders[role].tobytes()
    for gi in range(3):
        g = gi+1
        assert raw['incoming'][gi].tobytes() == packet
        routed, scores, selector = prior.prior.select(packet, guide)
        assert raw['routed'][gi].tobytes() == routed
        worst['selector_max_abs'] = max(worst['selector_max_abs'], physics.compare(raw['scores'][gi], scores))
        reads, rm = prior.read_trace(routed, tissue, ladder, bp, random(f'g{g}:birth'), random(f'g{g}:read'), cfg, replay=replay)
        np.testing.assert_array_equal(raw['read_states'][gi, 0], reads[0])
        if replay:
            worst['reader_max_abs'] = max(worst['reader_max_abs'], physics.compare(raw['read_states'][gi], reads))
        shift = np.array(divmod(int(random(f'g{g}:source_shift').integers(1,256)), 16), np.int64)
        np.testing.assert_array_equal(raw['shift'][gi], shift)
        writes, wm = prior.write_trace(raw['read_states'][gi,-1], tissue, ladder, random(f'g{g}:source_write'),
            writer, shift, cfg, True, replay)
        np.testing.assert_array_equal(raw['write_states'][gi, 0], writes[0])
        if replay:
            worst['writer_max_abs'] = max(worst['writer_max_abs'], physics.compare(raw['write_states'][gi], writes))
        ref = raw['write_states'][gi,-1,2]
        assert np.tanh(ref).std() > 1e-9
        outgoing = prior.packet(prior.project(np.tanh(ref)))
        assert raw['outgoing'][gi].tobytes() == outgoing
        entries.append(dict(generation=g, selector=selector, reader=rm, writer=wm,
            input_sha256=prior.sha(packet), output_sha256=prior.sha(outgoing)))
        packet = outgoing
    prior.nested(meta['generations'], entries)
    routed, scores, selector = prior.prior.select(packet, guide)
    assert raw['terminal_input'].tobytes() == packet and raw['terminal_packet'].tobytes() == routed
    worst['selector_max_abs'] = max(worst['selector_max_abs'], physics.compare(raw['terminal_scores'], scores))
    terminal, rm = prior.read_trace(routed, tissue, ladder, bp, random('terminal:birth'), random('terminal:read'),
        cfg, times=cfg.times, replay=replay)
    np.testing.assert_array_equal(raw['terminal_states'][0], terminal[0])
    if replay:
        worst['terminal_max_abs'] = physics.compare(raw['terminal_states'], terminal)
    prior.nested(meta['terminal'], dict(selector=selector, reader=rm))
    for out, key in (('values','read_states'), ('terminal_values','terminal_states')):
        observed = prior.observe(raw[key][None], raw['targets'], ((role,writer),), cfg)[0]
        worst['metric_max_abs'] = max(worst['metric_max_abs'], physics.compare(raw[out], observed))
    assert worst['selector_max_abs'] <= 1e-12 and worst['metric_max_abs'] <= 1e-12
    return dict(passes=True, full_physics_replayed=replay, generation_paths=3, terminal_paths=1,
        selectors=4, recipient_in_rng=False, source_later_states_used=False, **worst)


def compare_report(summary, rows):
    assert set(rows) == {(h,r,w) for h in HOSTS for r,w in CASES}
    assert summary['status'] == 'NATIVE_RECIPIENT_CONTRAST_ABSENT'
    assert summary['contexts'] == list(HOSTS) and summary['source_records'] == 2
    assert summary['disposable_paths'] == 12 and summary['generation_paths'] == 36 and summary['terminal_readers'] == 12
    assert summary['main_population_pilot_started'] is summary['prospective_evidence'] is summary['automatic_successor'] is False
    assert summary['fitted_predictors'] == summary['new_main_founders'] == 0
    assert len(summary['comparisons']) == 12
    for i, (h,r,w) in enumerate((h,r,w) for h in HOSTS for r,w in CASES):
        raw, meta = rows[h,r,w]; base, bm = rows[514240,r,w]
        actual = summary['comparisons'][i]
        expected = dict(recipient=h, role=r, writer=w)
        for out, key in (('read_max_abs','read_states'), ('write_max_abs','write_states'), ('terminal_max_abs','terminal_states')):
            expected[out] = max(abs(float(x)-float(y)) for x,y in zip(raw[key].flat,base[key].flat))
        a = np.frombuffer(raw['outgoing'].tobytes(), '<f8')
        b = np.frombuffer(base['outgoing'].tobytes(), '<f8')
        expected['outgoing_max_abs'] = float(np.max(np.abs(a-b)))
        expected['outgoing_byte_differences'] = sum(x != y for x,y in zip(raw['outgoing'].tobytes(),base['outgoing'].tobytes()))
        val = raw['terminal_values'][-1]; bv = base['terminal_values'][-1]
        expected.update(terminal_preference=float(val[0]-val[1]), baseline_preference=float(bv[0]-bv[1]),
            preference_change=float(val[0]-val[1]-bv[0]+bv[1]))
        sels = [x['selector'] for x in meta['generations']]+[meta['terminal']['selector']]
        bs = [x['selector'] for x in bm['generations']]+[bm['terminal']['selector']]
        expected['selector_changes'] = sum((s['inferred_family'],s['chosen_forward_shift']) !=
            (t['inferred_family'],t['chosen_forward_shift']) for s,t in zip(sels,bs))
        expected['family_changes'] = sum(s['inferred_family'] != t['inferred_family'] for s,t in zip(sels,bs))
        expected['read_initial_states_equal'] = bool(np.array_equal(raw['read_states'][:,0],base['read_states'][:,0]))
        expected['terminal_initial_state_equal'] = bool(np.array_equal(raw['terminal_states'][0],base['terminal_states'][0]))
        prior.nested(actual,expected)
        assert expected['read_initial_states_equal'] and expected['terminal_initial_state_equal']
        for e, bentry in zip(meta['generations'],bm['generations']):
            for key in ('birth_rng','read_rng'):
                assert e['reader'][key] == bentry['reader'][key]
            assert e['writer']['noise_rng'] == bentry['writer']['noise_rng']
        assert meta['terminal']['reader']['birth_rng'] == bm['terminal']['reader']['birth_rng']
        assert meta['terminal']['reader']['read_rng'] == bm['terminal']['reader']['read_rng']
    return dict(passes=True, comparisons=12, paired_randomness_verified=True,
        main_outcome_arrays_used=False, fitted_models=0, uncertainty_claim=False)
