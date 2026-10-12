"""D128 independent packet addressing, reader dynamics, observer and inference."""
from dataclasses import asdict
import hashlib

import numpy as np

from laws_confirmation import l20_three_rewrite as old
from laws_confirmation.io import canonical_digest, sha256_file

prior = old.checker()
physics = prior.physics
compare, nested, generator = physics.compare, physics.nested, physics.generator
TAG = 'l20-inverse-address-v1'
BASES=('translated','rescued','aligned','aligned_inverse')
KINDS=('translated','rescued','aligned','aligned_inverse',
    'translated_shuffle','rescued_shuffle','aligned_shuffle','aligned_inverse_shuffle',
    'translated_sham','rescued_sham','aligned_sham','aligned_inverse_sham',
    'translated_off','rescued_off','aligned_off','aligned_inverse_off',
    'ideal','ideal_shifted','ideal_rescued','zero')
CASES=tuple((r,k) for r in (0,1) for k in KINDS)
SOURCE_KINDS=('aligned','translated','no_feedback','aligned_shuffle','translated_shuffle','no_feedback_shuffle',
    'aligned_sham','translated_sham','no_feedback_sham','aligned_off','translated_off','no_feedback_off','ideal','zero')
SOURCE_CASES=tuple((r,k) for r in (0,1) for k in SOURCE_KINDS)
METRICS = prior.METRICS
packet, unpack, sha = prior.packet, prior.unpack, prior.sha
observe = prior.observe


def shifted(field,shift,inverse=True):
    dy,dx=(int(x) for x in shift);sign=1 if inverse else -1
    return np.asarray([[field[(y+sign*dy)%16,(x+sign*dx)%16]
        for x in range(16)] for y in range(16)],dtype=np.float64)


def check_life(raw,meta,cfg,source,replay=True):
    keys={'index','source_index','life','config','cases','times','reader_tag','source_tag',
        'source_reused','source_checkpoint','source_trajectories_new','new_source_writes',
        'packet_inputs','record_rule','record_reprojected','inverse_is_analyst_supplied',
        'source_shift_transmitted','tissue','ladder','blueprint','readers'}
    assert set(meta) in (keys,keys|{'replay'})
    index,life=meta['index'],meta['life']
    assert type(index) is int and index in (*range(70000,70008),514228)
    assert type(life) is int and 0<=life<cfg.lives
    assert meta['source_index']==(514227 if index==514228 else index-1000)
    nested(meta['config'],asdict(cfg));nested(meta['cases'],[list(c) for c in CASES]);nested(meta['times'],list(cfg.times))
    assert type(meta['source_checkpoint']) is int and meta['source_checkpoint']==1000
    assert type(meta['new_source_writes']) is int and meta['new_source_writes']==0
    nested(meta['packet_inputs'],['saved_packet_bytes','declared_source_shift'])
    assert meta['record_rule']=='native bytes or one inverse source shift; no normalization'
    assert meta['reader_tag']==TAG and meta['source_tag']=='l20-source-translation-v1'
    for k in ('source_reused','inverse_is_analyst_supplied'): assert meta[k] is True
    for k in ('source_trajectories_new','record_reprojected','source_shift_transmitted'): assert meta[k] is False
    shapes=dict(targets=(2,16,16),source_packets=(2,3,2,2048),source_shifts=(3,2),
        prepared_fields=(2,3,4,16,16),permutations=(2,3,256),
        packets=(40,3,2048),states=(40,3,len(cfg.times),3,16,16),values=(40,3,len(cfg.times),12))
    assert set(raw)==set(shapes)
    for key,shape in shapes.items():
        dtype=np.uint8 if key in ('packets','source_packets') else np.int64 if key in ('permutations','source_shifts') else np.float64
        assert raw[key].shape==shape and raw[key].dtype==dtype and np.isfinite(raw[key]).all()
    np.testing.assert_array_equal(raw['targets'],prior.prior.targets())
    np.testing.assert_array_equal(raw['targets'],source['targets'][life])
    for gi in range(3):
        code=int(generator('l20-source-translation-v1',meta['source_index'],life,f'g{gi+1}:source_shift').integers(1,256))
        shift=np.asarray(divmod(code,16),dtype=np.int64)
        assert shift.any()
        np.testing.assert_array_equal(raw['source_shifts'][gi],shift)
        np.testing.assert_array_equal(raw['source_shifts'][gi],source['source_shifts'][life,gi])
        for role in (0,1):
            kept=np.stack([source['packets'][life,SOURCE_CASES.index((role,k)),gi] for k in ('translated','aligned')])
            np.testing.assert_array_equal(raw['source_packets'][role,gi],kept)
            translated,aligned=(unpack(b.tobytes()) for b in kept)
            fields=np.stack((translated,shifted(translated,shift),aligned,shifted(aligned,shift)))
            np.testing.assert_array_equal(raw['prepared_fields'][role,gi],fields)
            for field in fields:
                assert abs(float(field.mean()))<1e-14 and abs(float(field.std())-.3)<1e-14
            for a,b in ((0,1),(2,3)):
                np.testing.assert_array_equal(np.sort(fields[a].ravel()),np.sort(fields[b].ravel()))
                np.testing.assert_array_equal(shifted(fields[b],shift,False),fields[a])
    tissue, ladder, bp = physics.parameters(meta); maximum = 0.; records = []
    for ci, (role, kind) in enumerate(CASES):
        entries = []
        for gi, g in enumerate((1, 2, 3)):
            perm = generator(TAG, index, life, f'g{g}:shuffle:{role}').permutation(256)
            np.testing.assert_array_equal(raw['permutations'][role, gi], perm)
            shift=raw['source_shifts'][gi]
            bases=dict(zip(BASES,raw['prepared_fields'][role,gi]))
            if kind in ('ideal','ideal_shifted','ideal_rescued'):
                ideal=prior.project(np.tanh(1.5*prior.prior.targets()[role]))
                expected=shifted(ideal,shift,False) if kind=='ideal_shifted' else ideal
            elif kind=='zero': expected=np.zeros((16,16))
            else:
                base=next(k for k in BASES if kind==k or kind in (k+'_shuffle',k+'_sham',k+'_off'))
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
    aliases=[((r,k),(r,k+'_sham')) for r in (0,1) for k in BASES]
    aliases += [((r,k+'_off'),(r,'zero')) for r in (0,1) for k in BASES]
    aliases += [((r,'ideal_rescued'),(r,'ideal')) for r in (0,1)]+[((0,'zero'),(1,'zero'))]
    for a, b in aliases:
        np.testing.assert_array_equal(raw['states'][CASES.index(a)], raw['states'][CASES.index(b)])
    values = observe(raw['states'], raw['targets'], CASES, cfg)
    np.testing.assert_allclose(raw['values'], values, atol=1e-12, rtol=0)
    return dict(full_life_replay=replay, dynamics_max_abs=maximum, metric_max_abs=float(abs(raw['values']-values).max()),
        reader_paths=120, exact_path_aliases=57, source_pairs=6, packet_lineage_checked=True,
        fresh_reset=True, exact_signs=True, new_source_writes=0)


