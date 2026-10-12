"""D143: full crossing of existing D142 address and other-noise histories."""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import numpy as np
from laws_confirmation import l20_guide_renewal as old
from laws_confirmation import l15_repair_speed_run as io
from laws_confirmation.io import sha256_file
from laws_confirmation.l20_three_rewrite import observations
from . import diagnostics as dev, repeated_system as source

ROOT = dev.ROOT
TAG = 'l20-extension1-crossed-address-noise-v1'
SOURCE_RUN = 'l20_extension1_repeated_futures_v1_attempt1'
SOURCE_COMPLETE_SHA = 'a04ec3a673e4794ecad5c6662891c30b74ab2e76a2731897b8efc7568416ad72'
BLOCKS, FUTURES = tuple(range(90000, 90016)), tuple(range(4))
DISPOSABLE = 514240
CASES = ((0, 'translated'), (0, 'aligned'), (1, 'translated'), (1, 'aligned'))
CONFIG = old.CONFIG


PHASES = tuple(f'g{g}:{p}' for g in (1, 2, 3) for p in ('birth', 'read', 'source_shift', 'source_write')) + ('terminal:birth', 'terminal:read')


def validate(index, life, noise, address):
    source.validate(index, life, noise)
    source.validate(index, life, address)


def namespace(level):
    return source.namespace(level)


def rng(index, life, noise, address, phase):
    validate(index, life, noise, address)
    if phase not in PHASES:
        raise ValueError('declared original phase required')
    level = address if phase.endswith(':source_shift') else noise
    return source.rng(index, life, level, phase)


def source_paths(index):
    validate(index, 0, 0, 0)
    directory = ROOT / ('tmp' if index == DISPOSABLE else 'outputs') / (SOURCE_RUN + '_benchmark' if index == DISPOSABLE else SOURCE_RUN)
    return directory / f'block_{index}.npz', directory / f'block_{index}.json'


def load_diagonal(index):
    arrays, metadata = source_paths(index)
    if index == DISPOSABLE:
        receipt = io.read_json(ROOT/'tmp'/f'{SOURCE_RUN}_benchmark.json')
        expected = receipt['artifact_sha256']
    else:
        path = ROOT/'runs'/SOURCE_RUN/'COMPLETE.json'
        assert sha256_file(path) == SOURCE_COMPLETE_SHA
        expected = io.read_json(path)['output_sha256']
    for path in (arrays, metadata):
        assert sha256_file(path) == expected[str(path)]
    raw, meta = io.load_npz(arrays), io.read_json(metadata)
    assert meta['index'] == index and meta['config'] == asdict(CONFIG)
    assert all(x.shape[:2] == (4, 4) for x in raw.values())
    return raw, meta


def load_source(index):
    return source.load_source(index)


def simulate(index, life, noise, address, founder_packets, guide, order=CASES):
    validate(index, life, noise, address)
    if founder_packets.shape != (2, 2048) or founder_packets.dtype != np.uint8:
        raise ValueError('only two ordinary source records may enter')
    if len(order) != 4 or set(order) != set(CASES):
        raise ValueError('complete primary condition panel required')
    dev.validate_guide(guide)
    ctx = old.context(index)
    random = lambda phase: rng(index, life, noise, address, phase)
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
    meta = dict(index=index, life=life, noise_id=noise, address_id=address,
        noise_namespace=namespace(noise), address_namespace=namespace(address), config=asdict(CONFIG),
        cases=[list(c) for c in CASES], paths=[entries[c] for c in CASES],
        host=dict(index=index, tissue=asdict(ctx['tissue']), ladder=asdict(ctx['ladder']), blueprint=asdict(ctx['bp'])),
        guide_sha256=old.GUIDE_SHA256, record_bytes=2048, public_guide_bytes=4096,
        source_records_reused=True, source_hosts_reused=True, old_lineage_states_reused=False,
        recombined_existing_streams=True, guide_refitted=False, parent_state_access=False)
    return raw, meta
