"""D122 independent packet addressing, reader dynamics, observer and inference."""
from dataclasses import asdict
import hashlib

import numpy as np

from laws_confirmation import l20_three_rewrite as old
from laws_confirmation.io import canonical_digest, sha256_file

prior = old.checker()
physics = prior.physics
compare, nested, generator = physics.compare, physics.nested, physics.generator
TAG = 'l20-birth-component-v1'
BASES = ('body', 'reference', 'history', 'birth')
KINDS = ('body', 'reference', 'history', 'birth', 'body_shuffle', 'reference_shuffle',
    'history_shuffle', 'birth_shuffle', 'history_sham', 'reference_sham',
    'history_off', 'reference_off', 'ideal', 'zero')
CASES = tuple((r, k) for r in (0, 1) for k in KINDS)
METRICS = prior.METRICS
packet, unpack, sha = prior.packet, prior.unpack, prior.sha
observe = prior.observe


def check_life(raw, meta, cfg, source, replay=True):
    keys = {'index', 'source_index', 'life', 'config', 'cases', 'times', 'reader_tag', 'source_tag',
        'source_reused', 'source_checkpoint', 'source_birth_checkpoint', 'source_snapshots',
        'component_names', 'writer_inputs', 'writer_rule', 'source_rho', 'birth_coefficient',
        'incoming_theta_used', 'birth_direct_term_only', 'source_birth_shared_between_roles',
        'tissue', 'ladder', 'blueprint', 'readers'}
    assert set(meta) in (keys, keys | {'replay'})
    index, life = meta['index'], meta['life']
    assert type(index) is int and index in (*range(64000, 64008), 514222)
    assert type(life) is int and 0 <= life < cfg.lives
    assert meta['source_index'] == (514217 if index == 514222 else index-4000)
    nested(meta['config'], asdict(cfg)); nested(meta['cases'], [list(c) for c in CASES])
    nested(meta['times'], list(cfg.times))
    assert type(meta['source_checkpoint']) is int and meta['source_checkpoint'] == 300
    assert type(meta['source_birth_checkpoint']) is int and meta['source_birth_checkpoint'] == 0
    nested(meta['source_snapshots'], ['V300', 'R300', 'R0'])
    nested(meta['component_names'], ['history', 'birth']); nested(meta['writer_inputs'], list(BASES))
    assert meta['writer_rule'] == 'project(snapshot, .3)' and meta['source_rho'] == .002
    assert meta['birth_coefficient'] == (1-.002)**300 and meta['incoming_theta_used'] is False
    assert meta['birth_direct_term_only'] is True and meta['source_birth_shared_between_roles'] is True
    assert meta['reader_tag'] == TAG and meta['source_tag'] == 'l20-three-rewrite-v1' and meta['source_reused'] is True
    shapes = dict(targets=(2, 16, 16), source_fields=(2, 3, 3, 16, 16),
        component_fields=(2, 3, 2, 16, 16), written_fields=(2, 3, 4, 16, 16),
        permutations=(2, 3, 256), packets=(28, 3, 2048),
        states=(28, 3, len(cfg.times), 3, 16, 16), values=(28, 3, len(cfg.times), 12))
    assert set(raw) == set(shapes)
    for key, shape in shapes.items():
        dtype = np.uint8 if key == 'packets' else np.int64 if key == 'permutations' else np.float64
        assert raw[key].shape == shape and raw[key].dtype == dtype and np.isfinite(raw[key]).all()
    np.testing.assert_array_equal(raw['targets'], prior.prior.targets())
    np.testing.assert_array_equal(raw['targets'], source['targets'][life])
    for role, ci in ((0, 0), (1, 8)):
        for gi in range(3):
            snapshots = [source['generation_states'][life, ci, gi, ti, f] for ti, f in ((4, 0), (4, 2), (0, 2))]
            np.testing.assert_array_equal(raw['source_fields'][role, gi], np.stack(snapshots))
            v, reference, initial = snapshots
            residual = ((1-.002)**300)*initial
            accumulated = reference-residual
            np.testing.assert_array_equal(raw['component_fields'][role, gi], np.stack((accumulated, residual)))
            np.testing.assert_allclose(accumulated+residual, reference, rtol=0, atol=1e-14)
            for slot, candidate in enumerate((v, reference, accumulated, residual)):
                assert candidate.std() > 1e-9, 'degenerate source: fail rather than exclude'
                expected = prior.project(candidate)
                np.testing.assert_array_equal(raw['written_fields'][role, gi, slot], expected)
                assert abs(float(expected.mean())) < 1e-14 and abs(float(expected.std())-.3) < 1e-14
    np.testing.assert_array_equal(raw['source_fields'][0, :, 2], raw['source_fields'][1, :, 2])
    tissue, ladder, bp = physics.parameters(meta); maximum = 0.; records = []
    for ci, (role, kind) in enumerate(CASES):
        entries = []
        for gi, g in enumerate((1, 2, 3)):
            perm = generator(TAG, index, life, f'g{g}:shuffle:{role}').permutation(256)
            np.testing.assert_array_equal(raw['permutations'][role, gi], perm)
            if kind == 'ideal': expected = prior.project(np.tanh(1.5*prior.prior.targets()[role]))
            elif kind == 'zero': expected = np.zeros((16, 16))
            else:
                original = raw['written_fields'][role, gi, BASES.index(kind.split('_', 1)[0])]
                expected = original.reshape(256)[perm].reshape(16, 16) if kind.endswith('_shuffle') else original
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
    aliases = [((r, k), (r, k+'_sham')) for r in (0, 1) for k in ('history', 'reference')]
    aliases += [((r, k+'_off'), (r, 'zero')) for r in (0, 1) for k in ('history', 'reference')]
    aliases += [((0, k), (1, k)) for k in ('zero', 'birth')]
    for a, b in aliases:
        np.testing.assert_array_equal(raw['states'][CASES.index(a)], raw['states'][CASES.index(b)])
    values = observe(raw['states'], raw['targets'], CASES, cfg)
    np.testing.assert_allclose(raw['values'], values, atol=1e-12, rtol=0)
    return dict(full_life_replay=replay, dynamics_max_abs=maximum, metric_max_abs=float(abs(raw['values']-values).max()),
        reader_paths=84, exact_path_aliases=30, source_pairs=6, packet_lineage_checked=True,
        fresh_reset=True, exact_signs=True, new_source_writes=0)


