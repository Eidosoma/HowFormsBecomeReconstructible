"""D123 independent packet addressing, reader dynamics, observer and inference."""
from dataclasses import asdict, replace
import hashlib

import numpy as np

from laws_confirmation import l20_three_rewrite as old
from laws_confirmation.io import canonical_digest, sha256_file

prior = old.checker()
physics = prior.physics
compare, nested, generator = physics.compare, physics.nested, physics.generator
TAG = 'l20-source-noise-v1'
MODES = ('noisy', 'quiet')
BASES = ('noisy_body', 'noisy_history', 'quiet_body', 'quiet_history')
KINDS = ('noisy_body', 'noisy_history', 'quiet_body', 'quiet_history',
    'noisy_body_shuffle', 'noisy_history_shuffle', 'quiet_body_shuffle', 'quiet_history_shuffle',
    'noisy_sham', 'quiet_sham', 'noisy_off', 'quiet_off', 'ideal', 'zero')
CASES = tuple((r, k) for r in (0, 1) for k in KINDS)
METRICS = prior.METRICS
packet, unpack, sha = prior.packet, prior.unpack, prior.sha
observe = prior.observe


def check_life(raw, meta, cfg, source, replay=True):
    keys = {'index', 'source_index', 'life', 'config', 'cases', 'times', 'reader_tag', 'source_tag',
        'origin_tag', 'source_birth_checkpoint', 'source_steps', 'source_times', 'source_start_reused',
        'source_noise_reused', 'source_trajectories_new', 'modes', 'sigmas', 'birth_coefficient',
        'writer_inputs', 'writer_rule', 'source_rho', 'incoming_theta_used_for_source',
        'incoming_theta_used_by_writer', 'birth_direct_term_only', 'source_birth_shared_between_roles',
        'source_context', 'source_paths', 'tissue', 'ladder', 'blueprint', 'readers'}
    assert set(meta) in (keys, keys | {'replay'})
    index, life = meta['index'], meta['life']
    assert type(index) is int and index in (*range(65000, 65008), 514223)
    assert type(life) is int and 0 <= life < cfg.lives
    assert meta['source_index'] == (514217 if index == 514223 else index-5000)
    nested(meta['config'], asdict(cfg)); nested(meta['cases'], [list(c) for c in CASES])
    nested(meta['times'], list(cfg.times)); nested(meta['source_times'], [0, 1, 100, 300])
    assert type(meta['source_steps']) is int and meta['source_steps'] == 300
    assert type(meta['source_birth_checkpoint']) is int and meta['source_birth_checkpoint'] == 0
    nested(meta['writer_inputs'], ['V300', 'R300-.998**300*R0'])
    nested(meta['modes'], ['noisy', 'quiet']); nested(meta['sigmas'], [.3, 0.])
    assert meta['writer_rule'] == 'project(snapshot, .3)' and meta['source_rho'] == .002
    assert meta['birth_coefficient'] == .998**300
    for key in ('source_start_reused', 'source_trajectories_new', 'incoming_theta_used_for_source',
                'birth_direct_term_only', 'source_birth_shared_between_roles'):
        assert meta[key] is True
    for key in ('source_noise_reused', 'incoming_theta_used_by_writer'): assert meta[key] is False
    assert meta['reader_tag'] == meta['source_tag'] == TAG and meta['origin_tag'] == 'l20-three-rewrite-v1'
    shapes = dict(targets=(2, 16, 16), source_births=(2, 3, 3, 16, 16), source_packets=(2, 3, 2048),
        source_states=(2, 3, 2, 4, 3, 16, 16), history_fields=(2, 3, 2, 16, 16),
        written_fields=(2, 3, 2, 2, 16, 16), permutations=(2, 3, 256),
        packets=(28, 3, 2048), states=(28, 3, len(cfg.times), 3, 16, 16),
        values=(28, 3, len(cfg.times), 12))
    assert set(raw) == set(shapes)
    for key, shape in shapes.items():
        dtype = np.uint8 if key in ('packets', 'source_packets') else np.int64 if key == 'permutations' else np.float64
        assert raw[key].shape == shape and raw[key].dtype == dtype and np.isfinite(raw[key]).all()
    np.testing.assert_array_equal(raw['targets'], prior.prior.targets())
    np.testing.assert_array_equal(raw['targets'], source['targets'][life])
    sm = meta['source_context']
    assert set(sm) == {'index', 'tissue', 'ladder', 'blueprint'} and sm['index'] == meta['source_index']
    tissue0, sladder, sbp = physics.parameters(sm)
    assert tissue0.sigma == .3 and sbp.rho == .002
    source_maximum = 0.; source_records = []
    for role, ci in ((0, 0), (1, 8)):
        generations = []
        for gi in range(3):
            start = source['generation_states'][life, ci, gi, 0, :3]
            supplied = source['incoming'][life, ci, gi].tobytes()
            np.testing.assert_array_equal(raw['source_births'][role, gi], start)
            assert raw['source_packets'][role, gi].tobytes() == supplied
            np.testing.assert_array_equal(unpack(supplied), source['generation_states'][life, ci, gi, 0, 3])
            entries = []
            for mi, sigma in enumerate((.3, 0.)):
                tissue = replace(tissue0, sigma=sigma); state = tuple(x[None].copy() for x in start)
                saved = [start.copy()]; weighted = np.zeros((1, 16, 16))
                np.testing.assert_array_equal(raw['source_states'][role, gi, mi, 0], start)
                random = generator(TAG, index, life, f'g{gi+1}:source')
                for t in range(1, 301):
                    noise = random.standard_normal((1, 16, 16))
                    if replay:
                        state = physics.step(*state, unpack(supplied), tissue, sladder, 0., sbp.rho, noise)
                        weighted = .998*weighted + .002*state[0]
                        if t in (1, 100, 300): saved.append(np.stack(state)[:, 0])
                if replay:
                    source_maximum = max(source_maximum, compare(raw['source_states'][role, gi, mi], np.stack(saved)))
                    np.testing.assert_allclose(raw['history_fields'][role, gi, mi], weighted[0], rtol=0, atol=1e-13)
                endpoint = raw['source_states'][role, gi, mi, -1]
                history = endpoint[2] - (.998**300)*start[2]
                np.testing.assert_array_equal(raw['history_fields'][role, gi, mi], history)
                for slot, candidate in enumerate((endpoint[0], history)):
                    assert candidate.std() > 1e-9, 'degenerate source: fail rather than exclude'
                    expected = prior.project(candidate)
                    np.testing.assert_array_equal(raw['written_fields'][role, gi, mi, slot], expected)
                    assert abs(float(expected.mean())) < 1e-14 and abs(float(expected.std())-.3) < 1e-14
                entries.append(dict(noise_rng=canonical_digest(random.bit_generator.state),
                    input_sha256=sha(supplied), packet_bytes=2048, sigma=sigma,
                    writing=False, gain=0., target_labels=False))
            assert entries[0]['noise_rng'] == entries[1]['noise_rng']
            generations.append(entries)
        source_records.append(generations)
    np.testing.assert_array_equal(raw['source_births'][0], raw['source_births'][1])
    nested(meta['source_paths'], source_records)
    tissue, ladder, bp = physics.parameters(meta)
    assert tissue.sigma == .3
    maximum = source_maximum; records = []
    for ci, (role, kind) in enumerate(CASES):
        entries = []
        for gi, g in enumerate((1, 2, 3)):
            perm = generator(TAG, index, life, f'g{g}:shuffle:{role}').permutation(256)
            np.testing.assert_array_equal(raw['permutations'][role, gi], perm)
            if kind == 'ideal': expected = prior.project(np.tanh(1.5*prior.prior.targets()[role]))
            elif kind == 'zero': expected = np.zeros((16, 16))
            else:
                wi = 0 if kind.startswith('noisy_') else 1
                body, history = raw['written_fields'][role, gi, wi]
                handling = kind.split('_', 1)[1]
                original = history if handling in ('history', 'history_shuffle', 'sham', 'off') else body
                expected = original.reshape(256)[perm].reshape(16, 16) if handling.endswith('_shuffle') else original
            supplied = raw['packets'][ci, gi].tobytes()
            assert supplied == packet(expected)
            if kind.endswith('_shuffle'):
                np.testing.assert_array_equal(np.sort(expected.ravel()), np.sort(original.ravel()))
            random = generator(TAG, index, life, f'g{g}:birth')
            v = .2*random.standard_normal((1, 16, 16)); birth_rng = canonical_digest(random.bit_generator.state)
            state = (v, v.copy(), v.copy()); saved = [np.stack(state)[:, 0]]
            np.testing.assert_array_equal(raw['states'][ci, gi, 0], saved[0])
            random = generator(TAG, index, life, f'g{g}:read')
            for t in range(1, cfg.steps+1):
                noise = random.standard_normal((1, 16, 16))
                if replay:
                    applied = expected if not kind.endswith('_off') else np.zeros((16, 16))
                    state = physics.step(*state, applied, tissue, ladder, 0., bp.rho, noise)
                    if t in cfg.times: saved.append(np.stack(state)[:, 0])
            if replay: maximum = max(maximum, compare(raw['states'][ci, gi], np.stack(saved)))
            entries.append(dict(birth_rng=birth_rng, read_rng=canonical_digest(random.bit_generator.state),
                input_sha256=sha(supplied), packet_bytes=2048, enabled=not kind.endswith('_off'), writing=False, gain=0., target_labels=False))
        records.append(entries)
    nested(meta['readers'], records)
    aliases = [((r, w+'_history'), (r, w+'_sham')) for r in (0, 1) for w in MODES]
    aliases += [((r, w+'_off'), (r, 'zero')) for r in (0, 1) for w in MODES]
    aliases.append(((0, 'zero'), (1, 'zero')))
    for a, b in aliases:
        np.testing.assert_array_equal(raw['states'][CASES.index(a)], raw['states'][CASES.index(b)])
    values = observe(raw['states'], raw['targets'], CASES, cfg)
    np.testing.assert_allclose(raw['values'], values, atol=1e-12, rtol=0)
    return dict(full_life_replay=replay, dynamics_max_abs=maximum, source_dynamics_max_abs=source_maximum, metric_max_abs=float(abs(raw['values']-values).max()),
        reader_paths=84, exact_path_aliases=27, source_pairs=6, source_paths=12, packet_lineage_checked=True,
        fresh_reset=True, exact_signs=True, new_source_writes=0)


