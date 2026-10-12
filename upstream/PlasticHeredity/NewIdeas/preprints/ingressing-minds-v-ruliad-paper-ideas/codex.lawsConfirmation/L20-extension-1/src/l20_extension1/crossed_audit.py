"""Independent D143 crossed-stream/reset/packet checks and D142/alias bridges."""
from dataclasses import asdict
import json
import numpy as np
from laws_confirmation import l20_guide_renewal as old

prior = old.checker()
physics = prior.physics
TAG = 'l20-extension1-repeated-futures-v1'
CASES = ((0, 'translated'), (0, 'aligned'), (1, 'translated'), (1, 'aligned'))
GUIDE_SHA = '59459443afbb634446a72526c13d6dc2359a750aea3d923563793840e9998b4c'


def check(raw, meta, founders, guide, replay=False):
    cfg = old.CONFIG
    assert set(meta) in ({'index', 'life', 'noise_id', 'address_id', 'noise_namespace', 'address_namespace', 'config', 'cases', 'paths', 'host',
        'guide_sha256', 'record_bytes', 'public_guide_bytes', 'source_records_reused', 'source_hosts_reused',
        'old_lineage_states_reused', 'recombined_existing_streams', 'guide_refitted', 'parent_state_access'},
        {'index', 'life', 'noise_id', 'address_id', 'noise_namespace', 'address_namespace', 'config', 'cases', 'paths', 'host',
        'guide_sha256', 'record_bytes', 'public_guide_bytes', 'source_records_reused', 'source_hosts_reused',
        'old_lineage_states_reused', 'recombined_existing_streams', 'guide_refitted', 'parent_state_access', 'replay'})
    index, life, noise, address = (meta[k] for k in ('index', 'life', 'noise_id', 'address_id'))
    assert type(index) is int and index in (*range(90000, 90016), 514240)
    assert type(life) is int and 0 <= life < 4
    assert type(noise) is int and 0 <= noise < 4 and type(address) is int and 0 <= address < 4
    tag, address_tag = f'{TAG}:future{noise}', f'{TAG}:future{address}'
    assert meta['noise_namespace'] == tag and meta['address_namespace'] == address_tag
    assert meta['host']['index'] == index
    prior.nested(meta['config'], asdict(cfg)); prior.nested(meta['cases'], [list(c) for c in CASES])
    assert meta['guide_sha256'] == prior.sha(guide.astype('<f8').tobytes()) == GUIDE_SHA
    for k in ('source_records_reused', 'source_hosts_reused', 'recombined_existing_streams'):
        assert meta[k] is True
    for k in ('old_lineage_states_reused', 'guide_refitted', 'parent_state_access'):
        assert meta[k] is False
    assert (meta['record_bytes'], meta['public_guide_bytes']) == (2048, 4096)
    shapes = dict(founder_packets=(2, 2048), guide=(2, 16, 16), targets=(2, 16, 16),
        incoming=(4, 3, 2048), routed=(4, 3, 2048), outgoing=(4, 3, 2048), scores=(4, 3, 2, 16, 16),
        read_states=(4, 3, len(cfg.read_times), 3, 16, 16), write_states=(4, 3, len(cfg.source_times), 4, 16, 16),
        shift=(4, 3, 2), terminal_input=(4, 2048), terminal_packet=(4, 2048),
        terminal_scores=(4, 2, 16, 16), terminal_states=(4, len(cfg.times), 3, 16, 16),
        values=(4, 3, len(cfg.read_times), 12), terminal_values=(4, len(cfg.times), 12))
    assert set(raw) == set(shapes)
    for k, shape in shapes.items():
        dtype = np.uint8 if k in ('founder_packets', 'incoming', 'routed', 'outgoing', 'terminal_input', 'terminal_packet') else np.int64 if k == 'shift' else np.float64
        assert raw[k].shape == shape and raw[k].dtype == dtype and np.isfinite(raw[k]).all()
    np.testing.assert_array_equal(raw['founder_packets'], founders)
    np.testing.assert_array_equal(raw['guide'], guide)
    np.testing.assert_array_equal(raw['targets'], prior.prior.targets())
    tissue, ladder, bp = physics.parameters(meta['host'])
    ctx = old.context(index)
    prior.nested(meta['host'], dict(index=index, tissue=asdict(ctx['tissue']), ladder=asdict(ctx['ladder']), blueprint=asdict(ctx['bp'])))
    random = lambda phase: physics.generator(address_tag if phase.endswith(':source_shift') else tag, index, life, phase)
    worst = dict(reader_max_abs=0., writer_max_abs=0., terminal_max_abs=0., selector_max_abs=0., metric_max_abs=0.)
    entries = []
    for ci, (role, writer) in enumerate(CASES):
        packet = founders[role].tobytes(); generations = []
        for gi in range(3):
            g = gi + 1
            assert raw['incoming'][ci, gi].tobytes() == packet
            routed, scores, selector = prior.prior.select(packet, guide)
            assert raw['routed'][ci, gi].tobytes() == routed
            worst['selector_max_abs'] = max(worst['selector_max_abs'], physics.compare(raw['scores'][ci, gi], scores))
            reads, rm = prior.read_trace(routed, tissue, ladder, bp, random(f'g{g}:birth'), random(f'g{g}:read'), cfg, replay=replay)
            np.testing.assert_array_equal(raw['read_states'][ci, gi, 0], reads[0])
            if replay: worst['reader_max_abs'] = max(worst['reader_max_abs'], physics.compare(raw['read_states'][ci, gi], reads))
            shift = np.asarray(divmod(int(random(f'g{g}:source_shift').integers(1, 256)), 16), np.int64)
            np.testing.assert_array_equal(raw['shift'][ci, gi], shift)
            start = raw['read_states'][ci, gi, -1]
            writes, wm = prior.write_trace(start, tissue, ladder, random(f'g{g}:source_write'), writer, shift, cfg, True, replay)
            np.testing.assert_array_equal(raw['write_states'][ci, gi, 0], writes[0])
            if replay: worst['writer_max_abs'] = max(worst['writer_max_abs'], physics.compare(raw['write_states'][ci, gi], writes))
            ref = raw['write_states'][ci, gi, -1, 2]
            assert np.tanh(ref).std() > 1e-9
            outgoing = prior.packet(prior.project(np.tanh(ref)))
            assert raw['outgoing'][ci, gi].tobytes() == outgoing
            generations.append(dict(generation=g, writer=writer, selector=selector, reader=rm, writer_details=wm,
                input_sha256=prior.sha(packet), output_sha256=prior.sha(outgoing), erased_before_writing=True, ordinary_packet_bytes=2048))
            packet = outgoing
        routed, scores, selector = prior.prior.select(packet, guide)
        assert raw['terminal_input'][ci].tobytes() == packet and raw['terminal_packet'][ci].tobytes() == routed
        worst['selector_max_abs'] = max(worst['selector_max_abs'], physics.compare(raw['terminal_scores'][ci], scores))
        terminal, rm = prior.read_trace(routed, tissue, ladder, bp, random('terminal:birth'), random('terminal:read'), cfg, times=cfg.times, replay=replay)
        np.testing.assert_array_equal(raw['terminal_states'][ci, 0], terminal[0])
        if replay: worst['terminal_max_abs'] = max(worst['terminal_max_abs'], physics.compare(raw['terminal_states'][ci], terminal))
        entries.append(dict(generations=generations, terminal=dict(selector=selector, reader=rm)))
    prior.nested(meta['paths'], entries)
    for key, state in (('values', 'read_states'), ('terminal_values', 'terminal_states')):
        value = prior.observe(raw[state], raw['targets'], CASES, cfg)
        worst['metric_max_abs'] = max(worst['metric_max_abs'], physics.compare(raw[key], value))
    assert worst['selector_max_abs'] <= 1e-12 and worst['metric_max_abs'] <= 1e-12
    for role in (0, 1):
        a, b = 2*role, 2*role+1
        np.testing.assert_array_equal(raw['read_states'][a, 0], raw['read_states'][b, 0])
        np.testing.assert_array_equal(raw['write_states'][a, 0, 1], raw['write_states'][b, 0, 1])
    if 'replay' in meta:
        assert meta['replay']['full_dynamics_replayed'] is True
        for k in worst:
            assert 0 <= meta['replay'][k] <= (1e-12 if k in ('selector_max_abs', 'metric_max_abs') else 1e-10)
    return dict(full_dynamics_replayed=replay, **worst, generation_paths=12, terminal_paths=4,
        selector_decisions=16, new_founders=0, packet_lineage=True, fresh_reset=True)


