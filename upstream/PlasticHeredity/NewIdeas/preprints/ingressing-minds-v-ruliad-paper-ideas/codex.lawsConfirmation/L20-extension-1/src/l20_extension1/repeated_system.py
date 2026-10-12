"""D142: fixed F0/host, four new noise namespaces, unchanged D141 physics."""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import numpy as np
from laws_confirmation import l20_guide_renewal as old
from laws_confirmation import l15_repair_speed_run as io
from laws_confirmation.io import sha256_file
from laws_confirmation.l20_three_rewrite import observations
from . import diagnostics as dev

ROOT = dev.ROOT
TAG = 'l20-extension1-repeated-futures-v1'
SOURCE_RUN = 'l20_extension1_heldout_v1_attempt1'
SOURCE_COMPLETE_SHA = '818395b38b2203f0bce8122cf56695590e54d8f870622dfa0608a3f40253f918'
BLOCKS, FUTURES = tuple(range(90000, 90016)), tuple(range(4))
DISPOSABLE = 514240
CASES = ((0, 'translated'), (0, 'aligned'), (1, 'translated'), (1, 'aligned'))
CONFIG = old.CONFIG


def validate(index, life, future):
    if type(index) is not int or index not in BLOCKS + (DISPOSABLE,):
        raise ValueError('declared original or disposable block required')
    if type(life) is not int or life not in range(4) or type(future) is not int or future not in FUTURES:
        raise ValueError('declared life and fresh future ID required')


def namespace(future):
    if type(future) is not int or future not in FUTURES:
        raise ValueError('four future IDs only')
    return f'{TAG}:future{future}'


def rng(index, life, future, phase):
    validate(index, life, future)
    return old.generator(namespace(future), index, life, phase)


def source_paths(index):
    validate(index, 0, 0)
    directory = ROOT / ('tmp' if index == DISPOSABLE else 'outputs') / (SOURCE_RUN + '_benchmark' if index == DISPOSABLE else SOURCE_RUN)
    return directory / f'lineage_{index}.npz', directory / f'lineage_{index}.json'


def load_source(index):
    arrays, meta_path = source_paths(index)
    if index == DISPOSABLE:
        expected = io.read_json(ROOT/'tmp'/f'{SOURCE_RUN}_benchmark.json')['artifact_sha256']
    else:
        complete = ROOT/'runs'/SOURCE_RUN/'COMPLETE.json'
        assert sha256_file(complete) == SOURCE_COMPLETE_SHA
        expected = io.read_json(complete)['output_sha256']
    for path in (arrays, meta_path):
        assert sha256_file(path) == expected[str(path)]
    meta = io.read_json(meta_path)
    assert meta['index'] == index and meta['config'] == asdict(CONFIG)
    with np.load(arrays, allow_pickle=False) as raw:
        packets, guide = raw['founder_packets'], raw['guide']
    assert packets.shape == (4, 2, 2048) and packets.dtype == np.uint8
    assert guide.shape == (4, 2, 16, 16) and guide.dtype == np.float64
    for life in range(4):
        dev.validate_guide(guide[life])
        ctx = old.context(index)
        expected_host = dict(index=index, tissue=asdict(ctx['tissue']), ladder=asdict(ctx['ladder']), blueprint=asdict(ctx['bp']))
        # JSON preserves the values of tuple-valued host settings as lists.
        assert meta['lives'][life]['host'] == json.loads(json.dumps(expected_host))
    packets.setflags(write=False); guide.setflags(write=False)
    return packets, guide


def simulate(index, life, future, founder_packets, guide, order=CASES):
    validate(index, life, future)
    if founder_packets.shape != (2, 2048) or founder_packets.dtype != np.uint8:
        raise ValueError('only two ordinary source records may enter')
    if len(order) != 4 or set(order) != set(CASES):
        raise ValueError('complete primary condition panel required')
    dev.validate_guide(guide)
    ctx = old.context(index)
    random = lambda phase: rng(index, life, future, phase)
    paths, entries = {}, {}
    for role, writer in order:
        packet = founder_packets[role].tobytes()
        rows, records = [], []
        for g in (1, 2, 3):
            routed, scores, selector = old.route(packet, 'learned', guide)
            read, rm = old.read_selected(routed, ctx, random(f'g{g}:birth'), random(f'g{g}:read'), CONFIG)
            shift = np.asarray(divmod(int(random(f'g{g}:source_shift').integers(1, 256)), 16), dtype=np.int64)
            write, wm = old.write_streams(read[-1], ctx, random(f'g{g}:source_write'), writer, shift, CONFIG)
            output = old.encode(old.record(write[-1, 2]))
            rows.append(dict(incoming=np.frombuffer(packet, np.uint8), routed=np.frombuffer(routed, np.uint8),
                outgoing=np.frombuffer(output, np.uint8), scores=scores, read_states=read, write_states=write, shift=shift))
            records.append(dict(generation=g, writer=writer, selector=selector, reader=rm, writer_details=wm,
                input_sha256=hashlib.sha256(packet).hexdigest(), output_sha256=hashlib.sha256(output).hexdigest(),
                erased_before_writing=True, ordinary_packet_bytes=2048))
            packet = output
        terminal_packet, scores, selector = old.route(packet, 'learned', guide)
        terminal, reader = old.read_selected(terminal_packet, ctx, random('terminal:birth'), random('terminal:read'), CONFIG, times=CONFIG.times)
        paths[role, writer] = {k: np.stack([r[k] for r in rows]) for k in rows[0]} | dict(
            terminal_input=np.frombuffer(packet, np.uint8), terminal_packet=np.frombuffer(terminal_packet, np.uint8),
            terminal_scores=scores, terminal_states=terminal)
        entries[role, writer] = dict(generations=records, terminal=dict(selector=selector, reader=reader))
    raw = {k: np.stack([paths[c][k] for c in CASES]) for k in paths[CASES[0]]}
    raw.update(founder_packets=founder_packets.copy(), guide=guide.copy(), targets=dev.targets())
    raw['values'] = observations(raw['read_states'], raw['targets'], CASES, CONFIG)
    raw['terminal_values'] = observations(raw['terminal_states'], raw['targets'], CASES, CONFIG)
    meta = dict(index=index, life=life, future=future, namespace=namespace(future), config=asdict(CONFIG),
        cases=[list(c) for c in CASES], paths=[entries[c] for c in CASES],
        host=dict(index=index, tissue=asdict(ctx['tissue']), ladder=asdict(ctx['ladder']), blueprint=asdict(ctx['bp'])),
        guide_sha256=old.GUIDE_SHA256, record_bytes=2048, public_guide_bytes=4096,
        source_records_reused=True, source_hosts_reused=True, old_lineage_states_reused=False,
        fresh_future_noise=True, guide_refitted=False, parent_state_access=False)
    return raw, meta