def check_block(raw, meta, cfg, replay=True, root=None):
    from laws_confirmation import l20_source_noise as p
    from laws_confirmation.io import DEFAULT_EXTERNAL_ROOT
    root = DEFAULT_EXTERNAL_ROOT if root is None else root
    assert set(meta) == {'index', 'config', 'source_sha256', 'lives'}
    index = meta['index']; assert type(index) is int and index in (*range(65000, 65008), 514223)
    nested(meta['config'], asdict(cfg)); assert len(meta['lives']) == cfg.lives
    assert all(x.shape[0] == cfg.lives for x in raw.values())
    # Shared I/O only; source addressing and all new physics above are independent.
    source, _ = p.load_source(index, root)
    assert meta['source_sha256'] == {str(x): sha256_file(x) for x in p.source_paths(index, root)}
    for life, row in enumerate(meta['lives']):
        assert row['index'] == index and row['life'] == life
        proof = row['replay']
        expected = dict(full_life_replay=True, dynamics_max_abs=proof['dynamics_max_abs'],
            source_dynamics_max_abs=proof['source_dynamics_max_abs'],
            metric_max_abs=proof['metric_max_abs'], reader_paths=84, exact_path_aliases=27, source_pairs=6, source_paths=12,
            packet_lineage_checked=True, fresh_reset=True, exact_signs=True, new_source_writes=0)
        nested(proof, expected)
        assert 0 <= proof['source_dynamics_max_abs'] <= proof['dynamics_max_abs'] <= 1e-10 and 0 <= proof['metric_max_abs'] <= 1e-12
        current = check_life({k: x[life] for k, x in raw.items()}, row, cfg, source, replay)
        if replay: nested(proof, current)
    return True