def check_block(raw, meta, cfg, replay=True, root=None):
    from laws_confirmation import l20_birth_component as p
    from laws_confirmation.io import DEFAULT_EXTERNAL_ROOT
    root = DEFAULT_EXTERNAL_ROOT if root is None else root
    assert set(meta) == {'index', 'config', 'source_sha256', 'lives'}
    index = meta['index']; assert type(index) is int and index in (*range(64000, 64008), 514222)
    nested(meta['config'], asdict(cfg)); assert len(meta['lives']) == cfg.lives
    assert all(x.shape[0] == cfg.lives for x in raw.values())
    # Shared I/O only; source addressing and all new physics above are independent.
    source, _ = p.load_source(index, root)
    assert meta['source_sha256'] == {str(x): sha256_file(x) for x in p.source_paths(index, root)}
    for life, row in enumerate(meta['lives']):
        assert row['index'] == index and row['life'] == life
        proof = row['replay']
        expected = dict(full_life_replay=True, dynamics_max_abs=proof['dynamics_max_abs'],
            metric_max_abs=proof['metric_max_abs'], reader_paths=84, exact_path_aliases=30, source_pairs=6,
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
    pairs = [('history', 'body'), ('history', 'reference'), ('reference', 'body'),
        ('history', 'birth'), ('reference', 'birth'), ('ideal', 'zero')]
    for k in BASES: pairs.extend([(k, k+'_shuffle'), (k, 'zero')])
    weights = {a+'_minus_'+b: [(a, 1), (b, -1)] for a, b in pairs}
    weights.update({
        'history_specificity_gain': [('history', 1), ('history_shuffle', -1), ('body', -1), ('body_shuffle', 1)],
        'reference_specificity_gain': [('reference', 1), ('reference_shuffle', -1), ('body', -1), ('body_shuffle', 1)],
        'birth_removal_specificity': [('history', 1), ('history_shuffle', -1), ('reference', -1), ('reference_shuffle', 1)]})
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
    primary = get('history_minus_body')
    directions = [get('history_minus_body', r) for r in (0, 1)]
    label = 'READOUT_NOT_QUALIFIED' if not instrument else 'HISTORY_EFFECT_UNRESOLVED'
    if instrument:
        if qualifies['history'] and primary['pointwise_block_bootstrap_95'][0] > 0 and all(r['mean'] > 0 for r in directions): label = 'HISTORY_ADVANTAGE_QUALIFIED'
        elif qualifies['body'] and primary['pointwise_block_bootstrap_95'][1] < 0 and all(r['mean'] < 0 for r in directions): label = 'BODY_ADVANTAGE_QUALIFIED'
    removal = get('history_minus_reference')
    rdir = [get('history_minus_reference', r) for r in (0, 1)]
    ready = qualifies['history'] and qualifies['reference']
    rlabel = 'BIRTH_REMOVAL_CONTENT_NOT_QUALIFIED' if not ready else 'BIRTH_REMOVAL_EFFECT_UNRESOLVED'
    if ready:
        if removal['pointwise_block_bootstrap_95'][0] > 0 and all(r['mean'] > 0 for r in rdir): rlabel = 'BIRTH_REMOVAL_IMPROVES_READOUT'
        elif removal['pointwise_block_bootstrap_95'][1] < 0 and all(r['mean'] < 0 for r in rdir): rlabel = 'BIRTH_REMOVAL_WORSENS_READOUT'
    expected = dict(schema='l20_birth_component_v1', label=label, primary=primary, directional_primary=directions,
        content_readable=qualifies, readout_qualified=bool(instrument), readout_gates=gates,
        birth_removal=removal, directional_birth_removal=rdir, birth_removal_label=rlabel,
        birth_removal_is_secondary=True, contrasts=rows, target_disagreement_cells=disagreements, cases=[list(c) for c in CASES],
        times=list(cfg.times), metrics=list(METRICS), cell_means=values.mean(axis=(0, 1)).tolist(),
        reader_blocks=list(range(64000, 64008)), source_blocks=list(range(60000, 60008)), blocks=8,
        lives_per_block=cfg.lives, generations_reused=3, reader_paths=8*cfg.lives*84, packet_bytes=2048,
        reused_source_histories=True, new_renewal_cohort=False,
        source_checkpoint=300, source_birth_checkpoint=0, source_rho=.002, birth_coefficient=(1-.002)**300,
        source_snapshots=['V300', 'R300', 'R0'], writer_inputs=list(BASES),
        writer_rule='project(snapshot, .3)', birth_direct_term_only=True,
        birth_pooled_preference_cancels_by_design=True,
        absolute_fidelity_gate=None, equivalence_test=False, secondary_intervals_multiplicity_adjusted=False)
    nested(summary, expected); return True


if __name__ == '__main__':
    from laws_confirmation.l20_birth_component_run import main
    main(default_command='audit')
