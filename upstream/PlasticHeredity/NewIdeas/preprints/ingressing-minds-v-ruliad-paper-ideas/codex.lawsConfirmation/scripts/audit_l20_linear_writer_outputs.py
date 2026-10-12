"""D121 independent packet addressing, reader dynamics, observer and inference."""
from dataclasses import asdict
import hashlib

import numpy as np

from laws_confirmation import l20_three_rewrite as old
from laws_confirmation.io import canonical_digest, sha256_file

prior = old.checker()
physics = prior.physics
compare, nested, generator = physics.compare, physics.nested, physics.generator
TAG = 'l20-linear-writer-v1'
WRITERS = ('linear', 'tanh')
BASES = ('linear_body', 'linear_reference', 'tanh_body', 'tanh_reference')
KINDS = ('linear_body', 'linear_reference', 'tanh_body', 'tanh_reference',
    'linear_body_shuffle', 'linear_reference_shuffle', 'tanh_body_shuffle', 'tanh_reference_shuffle',
    'linear_sham', 'tanh_sham', 'linear_off', 'tanh_off', 'ideal', 'zero')
CASES = tuple((r, k) for r in (0, 1) for k in KINDS)
METRICS = prior.METRICS
packet, unpack, sha = prior.packet, prior.unpack, prior.sha
observe = prior.observe


def check_life(raw, meta, cfg, source, replay=True):
    keys = {'index', 'source_index', 'life', 'config', 'cases', 'times', 'reader_tag', 'source_tag',
            'source_reused', 'source_checkpoint', 'writer_inputs', 'writers', 'writer_rules', 'incoming_theta_used', 'tissue', 'ladder', 'blueprint', 'readers'}
    assert set(meta) in (keys, keys | {'replay'})
    index, life = meta['index'], meta['life']
    assert type(index) is int and index in (*range(63000, 63008), 514221)
    assert type(life) is int and 0 <= life < cfg.lives
    assert meta['source_index'] == (514217 if index == 514221 else index-3000)
    nested(meta['config'], asdict(cfg)); nested(meta['cases'], [list(c) for c in CASES])
    nested(meta['times'], list(cfg.times)); assert type(meta['source_checkpoint']) is int and meta['source_checkpoint'] == 300
    nested(meta['writer_inputs'], ['V', 'R'])
    nested(meta['writers'], ['linear', 'tanh'])
    nested(meta['writer_rules'], ['project(snapshot, .3)', 'project(tanh(snapshot), .3)'])
    assert meta['incoming_theta_used'] is False
    assert meta['reader_tag'] == TAG and meta['source_tag'] == 'l20-three-rewrite-v1' and meta['source_reused'] is True
    shapes = dict(targets=(2, 16, 16), source_fields=(2, 3, 2, 16, 16), written_fields=(2, 3, 2, 2, 16, 16),
                  permutations=(2, 3, 256),
                  packets=(28, 3, 2048), states=(28, 3, len(cfg.times), 3, 16, 16),
                  values=(28, 3, len(cfg.times), 12))
    assert set(raw) == set(shapes)
    for key, shape in shapes.items():
        dtype = np.uint8 if key == 'packets' else np.int64 if key == 'permutations' else np.float64
        assert raw[key].shape == shape and raw[key].dtype == dtype and np.isfinite(raw[key]).all()
    np.testing.assert_array_equal(raw['targets'], prior.prior.targets())
    np.testing.assert_array_equal(raw['targets'], source['targets'][life])
    for role, ci in ((0, 0), (1, 8)):
        for gi in range(3):
            for slot, source_field in ((0, 0), (1, 2)):
                snapshot = source['generation_states'][life, ci, gi, 4, source_field]
                np.testing.assert_array_equal(raw['source_fields'][role, gi, slot], snapshot)
                # Separate normalization equations; no production constructor.
                for wi, candidate in enumerate((snapshot, np.tanh(snapshot))):
                    assert candidate.std() > 1e-9, 'degenerate source: fail rather than exclude'
                    expected = prior.project(candidate)
                    np.testing.assert_array_equal(raw['written_fields'][role, gi, wi, slot], expected)
                    assert abs(float(expected.mean())) < 1e-14 and abs(float(expected.std())-.3) < 1e-14
    tissue, ladder, bp = physics.parameters(meta); maximum = 0.; records = []
    for ci, (role, kind) in enumerate(CASES):
        entries = []
        for gi, g in enumerate((1, 2, 3)):
            perm = generator(TAG, index, life, f'g{g}:shuffle:{role}').permutation(256)
            np.testing.assert_array_equal(raw['permutations'][role, gi], perm)
            if kind == 'ideal': expected = prior.project(np.tanh(1.5*prior.prior.targets()[role]))
            elif kind == 'zero': expected = np.zeros((16, 16))
            else:
                wi = 0 if kind.startswith('linear_') else 1
                body, reference = raw['written_fields'][role, gi, wi]
                handling = kind.split('_', 1)[1]
                original = reference if handling in ('reference', 'reference_shuffle', 'off') else body
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
    aliases = [((r, w+'_body'), (r, w+'_sham')) for r in (0, 1) for w in WRITERS]
    aliases += [((r, w+'_off'), (r, 'zero')) for r in (0, 1) for w in WRITERS]
    aliases.append(((0, 'zero'), (1, 'zero')))
    for a, b in aliases:
        np.testing.assert_array_equal(raw['states'][CASES.index(a)], raw['states'][CASES.index(b)])
    values = observe(raw['states'], raw['targets'], CASES, cfg)
    np.testing.assert_allclose(raw['values'], values, atol=1e-12, rtol=0)
    return dict(full_life_replay=replay, dynamics_max_abs=maximum, metric_max_abs=float(abs(raw['values']-values).max()),
        reader_paths=84, exact_path_aliases=27, source_pairs=6, packet_lineage_checked=True,
        fresh_reset=True, exact_signs=True, new_source_writes=0)


