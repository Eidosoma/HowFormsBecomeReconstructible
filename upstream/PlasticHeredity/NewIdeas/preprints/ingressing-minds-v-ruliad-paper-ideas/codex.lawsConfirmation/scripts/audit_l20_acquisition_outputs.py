"""D116 independent parent/packet/reader reconstruction and block statistics.

Reuses separately restated D097 physics, not the production writer/reader,
observer or summarizer. Source code is available: not clean-room evidence.
"""
from dataclasses import asdict
import hashlib

import numpy as np

from laws_confirmation import l15_repair_speed as native
from laws_confirmation import l16_theta_content as old
from laws_confirmation.io import canonical_digest

physics = native.checker()
compare, nested, generator = physics.compare, physics.nested, physics.generator
independent_stats = old.checker().stats
TAG = 'l20-acquisition-only-v1'
KINDS = ('written', 'shuffled', 'sham', 'held', 'wrong', 'off', 'ideal')
CASES = tuple((r, k) for r in (0, 1) for k in KINDS)
PARENTS = tuple((r, w) for r in (0, 1) for w in (True, False))
METRICS = ('own_qualified', 'alternative_qualified', 'own_sign', 'alternative_sign',
    'amp_fraction', 'body_mean', 'body_rms', 'clip_fraction', 'roughness',
    'reference_mean', 'reference_rms', 'vr_mae')