def check_source(raw, meta, source):
    keys = {'index', 'life', 'cases', 'times', 'tissue', 'ladder', 'blueprint', 'readers', 'known_outcomes', 'new_source_writes', 'source_paths'}
    assert set(meta) in (keys, keys | {'replay'}) and set(raw) == {'packets', 'states', 'targets', 'source_births', 'source_packets', 'source_states'}
    cases = tuple((r, k) for r in (0, 1) for k in ('rewrite', 'ideal', 'zero'))
    nested(meta['cases'], [list(c) for c in cases]); nested(meta['times'], [0, 1, 100, 300])
    assert meta['index'] == 514217 and meta['life'] == 0 and meta['known_outcomes'] is True and meta['new_source_writes'] == 0
    indices = [prior.PROBES.index(c) for c in cases]
    np.testing.assert_array_equal(raw['packets'], source['probe_packets'][0, indices])
    np.testing.assert_array_equal(raw['states'], source['probe_states'][0, indices])
    np.testing.assert_array_equal(raw['targets'], prior.prior.targets())
    tissue, ladder, bp = physics.parameters(meta); maximum = 0.; records = []
    for supplied, observed in zip(raw['packets'], raw['states']):
        random = generator('l20-three-rewrite-v1', 514217, 0, 'terminal:birth')
        v = .2*random.standard_normal((1, 16, 16)); birth = canonical_digest(random.bit_generator.state)
        state = (v, v.copy(), v.copy()); saved = [np.stack(state)[:, 0]]
        random = generator('l20-three-rewrite-v1', 514217, 0, 'terminal:read')
        for t in range(1, 301):
            state = physics.step(*state, unpack(supplied.tobytes()), tissue, ladder, 0., bp.rho,
                random.standard_normal((1, 16, 16)))
            if t in (1, 100, 300): saved.append(np.stack(state)[:, 0])
        maximum = max(maximum, compare(observed, np.stack(saved)))
        records.append(dict(birth_rng=birth, read_rng=canonical_digest(random.bit_generator.state),
            input_sha256=sha(supplied.tobytes()), packet_bytes=2048, writing=False, gain=0.))
    nested(meta['readers'], records)
    source_maximum = 0.; records = []
    for role in (0, 1):
        entries = []
        for gi in range(3):
            start = source['generation_states'][0, role*8, gi, 0, :3]
            supplied = source['incoming'][0, role*8, gi].tobytes()
            np.testing.assert_array_equal(raw['source_births'][role, gi], start)
            assert raw['source_packets'][role, gi].tobytes() == supplied
            random = generator('l20-three-rewrite-v1', 514217, 0, f'g{gi+1}:read')
            state = tuple(x[None].copy() for x in start); saved = [start.copy()]
            for t in range(1, 301):
                state = physics.step(*state, unpack(supplied), tissue, ladder, 0., bp.rho,
                    random.standard_normal((1, 16, 16)))
                if t in (1, 100, 300): saved.append(np.stack(state)[:, 0])
            source_maximum = max(source_maximum, compare(raw['source_states'][role, gi], np.stack(saved)))
            np.testing.assert_array_equal(raw['source_states'][role, gi],
                source['generation_states'][0, role*8, gi, [0, 1, 2, 4], :3])
            entries.append(dict(noise_rng=canonical_digest(random.bit_generator.state),
                input_sha256=sha(supplied), packet_bytes=2048, sigma=.3,
                writing=False, gain=0., target_labels=False))
        records.append(entries)
    nested(meta['source_paths'], records)
    return dict(known_reader_paths=6, full_reader_replay=True, max_abs=maximum,
        known_source_paths=6, full_source_read_replay=True, source_max_abs=source_maximum,
        new_source_writes=0, whole_renewal_replayed=False, qualification_pool=False)