def check_block(raw, meta, cfg, replay=True, root=None):
    from laws_confirmation import l20_linear_writer as p
    from laws_confirmation.io import DEFAULT_EXTERNAL_ROOT
    root = DEFAULT_EXTERNAL_ROOT if root is None else root
    assert set(meta) == {'index', 'config', 'source_sha256', 'lives'}
    index = meta['index']; assert type(index) is int and index in (*range(63000, 63008), 514221)
    nested(meta['config'], asdict(cfg)); assert len(meta['lives']) == cfg.lives
    assert all(x.shape[0] == cfg.lives for x in raw.values())
    # Shared I/O only; source addressing and all new physics above are independent.
    source, _ = p.load_source(index, root)
    assert meta['source_sha256'] == {str(x): sha256_file(x) for x in p.source_paths(index, root)}
    for life, row in enumerate(meta['lives']):
        assert row['index'] == index and row['life'] == life
        proof = row['replay']
        expected = dict(full_life_replay=True, dynamics_max_abs=proof['dynamics_max_abs'],
            metric_max_abs=proof['metric_max_abs'], reader_paths=84, exact_path_aliases=27, source_pairs=6,
            packet_lineage_checked=True, fresh_reset=True, exact_signs=True, new_source_writes=0)
        nested(proof, expected)
        assert 0 <= proof['dynamics_max_abs'] <= 1e-10 and 0 <= proof['metric_max_abs'] <= 1e-12
        current = check_life({k: x[life] for k, x in raw.items()}, row, cfg, source, replay)
        if replay: nested(proof, current)
    return True


def check_source(raw, meta, source):
    keys = {'index', 'life', 'cases', 'times', 'tissue', 'ladder', 'blueprint', 'readers', 'known_outcomes', 'new_source_writes'}
    assert set(meta) in (keys, keys | {'replay'}) and set(raw) == {'packets', 'states', 'targets'}
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
    return dict(known_reader_paths=6, full_reader_replay=True, max_abs=maximum,
        new_source_writes=0, whole_renewal_replayed=False, qualification_pool=False)