def targets():
    y, x = np.indices((16, 16))
    return np.stack([np.where(y < 8, 1., -1.), np.where((x//4) % 2 == 0, 1., -1.)])


def project(x, norm=.3):
    centered = x-x.mean(axis=(-2, -1), keepdims=True)
    return centered*(norm/np.maximum(centered.std(axis=(-2, -1), keepdims=True), 1e-9))


def update(state, theta, tissue, ladder, bp, noise, writing):
    state = physics.step(*state, theta, tissue, ladder, bp.c_m, bp.rho, noise)
    if writing: theta = project((1-.001)*theta+.001*np.tanh(state[2]))
    return state, theta


def observe(raw, cfg):
    table = []
    for ci, (role, _) in enumerate(CASES):
        rows = []
        for v, _, ref in raw['states'][ci]:
            eligible = abs(v) > cfg.amp_threshold
            own, other = (v > 0) == (raw['targets'][role] > 0), (v > 0) == (raw['targets'][1-role] > 0)
            rough = (abs(v-v[:, (np.arange(16)-1) % 16]).sum()+abs(v-v[(np.arange(16)-1) % 16, :]).sum())/512
            rows.append([np.count_nonzero(own & eligible)/256, np.count_nonzero(other & eligible)/256,
                own.sum()/256, other.sum()/256, eligible.sum()/256, v.sum()/256, np.sqrt((v*v).sum()/256),
                np.count_nonzero(abs(v) == 2)/256, rough, ref.sum()/256, np.sqrt((ref*ref).sum()/256),
                abs(v-ref).sum()/256])
        table.append(rows)
    return np.asarray(table)


def check_life(raw, meta, cfg, replay=True):
    keys = {'index', 'life', 'config', 'cases', 'parents', 'tissue', 'ladder', 'blueprint',
        'parent_birth_rng', 'parent_settle_rng', 'teaching_rng', 'recipients', 'child_gain',
        'child_writing', 'packet_bytes', 'transmitted_fields', 'parent_settle_writing'}
    assert set(meta) in (keys, keys | {'replay'})
    shapes = dict(native_theta=(16,16), theta0=(16,16), parent_birth=(3,16,16), settled=(3,16,16),
        targets=(2,16,16), parent_states=(4,len(cfg.parent_times),4,16,16), permutations=(2,256),
        theta=(14,16,16), packets=(14,2048), states=(14,len(cfg.times),3,16,16), values=(14,len(cfg.times),12))
    assert set(raw) == set(shapes)
    for key, shape in shapes.items():
        assert raw[key].shape == shape and np.isfinite(raw[key]).all()
        assert raw[key].dtype == (np.int64 if key == 'permutations' else np.uint8 if key == 'packets' else np.float64)
    nested(meta['config'], asdict(cfg)); nested(meta['cases'], [list(c) for c in CASES])
    nested(meta['parents'], [list(c) for c in PARENTS])
    assert meta['child_writing'] is False and meta['parent_settle_writing'] is False
    assert meta['child_gain'] == 0. and meta['packet_bytes'] == 2048 and meta['transmitted_fields'] == ['theta']
    tissue, ladder, bp = physics.parameters(meta); index, life = meta['index'], meta['life']
    assert type(life) is int and 0 <= life < cfg.lives
    np.testing.assert_array_equal(raw['targets'], targets())
    theta_native = tissue.threshold_spread*generator(tissue.tissue_tag, index).standard_normal((16,16))
    np.testing.assert_array_equal(raw['native_theta'], theta_native)
    theta0 = project(theta_native); np.testing.assert_array_equal(raw['theta0'], theta0)
    random = generator(TAG, index, life, 'parent_birth')
    start = np.full((1,16,16), -1.); start[:, :, :8] = 1.
    v = start+tissue.copy_jitter*random.standard_normal((1,16,16))
    state = (v, v.copy(), v.copy())
    np.testing.assert_array_equal(raw['parent_birth'], np.stack(state)[:,0])
    assert meta['parent_birth_rng'] == canonical_digest(random.bit_generator.state)
    random = generator(TAG, index, life, 'parent_settle'); maximum = 0.
    for _ in range(cfg.settle):
        noise = random.standard_normal((1,16,16))
        if replay: state = physics.step(*state, theta0, tissue, ladder, bp.c_m, bp.rho, noise)
    if replay: maximum = max(maximum, compare(raw['settled'], np.stack(state)[:,0]))
    assert meta['parent_settle_rng'] == canonical_digest(random.bit_generator.state)
    parent_endings = []
    for pi, (role, writing) in enumerate(PARENTS):
        state = tuple(x[None].copy() for x in raw['settled']); field = theta0[None].copy()
        first = np.stack((*state, field))[:,0]
        np.testing.assert_array_equal(raw['parent_states'][pi, 0], first)
        random = generator(TAG, index, life, 'teaching'); saved = [first]
        for t in range(1, cfg.teaching+1):
            noise = random.standard_normal((1,16,16))
            if replay:
                state = (cfg.hold*targets()[role][None], state[1], state[2])
                state, field = update(state, field, tissue, ladder, bp, noise, writing)
                if t in cfg.parent_times: saved.append(np.stack((*state, field))[:,0])
        if replay: maximum = max(maximum, compare(raw['parent_states'][pi], np.stack(saved)))
        if not writing:
            np.testing.assert_array_equal(raw['parent_states'][pi,:,3], np.broadcast_to(theta0, (len(cfg.parent_times),16,16)))
        parent_endings.append(canonical_digest(random.bit_generator.state))
    nested(meta['teaching_rng'], parent_endings); assert len(set(parent_endings)) == 1
    perms = np.stack([generator(TAG, index, life, f'shuffle:{r}').permutation(256) for r in (0,1)])
    np.testing.assert_array_equal(raw['permutations'], perms)
    recipient_meta = []
    for ci, (role, kind) in enumerate(CASES):
        field = raw['parent_states'][PARENTS.index((role, True)), -1, 3].copy()
        if kind == 'shuffled': field = field.reshape(-1)[perms[role]].reshape(16,16)
        elif kind == 'sham':
            shuffled = field.ravel()[perms[role]]; restored = np.empty(256)
            for j, address in enumerate(perms[role]): restored[address] = shuffled[j]
            field = restored.reshape(16,16)
        elif kind == 'held': field = theta0.copy()
        elif kind == 'wrong': field = raw['parent_states'][PARENTS.index((1-role, True)), -1, 3].copy()
        elif kind == 'ideal': field = project(np.tanh(1.5*targets()[role]))
        np.testing.assert_array_equal(raw['theta'][ci], field)
        assert abs(float(field.mean())) <= 1e-14 and abs(float(field.std())-.3) <= 1e-14
        if kind in ('shuffled','sham'):
            np.testing.assert_array_equal(np.sort(field.ravel()), np.sort(raw['parent_states'][PARENTS.index((role, True)),-1,3].ravel()))
        packet = raw['packets'][ci].tobytes()
        assert packet == field.astype('<f8').tobytes(order='C')
        parsed = np.frombuffer(packet, '<f8').reshape(16,16).copy()
        applied = parsed if kind != 'off' else np.zeros_like(parsed)
        random = generator(TAG, index, life, 'child_birth')
        v = .2*random.standard_normal((1,16,16)); birth_digest = canonical_digest(random.bit_generator.state)
        state = (v, v.copy(), v.copy()); saved = [np.stack(state)[:,0]]
        np.testing.assert_array_equal(raw['states'][ci,0], saved[0])
        random = generator(TAG, index, life, 'child_noise')
        for t in range(1, cfg.steps+1):
            noise = random.standard_normal((1,16,16))
            if replay:
                state = physics.step(*state, applied, tissue, ladder, 0., bp.rho, noise)
                if t in cfg.times: saved.append(np.stack(state)[:,0])
        if replay: maximum = max(maximum, compare(raw['states'][ci], np.stack(saved)))
        recipient_meta.append(dict(birth_rng=birth_digest, noise_rng=canonical_digest(random.bit_generator.state),
                                   packet_sha256=hashlib.sha256(packet).hexdigest()))
    nested(meta['recipients'], recipient_meta)
    assert len({x['noise_rng'] for x in recipient_meta}) == len({x['birth_rng'] for x in recipient_meta}) == 1
    aliases = [((r,'written'),(r,'sham')) for r in (0,1)] + [((r,'written'),(1-r,'wrong')) for r in (0,1)] + [((0,'held'),(1,'held')),((0,'off'),(1,'off'))]
    for left, right in aliases:
        np.testing.assert_array_equal(raw['states'][CASES.index(left)], raw['states'][CASES.index(right)])
    values = observe(raw, cfg); np.testing.assert_allclose(raw['values'], values, rtol=0, atol=1e-12)
    return dict(full_life_replay=replay, dynamics_max_abs=maximum,
        metric_max_abs=float(abs(raw['values']-values).max()), exact_aliases=6,
        packet_only=True, equal_norms=True, exact_signs=True, parent_paths=4, descendant_paths=14)


def check_block(raw, meta, cfg, replay=True):
    assert set(meta) == {'index','config','lives'} and type(meta['index']) is int
    assert meta['index'] in (*range(59000,59008),514216)
    nested(meta['config'], asdict(cfg)); assert len(meta['lives']) == cfg.lives
    assert all(x.shape[0] == cfg.lives for x in raw.values())
    for life, row in enumerate(meta['lives']):
        assert row['index'] == meta['index'] and row['life'] == life
        proof = row['replay']
        assert set(proof) == {'full_life_replay','dynamics_max_abs','metric_max_abs','exact_aliases',
                             'packet_only','equal_norms','exact_signs','parent_paths','descendant_paths'}
        assert all(proof[k] is True for k in ('full_life_replay','packet_only','equal_norms','exact_signs'))
        assert (proof['exact_aliases'],proof['parent_paths'],proof['descendant_paths']) == (6,4,14)
        assert 0 <= proof['dynamics_max_abs'] <= 1e-10 and 0 <= proof['metric_max_abs'] <= 1e-12
        current = check_life({k:x[life] for k,x in raw.items()}, row, cfg, replay)
        if replay: nested(proof, current)
    return True


def check_summary(summary, blocks, cfg):
    assert len(blocks) == 8
    v = np.stack([b['values'] for b in blocks]); assert v.shape == (8,cfg.lives,14,len(cfg.times),12)
    assert np.isfinite(v).all()
    draws = generator(TAG,0,0,'bootstrap').integers(0,8,(10000,8)); rows = []
    for observer,col in (('qualified',0),('sign',2)):
        for ti,t in enumerate(cfg.times):
            for left,right in (('written','held'),('written','shuffled'),('written','wrong'),('written','off'),('ideal','off')):
                effects = []
                for role in (0,1):
                    li,ri = CASES.index((role,left)),CASES.index((role,right))
                    effects.append((v[:,:,li,ti,col]-v[:,:,li,ti,col+1])-(v[:,:,ri,ti,col]-v[:,:,ri,ti,col+1]))
                for role,effect in ((0,effects[0]),(1,effects[1]),('both',(effects[0]+effects[1])/2)):
                    rows.append(dict(name=left+'_minus_'+right,role=role,time=t,observer=observer,
                                     **independent_stats(effect,draws)))
    pick = lambda name, role='both': next(r for r in rows if r['name']==name and r['role']==role and r['time']==cfg.steps and r['observer']=='qualified')
    primary=pick('written_minus_held'); specificity=pick('written_minus_shuffled')
    directions=[pick('written_minus_held',r) for r in (0,1)]; gates=[pick('ideal_minus_off',r) for r in (0,1)]
    disagrees=[[int((b['targets'][l,0]!=b['targets'][l,1]).sum()) for l in range(cfg.lives)] for b in blocks]
    readable=all(x>0 for row in disagrees for x in row) and all(x['pointwise_block_bootstrap_95'][0]>0 for x in gates)
    positive=primary['pointwise_block_bootstrap_95'][0]>0 and specificity['pointwise_block_bootstrap_95'][0]>0 and all(x['mean']>0 for x in directions)
    expected=dict(schema='l20_acquisition_only_v1',tissues=list(range(59000,59008)),
        label='READOUT_NOT_QUALIFIED' if not readable else 'QUALIFIED_ACQUIRED_CONTENT' if positive else 'ACQUISITION_UNRESOLVED',
        primary=primary,specificity=specificity,directional_primary=directions,readout_gates=gates,
        readout_qualified=bool(readable),target_disagreement_cells=disagrees,contrasts=rows,
        cases=[list(c) for c in CASES],times=list(cfg.times),metrics=list(METRICS),cell_means=v.mean(axis=(0,1)).tolist(),
        blocks=8,lives_per_block=cfg.lives,packet_bytes=2048,boundaries=1,descendant_renewal=False,
        absolute_fidelity_gate=None,secondary_intervals_multiplicity_adjusted=False,independent_confirmation=False,
        independent_unit='random-stream/native-field block; fixed effective physics and targets')
    nested(summary,expected); return True


def check_source(raw, meta):
    assert set(raw)=={'prefix','theta_final','targets','transplant_states'}
    keys={'index','config','prefix_times','prefix_rng','transplant_rng','result','fidelity','freedom',
        'tissue','ladder','blueprint','full_source_executed','original_lineage_updates',
        'new_verification_not_historical_raw','whole_primary_reconstructed'}
    assert set(meta) in (keys,keys|{'replay'})
    assert all(x.dtype==np.float64 and np.isfinite(x).all() for x in raw.values())
    tissue,ladder,bp=physics.parameters(meta); cfg=meta['config']
    assert meta['index']==0 and meta['full_source_executed'] is True
    assert meta['new_verification_not_historical_raw'] is True and meta['whole_primary_reconstructed'] is False
    B=cfg['futures']; total=cfg['settle_sweeps']+cfg['imprint_sweeps']
    assert meta['original_lineage_updates']==total+cfg['cycles']*cfg['inter_fission']+cfg['zap_recover']
    times=sorted({0,1,cfg['settle_sweeps'],cfg['settle_sweeps']+1,total}); nested(meta['prefix_times'],times)
    target=np.stack([targets()[0]]*(B//2)+[targets()[1]]*(B-B//2))
    np.testing.assert_array_equal(raw['targets'],target)
    random=generator(cfg['trajectory_seed_tag'],'lineage','writable_fast',0,0)
    start=np.full((B,16,16),-1.); start[:,:,:8]=1.
    v=start+tissue.copy_jitter*random.standard_normal(start.shape); state=(v,v.copy(),v.copy())
    native_theta=tissue.threshold_spread*generator(tissue.tissue_tag,0).standard_normal((16,16))
    field=project(np.tile(native_theta,(B,1,1))); saved=[np.stack((*state,field))]
    for t in range(1,total+1):
        if t>cfg['settle_sweeps']: state=(cfg['imprint_hold']*target,state[1],state[2])
        state,field=update(state,field,tissue,ladder,bp,random.standard_normal(start.shape),True)
        if t in times: saved.append(np.stack((*state,field)))
    maximum=compare(raw['prefix'],np.stack(saved))
    nested(meta['prefix_rng'],[canonical_digest(random.bit_generator.state)])
    assert raw['theta_final'].shape==(B,16,16) and np.isfinite(raw['theta_final']).all()
    assert np.all(abs(raw['theta_final'].std(axis=(-2,-1))-.3)<1e-14)
    results={}; endings=[]
    for j,(b,label) in enumerate(((0,'groupA'),(B-1,'groupB'))):
        random=generator(cfg['trajectory_seed_tag'],'transplant','writable_fast',0,b)
        v=.2*random.standard_normal((2,16,16)); state=(v,v.copy(),v.copy()); saved=[np.stack(state)]
        theta=np.tile(raw['theta_final'][b],(2,1,1))
        for t in range(1,cfg['consensus_settle']+1):
            state=physics.step(*state,theta,tissue,ladder,0.,bp.rho,random.standard_normal(v.shape))
            if t in (1,cfg['consensus_settle']): saved.append(np.stack(state))
        maximum=max(maximum,compare(raw['transplant_states'][j],np.stack(saved)))
        results[label]=dict(match_A=float(((state[0]>0)==(target[0]>0)).mean()),
                            match_B=float(((state[0]>0)==(target[-1]>0)).mean()))
        endings.append(canonical_digest(random.bit_generator.state))
    results['own_target_margin']=(results['groupA']['match_A']-results['groupA']['match_B']+
        results['groupB']['match_B']-results['groupB']['match_A'])/2
    nested(meta['result'],results); nested(meta['transplant_rng'],endings)
    return dict(source_prefix_and_transplant_replayed=True,full_source_lineage_replayed=False,
        max_abs=maximum,source_parent_futures=B,transplant_paths=4,whole_primary_reconstructed=False)


if __name__=='__main__':
    from laws_confirmation.l20_acquisition_run import main
    main(default_command='audit')