def check_block(raw, meta, cfg, replay=True, root=None):
    from laws_confirmation import l20_inverse_address as p
    from laws_confirmation.io import DEFAULT_EXTERNAL_ROOT
    root = DEFAULT_EXTERNAL_ROOT if root is None else root
    assert set(meta) == {'index', 'config', 'source_sha256', 'lives'}
    index = meta['index']; assert type(index) is int and index in (*range(70000, 70008), 514228)
    nested(meta['config'], asdict(cfg)); assert len(meta['lives']) == cfg.lives
    assert all(x.shape[0] == cfg.lives for x in raw.values())
    # Shared I/O only; source addressing and all new physics above are independent.
    source, _ = p.load_source(index, root)
    assert meta['source_sha256'] == {str(x): sha256_file(x) for x in p.source_paths(index, root)}
    for life, row in enumerate(meta['lives']):
        assert row['index'] == index and row['life'] == life
        proof = row['replay']
        expected = dict(full_life_replay=True, dynamics_max_abs=proof['dynamics_max_abs'],
            metric_max_abs=proof['metric_max_abs'], reader_paths=120, exact_path_aliases=57, source_pairs=6,
            packet_lineage_checked=True, fresh_reset=True, exact_signs=True, new_source_writes=0)
        nested(proof, expected)
        assert 0 <= proof['dynamics_max_abs'] <= 1e-10 and 0 <= proof['metric_max_abs'] <= 1e-12
        current = check_life({k: x[life] for k, x in raw.items()}, row, cfg, source, replay)
        if replay: nested(proof, current)
    return True


def check_source(raw,meta,source):
    keys={'index','life','cases','times','tissue','ladder','blueprint','readers','known_outcomes','new_source_writes'}
    assert set(meta) in (keys,keys|{'replay'}) and set(raw)=={'packets','states','targets'}
    cases=tuple((r,k) for r in (0,1) for k in ('aligned','translated','ideal','zero'))
    nested(meta['cases'],[list(c) for c in cases]);nested(meta['times'],[0,1,100,300])
    assert meta['index']==514227 and meta['life']==0 and meta['known_outcomes'] is True and meta['new_source_writes']==0
    indices=[SOURCE_CASES.index(c) for c in cases]
    np.testing.assert_array_equal(raw['packets'],source['packets'][0,indices])
    np.testing.assert_array_equal(raw['states'],source['states'][0,indices])
    np.testing.assert_array_equal(raw['targets'],prior.prior.targets())
    tissue,ladder,bp=physics.parameters(meta);maximum=0.;records=[]
    for ci in range(8):
        row=[]
        for gi in range(3):
            supplied=raw['packets'][ci,gi].tobytes()
            random=generator('l20-source-translation-v1',514227,0,f'g{gi+1}:birth')
            v=.2*random.standard_normal((1,16,16));birth=canonical_digest(random.bit_generator.state)
            state=(v,v.copy(),v.copy());saved=[np.stack(state)[:,0]]
            random=generator('l20-source-translation-v1',514227,0,f'g{gi+1}:read')
            for t in range(1,301):
                state=physics.step(*state,unpack(supplied),tissue,ladder,0.,bp.rho,random.standard_normal((1,16,16)))
                if t in (1,100,300): saved.append(np.stack(state)[:,0])
            maximum=max(maximum,compare(raw['states'][ci,gi],np.stack(saved)))
            row.append(dict(birth_rng=birth,read_rng=canonical_digest(random.bit_generator.state),
                input_sha256=sha(supplied),packet_bytes=2048,enabled=True,writing=False,gain=0.,target_labels=False))
        records.append(row)
    nested(meta['readers'],records)
    return dict(known_reader_paths=24,full_reader_replay=True,max_abs=maximum,
        new_source_writes=0,whole_renewal_replayed=False,qualification_pool=False)


