"""Independent diagnostic/feature/model reconstruction; no production simulator calls."""
from __future__ import annotations
from dataclasses import asdict
import numpy as np
from laws_confirmation import l20_guide_renewal as old
from laws_confirmation import l15_repair_speed_run as io
from . import diagnostics as p

prior = old.checker()
physics = prior.physics
nested = physics.nested
GUIDE_SHA = '59459443afbb634446a72526c13d6dc2359a750aea3d923563793840e9998b4c'
TAG = 'l20-extension1-diagnostics-v1'
CASES = ((0, 'translated'), (0, 'aligned'), (1, 'translated'), (1, 'aligned'))


def corr(field, templates):
    centered = field - field.mean()
    scale = np.sqrt(np.mean(centered**2))
    values = np.zeros((2, 16, 16))
    if scale:
        for role in (0, 1):
            target = templates[role] - templates[role].mean()
            values[role] = np.fft.ifft2(np.fft.fft2(centered) * np.conj(np.fft.fft2(target))).real / (256*scale*np.sqrt(np.mean(target**2)))
    return values


def record_features(packet, role, guide):
    field = prior.unpack(packet)
    templates = prior.prior.targets()
    best = corr(field, templates).max(axis=(1, 2))
    routed, guide_scores, _ = prior.prior.select(packet, guide)
    f = prior.unpack(routed); f = f-f.mean(); scale = np.sqrt(np.mean(f*f))
    canonical = np.sum(templates*f, axis=(1, 2))/(256*scale) if scale else np.zeros(2)
    guide_best = guide_scores.max(axis=(1, 2))
    return np.array([best[role], best[role]-best[1-role], guide_best[role]-guide_best[1-role], canonical[role]-canonical[1-role]])


def terminal_features(v, role):
    own = prior.prior.targets()[role]; alternative = prior.prior.targets()[1-role]
    own_count = np.count_nonzero(((v > 0) == (own > 0)) & (np.abs(v) > .2))
    alternative_count = np.count_nonzero(((v > 0) == (alternative > 0)) & (np.abs(v) > .2))
    return np.array([(own_count-alternative_count)/256, np.sqrt(np.sum(v*v)/256)])


