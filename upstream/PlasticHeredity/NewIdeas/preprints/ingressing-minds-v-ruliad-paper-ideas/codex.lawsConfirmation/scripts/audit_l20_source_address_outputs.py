"""D126 independently restated source addressing, force probes, dynamics and statistics."""
from dataclasses import asdict
import hashlib

import numpy as np

from laws_confirmation import l20_three_rewrite as old
from laws_confirmation.io import canonical_digest, sha256_file

prior = old.checker()
physics = prior.physics
compare, nested, generator = physics.compare, physics.nested, physics.generator
TAG = 'l20-source-address-v1'
KINDS = ('aligned', 'scrambled', 'no_feedback',
         'aligned_shuffle', 'scrambled_shuffle', 'no_feedback_shuffle',
         'aligned_sham', 'scrambled_sham', 'no_feedback_sham',
         'aligned_off', 'scrambled_off', 'no_feedback_off', 'ideal', 'zero')
MODES = ('aligned', 'scrambled', 'no_feedback')
FORCE_METRICS = ('applied_mean', 'applied_std', 'input_rms', 'effective_rms',
    'effective_dot_v', 'effective_dot_reference_gap', 'output_clip_fraction', 'reference_gap_rms')
CASES = tuple((r, k) for r in (0, 1) for k in KINDS)
METRICS = prior.METRICS
packet, unpack, sha = prior.packet, prior.unpack, prior.sha
observe = prior.observe


def source_metadata(random, mode, permutation):
    return dict(noise_rng=canonical_digest(random.bit_generator.state),source_mode=mode,
        theta_to_body=mode != 'no_feedback',writing=True,gain=.2,rho=.002,lam=.001,sigma=.3,
        theta_start_zero=True,target_labels=False,
        source_permutation_sha256=hashlib.sha256(permutation.astype('<i8').tobytes()).hexdigest(),
        force_counterfactual='same-old-state/same-noise zero-theta next-V; diagnostic only')


def force_row(v, ref, field, actual, baseline, dt):
    centered = field-field.mean()
    impact = actual-baseline
    error = ref-v
    return np.array([field.mean(),field.std(),np.sqrt(np.mean((dt*centered)**2)),
        np.sqrt(np.mean(impact**2)),np.mean(impact*v),np.mean(impact*error),
        np.mean(np.abs(actual)==2.),np.sqrt(np.mean(error**2))],dtype=np.float64)


def replay_source(start, tissue, ladder, random, mode, permutation):
    state=tuple(x[None].copy() for x in start); theta=np.zeros((1,16,16))
    saved=[np.stack((*state,theta))[:,0]]; diagnostics=[]
    for t in range(1,1001):
        field = theta if mode == 'aligned' else theta.reshape(256)[permutation].reshape(1,16,16) if mode == 'scrambled' else np.zeros_like(theta)
        noise=random.standard_normal((1,16,16))
        baseline=physics.step(*state,np.zeros_like(theta),tissue,ladder,.2,.002,noise)
        advanced=physics.step(*state,field,tissue,ladder,.2,.002,noise)
        diagnostics.append(force_row(state[0],state[2],field,advanced[0],baseline[0],tissue.dt))
        state=advanced; theta=prior.project(.999*theta+.001*np.tanh(state[2]))
        if t in (1,300,1000): saved.append(np.stack((*state,theta))[:,0])
    return np.stack(saved),np.stack(diagnostics),source_metadata(random,mode,permutation)


def check_force_trace(forces, mode):
    assert forces.shape==(1000,8) and forces.dtype==np.float64 and np.isfinite(forces).all()
    np.testing.assert_allclose(forces[:,0],0.,rtol=0,atol=1e-14)
    np.testing.assert_array_equal(forces[0,:6],np.zeros(6))
    expected = np.zeros(1000) if mode=='no_feedback' else np.r_[0.,np.full(999,.3)]
    np.testing.assert_allclose(forces[:,1],expected,rtol=0,atol=1e-14)
    np.testing.assert_allclose(forces[:,2],.2*expected,rtol=0,atol=1e-14)
    assert np.all((forces[:,3]>=0)&(forces[:,3]<=4))
    assert np.all((forces[:,6]>=0)&(forces[:,6]<=1)) and np.all(forces[:,7]>=0)
    if mode=='no_feedback': np.testing.assert_array_equal(forces[:,:6],np.zeros((1000,6)))