def check_summary(summary, blocks, cfg):
    assert len(blocks) == 8
    values = np.stack([b['values'] for b in blocks])
    assert values.shape == (8, cfg.lives, 40, 3, len(cfg.times), 12) and np.isfinite(values).all()
    draws = generator(TAG, 0, 0, 'bootstrap').integers(0, 8, (10000, 8)); rows = []
    names=('rescued_minus_translated','aligned_inverse_minus_aligned','rescued_minus_aligned','translated_minus_aligned',
        'translated_minus_translated_shuffle','rescued_minus_rescued_shuffle','aligned_minus_aligned_shuffle',
        'aligned_inverse_minus_aligned_inverse_shuffle','translated_minus_zero','rescued_minus_zero','aligned_minus_zero',
        'aligned_inverse_minus_zero','ideal_minus_zero','ideal_rescued_minus_ideal_shifted','ideal_shifted_minus_zero',
        'specificity_gain','source_interaction')
    for observer, col in (('qualified', 0), ('sign', 2)):
        for stage in ('all', 1, 2, 3):
            for name in names:
                effects = []
                for role in (0, 1):
                    if name=='specificity_gain': weights={'rescued':1,'rescued_shuffle':-1,'translated':-1,'translated_shuffle':1}
                    elif name=='source_interaction': weights={'rescued':1,'translated':-1,'aligned_inverse':-1,'aligned':1}
                    else: weights=dict(zip(name.split('_minus_'),(1,-1)))
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
    for kind in BASES:
        specific = get(kind+'_minus_'+kind+'_shuffle')
        qualifies[kind] = bool(instrument and specific['pointwise_block_bootstrap_95'][0] > 0 and all(
            get(kind+'_minus_'+kind+'_shuffle', r)['mean'] > 0 and get(kind+'_minus_zero', r)['pointwise_block_bootstrap_95'][0] > 0 for r in (0, 1)))
    calibration_gates=[get('ideal_rescued_minus_ideal_shifted',r) for r in (0,1)]
    calibration=bool(instrument and all(x['pointwise_block_bootstrap_95'][0]>0 for x in calibration_gates))
    primary=get('rescued_minus_translated');directions=[get('rescued_minus_translated',r) for r in (0,1)]
    label='READOUT_NOT_QUALIFIED' if not instrument else 'RESCUE_CONTROL_NOT_QUALIFIED' if not calibration else 'INVERSE_EFFECT_UNRESOLVED'
    if instrument and calibration:
        if primary['pointwise_block_bootstrap_95'][0]>0 and all(r['mean']>0 for r in directions):
            label='INVERSE_RESCUE_QUALIFIED' if qualifies['rescued'] else 'INVERSE_GAIN_WITHOUT_CONTENT_QUALIFICATION'
        elif primary['pointwise_block_bootstrap_95'][1]<0 and all(r['mean']<0 for r in directions):
            label='INVERSE_HARM_DETECTED'
    expected=dict(schema='l20_inverse_address_v1',label=label,primary=primary,directional_primary=directions,
        content_qualified=qualifies,readout_qualified=bool(instrument),calibration_qualified=calibration,
        readout_gates=gates,calibration_gates=calibration_gates,contrasts=rows,target_disagreement_cells=disagreements,
        cases=[list(c) for c in CASES],times=list(cfg.times),metrics=list(METRICS),
        cell_means=values.mean(axis=(0,1)).tolist(),reader_blocks=list(range(70000,70008)),source_blocks=list(range(69000,69008)),
        blocks=8,lives_per_block=cfg.lives,generations_reused=3,reader_paths=8*cfg.lives*120,
        packet_bytes=2048,reused_source_histories=True,new_renewal_cohort=False,new_source_writes=0,
        source_checkpoint=1000,packet_inputs=['saved_packet_bytes','declared_source_shift'],
        record_rule='native bytes or one inverse source shift; no normalization',
        record_reprojected=False,inverse_is_analyst_supplied=True,source_shift_transmitted=False,
        absolute_fidelity_gate=None,equivalence_test=False,secondary_intervals_multiplicity_adjusted=False)
    nested(summary, expected); return True


if __name__ == '__main__':
    from laws_confirmation.l20_inverse_address_run import main
    main(default_command='audit')