def check_summary(summary, blocks, cfg):
    assert len(blocks) == 8
    values = np.stack([b['values'] for b in blocks])
    assert values.shape == (8, cfg.lives, 28, 3, len(cfg.times), 12) and np.isfinite(values).all()
    draws = generator(TAG, 0, 0, 'bootstrap').integers(0, 8, (10000, 8)); rows = []
    pairs = [('linear_reference', 'linear_body'), ('tanh_reference', 'tanh_body'),
        ('tanh_reference', 'linear_reference'), ('tanh_body', 'linear_body'), ('ideal', 'zero')]
    for k in BASES: pairs.extend([(k, k+'_shuffle'), (k, 'zero')])
    weights = {a+'_minus_'+b: [(a, 1), (b, -1)] for a, b in pairs}
    weights.update({
        'linear_specificity_gain': [('linear_reference', 1), ('linear_reference_shuffle', -1),
            ('linear_body', -1), ('linear_body_shuffle', 1)],
        'tanh_specificity_gain': [('tanh_reference', 1), ('tanh_reference_shuffle', -1),
            ('tanh_body', -1), ('tanh_body_shuffle', 1)],
        'writer_interaction': [('tanh_reference', 1), ('tanh_body', -1),
            ('linear_reference', -1), ('linear_body', 1)],
        'specificity_interaction': [('tanh_reference', 1), ('tanh_reference_shuffle', -1),
            ('tanh_body', -1), ('tanh_body_shuffle', 1), ('linear_reference', -1),
            ('linear_reference_shuffle', 1), ('linear_body', 1), ('linear_body_shuffle', -1)]})
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
    primary = get('linear_reference_minus_linear_body')
    directions = [get('linear_reference_minus_linear_body', r) for r in (0, 1)]
    label = 'READOUT_NOT_QUALIFIED' if not instrument else 'LINEAR_REFERENCE_EFFECT_UNRESOLVED'
    if instrument:
        if qualifies['linear_reference'] and primary['pointwise_block_bootstrap_95'][0] > 0 and all(r['mean'] > 0 for r in directions): label = 'LINEAR_REFERENCE_ADVANTAGE_QUALIFIED'
        elif qualifies['linear_body'] and primary['pointwise_block_bootstrap_95'][1] < 0 and all(r['mean'] < 0 for r in directions): label = 'LINEAR_BODY_ADVANTAGE_QUALIFIED'
    interaction = get('writer_interaction')
    idir = [get('writer_interaction', r) for r in (0, 1)]
    ilabel = 'INTERACTION_CONTENT_NOT_QUALIFIED' if not all(qualifies.values()) else 'INTERACTION_UNRESOLVED'
    if all(qualifies.values()):
        if interaction['pointwise_block_bootstrap_95'][0] > 0 and all(r['mean'] > 0 for r in idir): ilabel = 'TANH_INCREASES_REFERENCE_GAP'
        elif interaction['pointwise_block_bootstrap_95'][1] < 0 and all(r['mean'] < 0 for r in idir): ilabel = 'TANH_DECREASES_REFERENCE_GAP'
    expected = dict(schema='l20_linear_writer_v1', label=label, primary=primary, directional_primary=directions,
        content_readable=qualifies, readout_qualified=bool(instrument), readout_gates=gates,
        interaction=interaction, directional_interaction=idir, interaction_label=ilabel,
        interaction_is_secondary=True, contrasts=rows, target_disagreement_cells=disagreements, cases=[list(c) for c in CASES],
        times=list(cfg.times), metrics=list(METRICS), cell_means=values.mean(axis=(0, 1)).tolist(),
        reader_blocks=list(range(63000, 63008)), source_blocks=list(range(60000, 60008)), blocks=8,
        lives_per_block=cfg.lives, generations_reused=3, reader_paths=8*cfg.lives*84, packet_bytes=2048,
        reused_source_histories=True, new_renewal_cohort=False,
        source_checkpoint=300, writer_inputs=['V', 'R'], writers=['linear', 'tanh'],
        writer_rules=['project(snapshot, .3)', 'project(tanh(snapshot), .3)'],
        absolute_fidelity_gate=None, equivalence_test=False, secondary_intervals_multiplicity_adjusted=False)
    nested(summary, expected); return True


if __name__ == '__main__':
    from laws_confirmation.l20_linear_writer_run import main
    main(default_command='audit')