def check_life(raw, meta, cfg, source, replay=True):
    keys = {'index','source_index','life','config','cases','times','reader_tag','source_tag',
        'origin_tag','source_start_checkpoint','source_start_reused','source_noise_reused',
        'source_trajectories_new','source_steps','source_times','modes','theta_start_zero',
        'source_rho','source_gain','source_lambda','writer_inputs','writer_rule',
        'latent_theta_transmitted','source_target_labels','source_context','source_paths',
        'tissue','ladder','blueprint','readers','force_metrics','source_address_rule'}
    assert set(meta) in (keys, keys | {'replay'})
    index, life = meta['index'], meta['life']
    assert type(index) is int and index in (*range(68000,68008),514226)
    assert type(life) is int and 0 <= life < cfg.lives
    assert meta['source_index'] == (514217 if index == 514226 else index-8000)
    nested(meta['config'],asdict(cfg)); nested(meta['cases'],[list(c) for c in CASES])
    nested(meta['times'],list(cfg.times)); nested(meta['source_times'],[0,1,300,1000])
    assert type(meta['source_steps']) is int and meta['source_steps'] == 1000
    assert type(meta['source_start_checkpoint']) is int and meta['source_start_checkpoint'] == 300
    nested(meta['writer_inputs'],['R_final']); nested(meta['modes'],list(MODES))
    nested(meta['force_metrics'],list(FORCE_METRICS))
    assert meta['source_address_rule']=='one fixed permutation per life/stratum; shared across roles'
    assert meta['writer_rule'] == 'project(tanh(R_final), .3)'
    assert (meta['source_rho'],meta['source_gain'],meta['source_lambda']) == (.002,.2,.001)
    for key in ('source_start_reused','source_trajectories_new','theta_start_zero'): assert meta[key] is True
    for key in ('source_noise_reused','latent_theta_transmitted','source_target_labels'): assert meta[key] is False
    assert meta['reader_tag'] == meta['source_tag'] == TAG and meta['origin_tag'] == 'l20-three-rewrite-v1'
    shapes = dict(targets=(2,16,16),source_starts=(2,3,3,16,16),
        source_states=(2,3,3,4,4,16,16),written_fields=(2,3,3,16,16),permutations=(2,3,256),
        source_forces=(2,3,3,1000,8),source_permutations=(3,256),
        packets=(28,3,2048),states=(28,3,len(cfg.times),3,16,16),values=(28,3,len(cfg.times),12))
    assert set(raw) == set(shapes)
    for key, shape in shapes.items():
        dtype = np.uint8 if key == 'packets' else np.int64 if key in ('permutations','source_permutations') else np.float64
        assert raw[key].shape == shape and raw[key].dtype == dtype and np.isfinite(raw[key]).all()
    np.testing.assert_array_equal(raw['targets'],prior.prior.targets())
    np.testing.assert_array_equal(raw['targets'],source['targets'][life])
    sm = meta['source_context']
    assert set(sm) == {'index','tissue','ladder','blueprint'} and sm['index'] == meta['source_index']
    stissue, sladder, sbp = physics.parameters(sm)
    assert (stissue.sigma,sbp.rho,sbp.c_m) == (.3,.002,.2)
    source_maximum = 0.; force_maximum = 0.; source_records = []
    for role, ci in ((0,0),(1,8)):
        generations = []
        for gi in range(3):
            start = source['generation_states'][life,ci,gi,4,:3]
            np.testing.assert_array_equal(raw['source_starts'][role,gi],start)
            permutation=generator(TAG,index,life,f'g{gi+1}:source_address').permutation(256)
            np.testing.assert_array_equal(raw['source_permutations'][gi],permutation)
            entries=[]
            for mi, mode in enumerate(MODES):
                start_state=np.concatenate((start,np.zeros((1,16,16))),axis=0)
                np.testing.assert_array_equal(raw['source_states'][role,gi,mi,0],start_state)
                random=generator(TAG,index,life,f'g{gi+1}:source')
                if replay:
                    states,forces,entry=replay_source(start,stissue,sladder,random,mode,permutation)
                    source_maximum=max(source_maximum,compare(raw['source_states'][role,gi,mi],states))
                    np.testing.assert_allclose(raw['source_forces'][role,gi,mi],forces,rtol=0,atol=1e-12)
                    force_maximum=max(force_maximum,float(np.max(np.abs(raw['source_forces'][role,gi,mi]-forces))))
                else:
                    for _ in range(1000): random.standard_normal((1,16,16))
                    entry=source_metadata(random,mode,permutation)
                check_force_trace(raw['source_forces'][role,gi,mi],mode)
                ref=raw['source_states'][role,gi,mi,-1,2]; candidate=np.tanh(ref)
                assert candidate.std()>1e-9,'degenerate source: fail rather than exclude'
                expected=prior.project(candidate)
                np.testing.assert_array_equal(raw['written_fields'][role,gi,mi],expected)
                assert abs(float(expected.mean()))<1e-14 and abs(float(expected.std())-.3)<1e-14
                latent=raw['source_states'][role,gi,mi,1:,3]
                assert np.all(np.abs(latent.mean(axis=(-2,-1)))<1e-14)
                assert np.all(np.abs(latent.std(axis=(-2,-1))-.3)<1e-14)
                entries.append(entry)
            assert len({entry['noise_rng'] for entry in entries})==1
            for mi in (1,2):
                np.testing.assert_array_equal(raw['source_states'][role,gi,0,1],raw['source_states'][role,gi,mi,1])
            generations.append(entries)
        source_records.append(generations)
    nested(meta['source_paths'],source_records)
    tissue, ladder, bp = physics.parameters(meta); maximum = source_maximum; records = []
    assert tissue.sigma == .3
    for ci, (role, kind) in enumerate(CASES):
        entries = []
        for gi, g in enumerate((1, 2, 3)):
            perm = generator(TAG, index, life, f'g{g}:shuffle:{role}').permutation(256)
            np.testing.assert_array_equal(raw['permutations'][role, gi], perm)
            bases=dict(zip(MODES,raw['written_fields'][role,gi]))
            if kind in ('ideal','zero'):
                expected=prior.project(np.tanh(1.5*prior.prior.targets()[role])) if kind=='ideal' else np.zeros((16,16))
            else:
                base=next(k for k in MODES if kind==k or kind.startswith(k+'_'))
                original=bases[base]
                expected=original.reshape(256)[perm].reshape(16,16) if kind.endswith('_shuffle') else original
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
    aliases = [((r, a), (r, b)) for r in (0, 1) for a, b in
               (('aligned','aligned_sham'),('scrambled','scrambled_sham'),('no_feedback','no_feedback_sham'),
                ('aligned_off','zero'),('scrambled_off','zero'),('no_feedback_off','zero'))]
    aliases.append(((0, 'zero'), (1, 'zero')))
    for a, b in aliases:
        np.testing.assert_array_equal(raw['states'][CASES.index(a)], raw['states'][CASES.index(b)])
    values = observe(raw['states'], raw['targets'], CASES, cfg)
    np.testing.assert_allclose(raw['values'], values, atol=1e-12, rtol=0)
    return dict(full_life_replay=replay, dynamics_max_abs=maximum,
        source_dynamics_max_abs=source_maximum, force_metric_max_abs=force_maximum,
        force_probe_steps=18000, metric_max_abs=float(abs(raw['values']-values).max()),
        reader_paths=84, exact_path_aliases=39, source_pairs=6, source_paths=18, packet_lineage_checked=True,
        fresh_reset=True, exact_signs=True, new_source_writer_paths=18)