def check_life(raw, meta, founders, guide, replay=True):
    cohort, index, life = meta['cohort'], meta['index'], meta['life']
    legal = tuple(('d135', i) for i in range(75000, 75008)) + tuple(('d140', i) for i in range(78000, 78008)) + (('disposable', 514240),)
    assert type(index) is int and (cohort, index) in legal and type(life) is int and 0 <= life < 4
    host = index-2000 if cohort == 'd135' else index
    assert meta['host']['index'] == host
    assert set(meta) in ({'cohort','index','life','host','tag','config','cases','branches','cycles','guide_sha256',
                         'predictor_has_parent_state','diagnostic_to_lineage'},
                        {'cohort','index','life','host','tag','config','cases','branches','cycles','guide_sha256',
                         'predictor_has_parent_state','diagnostic_to_lineage','replay'})
    assert meta['tag'] == f'{TAG}:{cohort}' and meta['guide_sha256'] == GUIDE_SHA
    assert meta['predictor_has_parent_state'] is False and meta['diagnostic_to_lineage'] is False
    nested(meta['config'], asdict(p.CONFIG)); nested(meta['cases'], [list(c) for c in CASES]); nested(meta['branches'], ['U0','U1','C1'])
    tissue, ladder, bp = physics.parameters(meta['host'])
    assert prior.sha(guide.astype('<f8').tobytes()) == GUIDE_SHA
    cfg = p.CONFIG
    shapes = dict(founder_packets=(2,2048), guide=(2,16,16), sites=(64,), permutation=(64,),
        input=(4,3,2048), routed=(4,3,2048), outgoing=(4,3,2048), terminal_packet=(4,3,2048),
        read_states=(4,3,len(cfg.read_times),3,16,16), write_states=(4,3,len(cfg.source_times),4,16,16),
        terminal_states=(4,3,len(cfg.times),3,16,16), scores=(4,3,2,2,16,16), shift=(4,3,2),
        initial_features=(4,4), diagnostic_features=(4,3,6), input_strength=(4,3,2), changed_sites=(4,))
    assert set(raw) == set(shapes)
    for key, shape in shapes.items():
        dtype = np.uint8 if key in ('founder_packets','input','routed','outgoing','terminal_packet') else np.int64 if key in ('sites','permutation','shift','changed_sites') else np.float64
        assert raw[key].shape == shape and raw[key].dtype == dtype and np.isfinite(raw[key]).all(), key
    np.testing.assert_array_equal(raw['founder_packets'], founders); np.testing.assert_array_equal(raw['guide'], guide)
    random = lambda phase: physics.generator(f'{TAG}:{cohort}', index, life, phase)
    sites = random('mask').permutation(256)[:64]; permutation = random('permutation').permutation(64)
    np.testing.assert_array_equal(raw['sites'], sites); np.testing.assert_array_equal(raw['permutation'], permutation)
    rmax = wmax = tmax = smax = fmax = 0.; entries = []
    for ci, (role, mode) in enumerate(CASES):
        packet = founders[role].tobytes(); f = prior.unpack(packet).ravel(); shuffled = f.copy()
        for destination, source in zip(sites, sites[permutation]):
            shuffled[destination] = f[source]
        challenged = prior.packet(shuffled.reshape(16,16))
        np.testing.assert_array_equal(np.sort(shuffled), np.sort(f))
        assert raw['changed_sites'][ci] == np.count_nonzero(shuffled != f)
        np.testing.assert_allclose(raw['initial_features'][ci], record_features(packet, role, guide), rtol=0, atol=1e-12)
        case_entries = []
        for bi, incoming in enumerate((packet, packet, challenged)):
            trial = 0 if bi == 0 else 1
            draw = lambda phase: random(f'trial{trial}:{phase}')
            assert raw['input'][ci, bi].tobytes() == incoming
            field = prior.unpack(incoming)
            np.testing.assert_allclose(raw['input_strength'][ci, bi], [np.sum(field)/256, np.sqrt(np.sum(field**2)/256)], atol=1e-14, rtol=0)
            routed, scores, selection = prior.prior.select(incoming, guide)
            assert raw['routed'][ci, bi].tobytes() == routed
            np.testing.assert_allclose(raw['scores'][ci, bi, 0], scores, atol=1e-12, rtol=0)
            smax = max(smax, float(abs(raw['scores'][ci,bi,0]-scores).max()))
            reads, reader = prior.read_trace(routed, tissue, ladder, bp, draw('birth'), draw('read'), cfg, replay=replay)
            np.testing.assert_array_equal(raw['read_states'][ci, bi, 0], reads[0])
            if replay: rmax = max(rmax, physics.compare(raw['read_states'][ci, bi], reads))
            shift = np.array(divmod(int(draw('shift').integers(1,256)),16), np.int64)
            np.testing.assert_array_equal(raw['shift'][ci,bi], shift)
            start = raw['read_states'][ci,bi,-1]
            writes, writer = prior.write_trace(start, tissue, ladder, draw('write'), mode, shift, cfg, replay=replay)
            np.testing.assert_array_equal(raw['write_states'][ci,bi,0], np.concatenate((start, np.zeros((1,16,16)))))
            if replay: wmax = max(wmax, physics.compare(raw['write_states'][ci,bi], writes))
            ref = raw['write_states'][ci,bi,-1,2]; assert np.tanh(ref).std() > 1e-9
            outgoing = prior.packet(prior.project(np.tanh(ref)))
            assert raw['outgoing'][ci,bi].tobytes() == outgoing
            final_packet, scores, final_selection = prior.prior.select(outgoing, guide)
            assert raw['terminal_packet'][ci,bi].tobytes() == final_packet
            np.testing.assert_allclose(raw['scores'][ci,bi,1], scores, atol=1e-12, rtol=0)
            smax = max(smax, float(abs(raw['scores'][ci,bi,1]-scores).max()))
            terminal, final_reader = prior.read_trace(final_packet, tissue, ladder, bp, draw('final_birth'), draw('final_read'), cfg, times=cfg.times, replay=replay)
            np.testing.assert_array_equal(raw['terminal_states'][ci,bi,0], terminal[0])
            if replay: tmax = max(tmax, physics.compare(raw['terminal_states'][ci,bi], terminal))
            expected = np.r_[record_features(outgoing, role, guide), terminal_features(raw['terminal_states'][ci,bi,-1,0], role)]
            np.testing.assert_allclose(raw['diagnostic_features'][ci,bi], expected, atol=1e-12, rtol=0)
            fmax = max(fmax, float(abs(raw['diagnostic_features'][ci,bi]-expected).max()))
            case_entries.append(dict(trial=trial, mode=mode, selector=selection, reader=reader, writer=writer,
                terminal_selector=final_selection, terminal_reader=final_reader))
        entries.append(case_entries)
        # Matched U1/C1 births; independent U0 and final-reader births.
        np.testing.assert_array_equal(raw['read_states'][ci,1,0], raw['read_states'][ci,2,0])
        np.testing.assert_array_equal(raw['terminal_states'][ci,1,0], raw['terminal_states'][ci,2,0])
        assert not np.array_equal(raw['read_states'][ci,0,0], raw['read_states'][ci,1,0])
        for bi in range(3):
            assert not np.array_equal(raw['read_states'][ci,bi,0], raw['terminal_states'][ci,bi,0])
    nested(meta['cycles'], entries)
    for a, b in ((0,1),(2,3)):
        np.testing.assert_array_equal(raw['read_states'][a], raw['read_states'][b])
        np.testing.assert_array_equal(raw['write_states'][a,:,0:2], raw['write_states'][b,:,0:2])
    return dict(diagnostic_cycles=12, reader_paths=24, selectors=24,
        reader_max_abs=rmax, writer_max_abs=wmax, terminal_max_abs=tmax,
        selector_max_abs=smax, feature_max_abs=fmax, full_dynamics_replayed=bool(replay))