def diagonal(raw, meta, old_raw, old_meta):
    n = meta['noise_id']
    assert meta['address_id'] == n and old_meta['future'] == n
    assert set(raw) == set(old_raw)
    for key in raw:
        np.testing.assert_array_equal(raw[key], old_raw[key])
    for key in ('paths', 'host', 'config', 'cases', 'guide_sha256', 'record_bytes', 'public_guide_bytes'):
        # The live dataclasses contain tuples; saved JSON contains lists.
        # Normalize only that serialization distinction, without tolerances.
        assert json.loads(json.dumps(meta[key])) == json.loads(json.dumps(old_meta[key]))
    assert meta['noise_namespace'] == meta['address_namespace'] == old_meta['namespace']
    return True


def crossed_panel(raw, meta):
    # block axes: life, noise, address, condition, ...
    assert all(v.shape[:3] == (4, 4, 4) for v in raw.values())
    unique_addresses = []
    for life in range(4):
        shifts = [raw['shift'][life, 0, a, 0].tobytes() for a in range(4)]
        unique_addresses.append(len(set(shifts)))
        for noise in range(4):
            for address in range(4):
                entry = meta['lives'][life][noise][address]
                assert (entry['life'], entry['noise_id'], entry['address_id']) == (life, noise, address)
                np.testing.assert_array_equal(raw['shift'][life, noise, address], raw['shift'][life, 0, address])
                for role in (0, 1):
                    for ci in (2*role, 2*role+1):
                        np.testing.assert_array_equal(raw['read_states'][life, noise, address, ci, 0],
                                                      raw['read_states'][life, noise, 0, ci, 0])
                        np.testing.assert_array_equal(raw['write_states'][life, noise, address, ci, 0, :2],
                                                      raw['write_states'][life, noise, 0, ci, 0, :2])
                    ci = 2*role+1
                    for key in raw:
                        if key in ('founder_packets', 'guide', 'targets', 'shift'):
                            continue
                        np.testing.assert_array_equal(raw[key][life, noise, address, ci],
                                                      raw[key][life, noise, 0, ci])
        for n in range(4):
            for other in range(n+1, 4):
                assert not np.array_equal(raw['read_states'][life, n, 0, 0, 0, 0],
                                          raw['read_states'][life, other, 0, 0, 0, 0])
    return dict(labelled_terminal_cells=256, nominal_distinct_condition_stream_cells=160,
        aligned_address_aliases=96, diagonal_cells=64, novel_ordinary_off_diagonal_cells=96,
        distinct_address_sequences_per_life=unique_addresses, new_founders=0)