def check_block(raw, meta, cfg, replay=True, root=None):
    from laws_confirmation import l20_source_address as p
    from laws_confirmation.io import DEFAULT_EXTERNAL_ROOT
    root = DEFAULT_EXTERNAL_ROOT if root is None else root
    assert set(meta) == {'index', 'config', 'source_sha256', 'lives'}
    index = meta['index']; assert type(index) is int and index in (*range(68000, 68008), 514226)
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
            force_metric_max_abs=proof['force_metric_max_abs'],force_probe_steps=18000,
            metric_max_abs=proof['metric_max_abs'], reader_paths=84, exact_path_aliases=39, source_pairs=6, source_paths=18,
            packet_lineage_checked=True, fresh_reset=True, exact_signs=True, new_source_writer_paths=18)
        nested(proof, expected)
        assert 0 <= proof['source_dynamics_max_abs'] <= proof['dynamics_max_abs'] <= 1e-10 and 0 <= proof['metric_max_abs'] <= 1e-12
        assert 0 <= proof['force_metric_max_abs'] <= 1e-12
        current = check_life({k: x[life] for k, x in raw.items()}, row, cfg, source, replay)
        if replay: nested(proof, current)
    return True


def check_source(raw, meta, source):
    keys = {'index', 'life', 'cases', 'times', 'tissue', 'ladder', 'blueprint', 'readers', 'known_outcomes', 'new_source_writer_paths', 'source_paths', 'force_metrics'}
    assert set(meta) in (keys, keys | {'replay'}) and set(raw) == {'packets', 'states', 'targets', 'source_starts', 'source_states', 'source_forces'}
    cases = tuple((r, k) for r in (0, 1) for k in ('rewrite', 'ideal', 'zero'))
    nested(meta['cases'], [list(c) for c in cases]); nested(meta['times'], [0, 1, 100, 300])
    assert meta['index'] == 514217 and meta['life'] == 0 and meta['known_outcomes'] is True and meta['new_source_writer_paths'] == 0
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
    nested(meta['force_metrics'],list(FORCE_METRICS))
    assert raw['source_forces'].shape==(2,3,1000,8)
    source_maximum=0.;force_maximum=0.;records=[];permutation=np.arange(256,dtype=np.int64)
    for role in (0,1):
        entries=[]
        for gi in range(3):
            start=source['generation_states'][0,role*8,gi,4,:3]
            np.testing.assert_array_equal(raw['source_starts'][role,gi],start)
            random=generator('l20-three-rewrite-v1',514217,0,f'g{gi+1}:write')
            states,forces,entry=replay_source(start,tissue,ladder,random,'aligned',permutation)
            source_maximum=max(source_maximum,compare(raw['source_states'][role,gi],states))
            np.testing.assert_array_equal(raw['source_states'][role,gi,1:],source['generation_states'][0,role*8,gi,5:8])
            np.testing.assert_allclose(raw['source_forces'][role,gi],forces,rtol=0,atol=1e-12)
            force_maximum=max(force_maximum,float(np.max(np.abs(raw['source_forces'][role,gi]-forces))))
            check_force_trace(raw['source_forces'][role,gi],'aligned');entries.append(entry)
        records.append(entries)
    nested(meta['source_paths'],records)
    return dict(known_reader_paths=6,full_reader_replay=True,max_abs=maximum,
        known_source_writer_paths=6,full_source_write_replay=True,source_max_abs=source_maximum,
        force_probe_steps=6000,force_metric_max_abs=force_maximum,
        new_source_writer_paths=0,whole_renewal_replayed=False,qualification_pool=False)