def check_block(raw, meta, replay=False):
    assert set(meta) == {'cohort','index','host_index','source_sha256','config','lives'}
    cohort, index = meta['cohort'], meta['index']
    a, b = p.source_paths(cohort,index)
    assert meta['source_sha256'] == io.hashes([a,b])
    source = io.load_npz(a)
    assert raw['outcomes'].shape == (4,4) and raw['outcomes'].dtype == np.float64
    assert len(meta['lives']) == 4 and meta['config'] == asdict(p.CONFIG)
    assert meta['host_index'] == (index-2000 if cohort == 'd135' else index)
    for life in range(4):
        m = meta['lives'][life]
        assert (m['cohort'],m['index'],m['life']) == (cohort,index,life)
        proof = check_life({k:v[life] for k,v in raw.items() if k != 'outcomes'}, m,
                           source['founder_packets'][life], source['guide'][life], replay)
        assert m['replay']['full_dynamics_replayed'] is True
        for key in ('diagnostic_cycles','reader_paths','selectors','selector_max_abs','feature_max_abs'):
            nested(m['replay'][key], proof[key])
        for key in ('reader_max_abs','writer_max_abs','terminal_max_abs'):
            assert type(m['replay'][key]) is float and 0 <= m['replay'][key] <= 1e-10
            if replay: nested(m['replay'][key], proof[key])
        for ci,(role,mode) in enumerate(CASES):
            ki = p.d140.CASES.index((role,mode)); ti = p.d140.PROBES.index((role,mode))
            np.testing.assert_array_equal(source['incoming'][life,ki,0], raw['founder_packets'][life,role])
            expected = terminal_features(source['terminal_states'][life,ti,-1,0],role)[0]
            assert raw['outcomes'][life,ci] == expected
    return True


def data(blocks):
    assert len(blocks) == 16
    start = np.stack([b['initial_features'] for b in blocks]).reshape(256,4)
    diagnostics = np.stack([b['diagnostic_features'] for b in blocks]).reshape(256,3,6)
    x = dict(starting_only=start, passive=np.column_stack((start, diagnostics[:,0], diagnostics[:,1])),
             challenge=np.column_stack((start, diagnostics[:,0], diagnostics[:,2])))
    return x, np.stack([b['outcomes'] for b in blocks]).reshape(256), np.tile(np.arange(4,dtype=np.int64),64), np.repeat(np.arange(16,dtype=np.int64),16)


def independent_fit(x, y, groups, alpha):
    means = np.array([np.sum(x[groups==g],axis=0)/np.sum(groups==g) for g in range(4)])
    offsets = np.array([np.sum(y[groups==g])/np.sum(groups==g) for g in range(4)])
    residual = x-means[groups]; scales = np.sqrt(np.sum(residual**2,axis=0)/len(x))
    scales = np.where(scales <= 1e-12, 1., scales)
    # Augmented least squares via SVD, independent of production normal equations.
    design = np.vstack((residual/scales, np.sqrt(len(x)*alpha)*np.eye(x.shape[1])))
    response = np.r_[y-offsets[groups], np.zeros(x.shape[1])]
    beta = np.linalg.lstsq(design,response,rcond=None)[0]
    return means, offsets, scales, beta