def check_summary(summary, blocks, cfg):
    assert len(blocks) == 8
    values = np.stack([b['values'] for b in blocks])
    assert values.shape == (8, cfg.lives, 28, 3, len(cfg.times), 12) and np.isfinite(values).all()
    draws = generator(TAG, 0, 0, 'bootstrap').integers(0, 8, (10000, 8)); rows = []
    pairs = [('noisy_history', 'noisy_body'), ('quiet_history', 'quiet_body'),
        ('noisy_history', 'quiet_history'), ('noisy_body', 'quiet_body'), ('ideal', 'zero')]
    for k in BASES: pairs.extend([(k, k+'_shuffle'), (k, 'zero')])
    weights = {a+'_minus_'+b: [(a, 1), (b, -1)] for a, b in pairs}
    weights.update({
        'noisy_specificity_gain': [('noisy_history', 1), ('noisy_history_shuffle', -1), ('noisy_body', -1), ('noisy_body_shuffle', 1)],
        'quiet_specificity_gain': [('quiet_history', 1), ('quiet_history_shuffle', -1), ('quiet_body', -1), ('quiet_body_shuffle', 1)],
        'noise_interaction': [('noisy_history', 1), ('noisy_body', -1), ('quiet_history', -1), ('quiet_body', 1)],
        'specificity_interaction': [('noisy_history', 1), ('noisy_history_shuffle', -1), ('noisy_body', -1),
            ('noisy_body_shuffle', 1), ('quiet_history', -1), ('quiet_history_shuffle', 1),
            ('quiet_body', 1), ('quiet_body_shuffle', -1)]})
    for observer, col in (('qualified', 0), ('sign', 2)):
        for stage in ('all', 1, 2, 3):
            for name, terms in weights.items():
                effects = []
                for role in (0, 1):
                    effect = np.zeros((8, cfg.lives, 3 if stage == 'all' else 1))
                    for kind, weight in terms:
                        ci = CASES.index((role, kind))
                        for slot, gi in enumerate(range(3) if stage == 'all' else (stage-1,)):
                            effect[:, :, slot] += weight*(values[:, :, ci, gi, -1, col]-values[:, :, ci, gi, -1, col+1])
                    effects.append(effect.mean(axis=-1))
                for role, effect in ((0, effects[0]), (1, effects[1]), ('both', (effects[0]+effects[1])/2)):
                    rows.append(dict(name=name, stage=stage, role=role, observer=observer, **prior.stats(effect, draws)))
    get = lambda name, role='both': next(r for r in rows if (r['name'], r['stage'], r['role'], r['observer']) == (name, 'all', role, 'qualified'))
    gates = [get('ideal_minus_zero', r) for r in (0, 1)]
    disagreements = [[int((b['targets'][l, 0] != b['targets'][l, 1]).sum()) for l in range(cfg.lives)] for b in blocks]
    instrument = all(r['pointwise_block_bootstrap_95'][0] > 0 for r in gates) and all(n > 0 for row in disagreements for n in row)
    qualifies = {}
    for kind in BASES:
        specific = get(kind+'_minus_'+kind+'_shuffle')
        qualifies[kind] = bool(instrument and specific['pointwise_block_bootstrap_95'][0] > 0 and all(
            get(kind+'_minus_'+kind+'_shuffle', r)['mean'] > 0 and get(kind+'_minus_zero', r)['pointwise_block_bootstrap_95'][0] > 0 for r in (0, 1)))
    primary = get('noise_interaction')
    directions = [get('noise_interaction', r) for r in (0, 1)]
    label = 'READOUT_NOT_QUALIFIED' if not instrument else 'INTERACTION_CONTENT_NOT_QUALIFIED' if not all(qualifies.values()) else 'SOURCE_NOISE_INTERACTION_UNRESOLVED'
    if all(qualifies.values()):
        if primary['pointwise_block_bootstrap_95'][0] > 0 and all(r['mean'] > 0 for r in directions): label = 'SOURCE_NOISE_INCREASES_HISTORY_GAP'
        elif primary['pointwise_block_bootstrap_95'][1] < 0 and all(r['mean'] < 0 for r in directions): label = 'SOURCE_NOISE_DECREASES_HISTORY_GAP'
    gaps, gap_directions, gap_labels = {}, {}, {}
    for mode in ('noisy', 'quiet'):
        gap = get(mode+'_history_minus_'+mode+'_body')
        ds = [get(mode+'_history_minus_'+mode+'_body', r) for r in (0, 1)]
        ready = qualifies[mode+'_history'] and qualifies[mode+'_body']
        glabel = 'HISTORY_EFFECT_UNRESOLVED' if ready else 'CONTENT_NOT_QUALIFIED'
        if ready:
            if gap['pointwise_block_bootstrap_95'][0] > 0 and all(r['mean'] > 0 for r in ds): glabel = 'HISTORY_ADVANTAGE_QUALIFIED'
            elif gap['pointwise_block_bootstrap_95'][1] < 0 and all(r['mean'] < 0 for r in ds): glabel = 'BODY_ADVANTAGE_QUALIFIED'
        gaps[mode], gap_directions[mode], gap_labels[mode] = gap, ds, glabel
    expected = dict(schema='l20_source_noise_v1', label=label, primary=primary, directional_primary=directions,
        content_readable=qualifies, readout_qualified=bool(instrument), readout_gates=gates,
        history_gaps=gaps, directional_history_gaps=gap_directions, history_gap_labels=gap_labels,
        history_gaps_are_secondary=True, contrasts=rows, target_disagreement_cells=disagreements, cases=[list(c) for c in CASES],
        times=list(cfg.times), metrics=list(METRICS), cell_means=values.mean(axis=(0, 1)).tolist(),
        reader_blocks=list(range(65000, 65008)), source_blocks=list(range(60000, 60008)), blocks=8,
        lives_per_block=cfg.lives, source_generation_strata=3, reader_paths=8*cfg.lives*84, packet_bytes=2048,
        source_starts_reused=True, new_source_paths=8*cfg.lives*12, source_noise_reused=False, new_renewal_cohort=False,
        source_steps=300, source_times=[0, 1, 100, 300], source_rho=.002, birth_coefficient=.998**300,
        modes=['noisy', 'quiet'], sigmas=[.3, 0.], reader_sigma=.3,
        writer_inputs=['V300', 'R300-.998**300*R0'], writer_rule='project(snapshot, .3)', birth_direct_term_only=True,
        absolute_fidelity_gate=None, equivalence_test=False, secondary_intervals_multiplicity_adjusted=False)
    nested(summary, expected); return True


if __name__ == '__main__':
    from laws_confirmation.l20_source_noise_run import main
    main(default_command='audit')