def force_summary(blocks, cfg):
    f=np.stack([b['source_forces'] for b in blocks])
    assert f.shape==(8,cfg.lives,2,3,3,1000,8) and np.isfinite(f).all()
    draws=generator(TAG,0,0,'bootstrap').integers(0,8,(10000,8));rows=[]
    for metric,name in enumerate(FORCE_METRICS):
        for stage in ('all',1,2,3):
            effects=[]
            for role in (0,1):
                panels=[]
                for gi in range(3) if stage=='all' else (stage-1,):
                    delta=f[:,:,role,gi,0,:,metric]-f[:,:,role,gi,1,:,metric]
                    panels.append(delta.mean(axis=-1))
                effects.append(np.stack(panels,axis=-1).mean(axis=-1))
            for role,effect in ((0,effects[0]),(1,effects[1]),('both',(effects[0]+effects[1])/2)):
                rows.append(dict(metric=name,stage=stage,role=role,**prior.stats(effect,draws)))
    return dict(metrics=list(FORCE_METRICS),modes=list(MODES),steps=list(range(1,1001)),
        mode_means=f.mean(axis=(0,1,2,3,5)).tolist(),aligned_minus_scrambled=rows,
        input_strength_matched=True,effective_force_matched=False,inferential_gate=False,
        secondary_intervals_multiplicity_adjusted=False)


