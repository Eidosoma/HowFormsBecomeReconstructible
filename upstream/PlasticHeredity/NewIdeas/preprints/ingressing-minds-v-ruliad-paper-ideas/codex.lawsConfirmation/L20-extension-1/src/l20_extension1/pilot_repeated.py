# D162 literal adapter: new cohort/namespaces only; inherited physics unchanged.
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
TAG = 'l20-extension1-pilot64-v1'
BLOCKS, FUTURES = tuple(range(100000, 100064)), tuple(range(4))
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