def independent_predict(fit, x, groups):
    means, offsets, scales, beta = fit
    return np.maximum(-1.,np.minimum(1.,offsets[groups]+np.sum((x-means[groups])/scales*beta,axis=1)))


def check_fit(result, x, y, groups, blocks):
    alphas = [.001,.01,.1,1.,10.,100.]
    assert set(result) == {'model','cv_alphas','cv_block_mse','cv_mse','selected_index','cv_predictions','blocks','prospective_evidence','preprocessing'}
    assert result['cv_alphas'] == alphas and result['blocks'] == list(range(16))
    assert result['prospective_evidence'] is False and result['preprocessing'] == 'training-only group centering and pooled residual SD'
    errors, predictions = np.zeros((6,16)), np.zeros((6,256))
    for ai,alpha in enumerate(alphas):
        for block in range(16):
            test = blocks==block
            fit = independent_fit(x[~test],y[~test],groups[~test],alpha)
            predictions[ai,test] = independent_predict(fit,x[test],groups[test])
            errors[ai,block] = np.sum((predictions[ai,test]-y[test])**2)/16
    means = errors.mean(axis=1)
    chosen = max(i for i in range(6) if means[i] <= means.min()+1e-12)
    assert result['selected_index'] == chosen
    for key,expected in (('cv_block_mse',errors),('cv_mse',means),('cv_predictions',predictions[chosen])):
        np.testing.assert_allclose(result[key],expected,rtol=0,atol=1e-10)
    fit = independent_fit(x,y,groups,alphas[chosen]); model = result['model']
    assert set(model) == {'alpha','features','group_feature_means','group_outcome_means','scales','coefficients','clip'}
    assert model['alpha'] == alphas[chosen] and model['features'] == x.shape[1] and model['clip'] == [-1.,1.]
    for key,expected in zip(('group_feature_means','group_outcome_means','scales','coefficients'),fit):
        np.testing.assert_allclose(model[key],expected,rtol=0,atol=1e-10)
    return True


def check_models(models, blocks):
    x,y,groups,ids = data(blocks)
    assert set(models) == {'stage','cohorts','feature_names','fits','heldout_outcomes_seen'}
    assert models['stage'] == 'DEVELOPMENT_ONLY' and models['cohorts'] == [list(c) for c in p.DEVELOPMENT]
    assert type(models['heldout_outcomes_seen']) is int and models['heldout_outcomes_seen'] == 0
    initial = list(p.INITIAL_FEATURES)
    names = initial+['U0:'+n for n in p.CYCLE_FEATURES]+['second:'+n for n in p.CYCLE_FEATURES]
    assert models['feature_names'] == {'starting_only':initial,'passive':names,'challenge':names}
    assert set(models['fits']) == set(x)
    for key in x: check_fit(models['fits'][key],x[key],y,groups,ids)
    return True


def check_summary(summary, models, blocks):
    _, y, groups, ids = data(blocks)
    rows = {}
    for key in ('starting_only', 'passive', 'challenge'):
        error = np.asarray(models['fits'][key]['cv_predictions'])-y
        rows[key] = dict(alpha=models['fits'][key]['model']['alpha'],
            cv_mse=float(np.dot(error,error)/256), cv_mae=float(np.sum(np.abs(error))/256),
            group_mse=[float(np.dot(error[groups==g],error[groups==g])/64) for g in range(4)],
            block_mse=[float(np.dot(error[ids==b],error[ids==b])/16) for b in range(16)])
    expected = dict(stage='DEVELOPMENT_ONLY',prospective_evidence=False,selection_affected_cv=True,
        independent_founder_blocks=16,cases=256,diagnostic_cycles=768,heldout_outcomes_seen=0,
        rows=rows,cv_mse_improvement=rows['passive']['cv_mse']-rows['challenge']['cv_mse'],
        interpretation='Development diagnostics only. No held-out forecast evidence or success claim.',
        automatic_successor=False)
    nested(summary,expected)
    return True