def check_summary(summary, blocks, cfg):
    assert len(blocks) == 8
    values = np.stack([b['values'] for b in blocks])
    assert values.shape == (8, cfg.lives, 28, 3, len(cfg.times), 12) and np.isfinite(values).all()
    draws = generator(TAG, 0, 0, 'bootstrap').integers(0, 8, (10000, 8)); rows = []
    names = ('aligned_minus_scrambled','aligned_minus_no_feedback','scrambled_minus_no_feedback',
        'aligned_minus_aligned_shuffle','scrambled_minus_scrambled_shuffle','no_feedback_minus_no_feedback_shuffle',
        'ideal_minus_zero','aligned_minus_zero','scrambled_minus_zero','no_feedback_minus_zero','specificity_gain')
    for observer, col in (('qualified', 0), ('sign', 2)):
        for stage in ('all', 1, 2, 3):
            for name in names:
                effects = []
                for role in (0, 1):
                    weights = {'aligned': 1, 'aligned_shuffle': -1, 'scrambled': -1, 'scrambled_shuffle': 1} if name == 'specificity_gain' else dict(zip(name.split('_minus_'), (1, -1)))
                    effect = np.zeros((8, cfg.lives, 3 if stage == 'all' else 1))
                    for kind, weight in weights.items():
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
    for kind in MODES:
        specific = get(kind+'_minus_'+kind+'_shuffle')
        qualifies[kind] = bool(instrument and specific['pointwise_block_bootstrap_95'][0] > 0 and all(
            get(kind+'_minus_'+kind+'_shuffle', r)['mean'] > 0 and get(kind+'_minus_zero', r)['pointwise_block_bootstrap_95'][0] > 0 for r in (0, 1)))
    primary = get('aligned_minus_scrambled'); directions = [get('aligned_minus_scrambled', r) for r in (0, 1)]
    label = 'READOUT_NOT_QUALIFIED' if not instrument else 'ADDRESS_EFFECT_UNRESOLVED'
    if instrument:
        if qualifies['aligned'] and primary['pointwise_block_bootstrap_95'][0] > 0 and all(r['mean'] > 0 for r in directions): label = 'ALIGNED_ADVANTAGE_QUALIFIED'
        elif qualifies['scrambled'] and primary['pointwise_block_bootstrap_95'][1] < 0 and all(r['mean'] < 0 for r in directions): label = 'SCRAMBLED_ADVANTAGE_QUALIFIED'
    expected = dict(schema='l20_source_address_v1', label=label, primary=primary, directional_primary=directions,
        scrambled_readable=qualifies['scrambled'], aligned_readable=qualifies['aligned'],
        no_feedback_readable=qualifies['no_feedback'], readout_qualified=bool(instrument),
        source_force_audit=force_summary(blocks,cfg),
        readout_gates=gates, contrasts=rows, target_disagreement_cells=disagreements, cases=[list(c) for c in CASES],
        times=list(cfg.times), metrics=list(METRICS), cell_means=values.mean(axis=(0, 1)).tolist(),
        reader_blocks=list(range(68000, 68008)), source_blocks=list(range(60000, 60008)), blocks=8,
        lives_per_block=cfg.lives, generations_reused=3, reader_paths=8*cfg.lives*84, packet_bytes=2048,
        new_renewal_cohort=False,
        source_start_checkpoint=300, source_steps=1000, source_times=[0,1,300,1000],
        source_rho=.002, source_lambda=.001, source_gain=.2,
        source_starts_reused=True, source_noise_reused=False, new_source_writer_paths=8*cfg.lives*18,
        modes=list(MODES), latent_theta_transmitted=False, writer_inputs=['R_final'],
        record_rule='project(tanh(R_final), .3)', theta_start_zero=True,
        absolute_fidelity_gate=None,
        equivalence_test=False, secondary_intervals_multiplicity_adjusted=False)
    nested(summary, expected); return True


if __name__ == '__main__':
    from laws_confirmation.l20_source_address_run import main
    main(default_command='audit')

