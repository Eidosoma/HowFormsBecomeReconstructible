# D162 literal adapter: new cohort/namespaces only; inherited physics unchanged.
"""Prospective diagnostic copies; only public conditions, F0 and guide enter."""
from dataclasses import asdict
import numpy as np
from laws_confirmation import l20_guide_renewal as old
from .diagnostics import (CONFIG, CASES, BRANCHES, INITIAL_FEATURES, CYCLE_FEATURES,
    record_features, terminal_features, partial_shuffle, validate_guide, observer_features)

TAG = 'l20-extension1-pilot64-v1:diagnostics'

def validate_spec(cohort, index):
    if type(index) is not int or not ((cohort == 'heldout' and 100000 <= index < 100064) or
                                     (cohort == 'disposable' and index == 514240)):
        raise ValueError('declared held-out/disposable founder required')
    return index

def rng(cohort, index, life, phase):
    validate_spec(cohort, index)
    if type(life) is not int or not 0 <= life < 4:
        raise ValueError('declared life required')
    return old.generator(f'{TAG}:{cohort}', index, life, phase)


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
