"""D196 independent scalar checks and complete saved-summary reconstruction."""

import importlib.util
import math
from pathlib import Path
import numpy as np

_spec = importlib.util.spec_from_file_location('d194_independent', Path(__file__).with_name('check_l22_yoked_separation.py'))
old = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(old)
close = old.close
BLOCKS = (319100, 319101, 319102, 319103)
ARMS = ('LL', 'YL', 'LL_pulse', 'YL_pulse')
TIMES = (0, 1, 50, 250, 500, 1000)
FIELDS = old.FIELDS
BEHAVIOR = ('accuracy', 'partner_accuracy', 'preference', 'projection_gap', 'margin', 'winner_gap')
WEIGHTS = {'contingent_body_undisturbed': (1, -1, 0, 0),
    'contingent_body_disturbed': (0, 0, 1, -1), 'own_disturbance': (-1, 0, 1, 0),
    'yoked_disturbance': (0, -1, 0, 1), 'disturbance_interaction': (-1, 1, 1, -1)}


def addresses(bundle, parents, draws):
    n = 4*parents; traces, raws, readers = [bundle[k] for k in ('traces', 'raws', 'readers')]
    assert set(traces) == set(raws) == set(readers) == {'A', 'B'}
    assert bundle['codes'].shape == (4, 16, 16)
    for x in traces.values(): assert x.shape == (1001, n, 16, 16) and x.dtype == np.float64 and np.isfinite(x).all()
    np.testing.assert_array_equal(traces['A'][0], traces['B'][0])
    checkpoint = {f's{t}_{k}' for t in TIMES for k in ('V', 'ema', 'R', 'theta', 'S', 'body_input', 'writer_input')}
    event = {f'pulse_{phase}_{k}' for phase in ('before', 'after', 'step') for k in ('V', 'ema', 'R', 'theta')}
    for role in ('A', 'B'):
        other = 'B' if role == 'A' else 'A'; assert set(raws[role]) == set(ARMS)
        for arm in ARMS:
            raw = raws[role][arm]
            assert set(raw) == checkpoint | (event if arm.endswith('_pulse') else set())
            for x in raw.values(): assert x.shape == (n, 16, 16) and x.dtype == np.float64 and np.isfinite(x).all()
            for t in TIMES:
                np.testing.assert_array_equal(raw[f's{t}_S'], traces[role][0])
                np.testing.assert_array_equal(raw[f's{t}_writer_input'], raw[f's{t}_R'])
                if arm.startswith('YL'):
                    np.testing.assert_array_equal(raw[f's{t}_body_input'], traces[other][max(t-1, 0)])
                elif arm == 'LL' or t <= 500:
                    np.testing.assert_array_equal(raw[f's{t}_body_input'], traces[role][max(t-1, 0)])
                    np.testing.assert_array_equal(raw[f's{t}_R'], traces[role][t])
            if arm.endswith('_pulse'):
                base = raws[role][arm.removesuffix('_pulse')]
                for t in TIMES[:-1]:
                    for k in ('V', 'ema', 'R', 'theta', 'S', 'body_input', 'writer_input'):
                        np.testing.assert_array_equal(raw[f's{t}_{k}'], base[f's{t}_{k}'])
                for k in ('V', 'ema', 'R', 'theta'):
                    np.testing.assert_array_equal(raw['pulse_before_'+k], base['s500_'+k])
                    expected = raw['pulse_before_'+k].copy()
                    if k == 'V': expected[:, 4:12, 4:12] *= -1
                    np.testing.assert_array_equal(raw['pulse_after_'+k], expected)
        for t in (0, 1):
            for k in ('V', 'ema', 'R', 'theta', 'body_input', 'writer_input'):
                np.testing.assert_array_equal(raws[role]['LL'][f's{t}_{k}'], raws[role]['YL'][f's{t}_{k}'])
        assert set(readers[role]) == {'future_1', 'future_2'}
        for future in ('future_1', 'future_2'):
            assert set(readers[role][future]) == set(ARMS)
            for arm in ARMS:
                raw = readers[role][future][arm]
                np.testing.assert_array_equal(raw['s0_V'], readers[role][future]['LL']['s0_V'])
                for t in (0, 1, 1000):
                    np.testing.assert_array_equal(raw[f's{t}_theta'], np.repeat(raws[role][arm]['s1000_theta'], draws, axis=0))


def projection(x, codes, parents, reported):
    expected = []
    for i, field in enumerate(x):
        label = i//parents
        expected.append([math.fsum(float(v)*(float(a)-float(b)) for v,a,b in
            zip(field.flat, codes[label].flat, codes[(label+2)%4].flat))/256])
    close(reported, np.array(expected))


def contrast(cells, name, reported):
    shape = cells['LL'].shape
    expected = np.array([math.fsum(w*float(cells[a].flat[i]) for a,w in zip(ARMS,WEIGHTS[name]))
                         for i in range(cells['LL'].size)]).reshape(shape)
    close(reported, expected)


def expected_keys():
    keys = set()
    for f in ('common', 'residual'):
        for r in ('A', 'B'):
            for pair in ('undisturbed', 'disturbed', 'own_pulse', 'recorded_pulse'):
                for field in ('body_input', 'V', 'R', 'writer_drive', 'theta'):
                    for t in TIMES: keys.add(f'chain|{f}|{r}|{pair}|{field}|{t}')
            for phase in ('before', 'after', 'step'):
                for field in ('V', 'ema', 'R', 'theta'): keys.add(f'event_route|{f}|{r}|{phase}|{field}')
            for arm in ARMS[2:]:
                for jump in ('jump', 'first_response'):
                    for field in ('V', 'ema', 'R', 'theta'): keys.add(f'event|{f}|{r}|{arm}|{jump}|{field}')
                for phase in ('before', 'after', 'step'):
                    for field in ('V', 'R', 'writer_drive', 'theta'): keys.add(f'event_projection|{f}|{r}|{arm}|{phase}|{field}')
            for arm in ARMS:
                for field in ('V', 'R', 'writer_drive', 'theta'):
                    for t in TIMES: keys.add(f'projection|{f}|{r}|{arm}|{field}|{t}')
            for future in ('future_1', 'future_2'):
                for pair in ('undisturbed', 'disturbed', 'own_pulse', 'recorded_pulse'):
                    for t in (0, 1, 1000): keys.add(f'reader|{f}|{r}|{future}|{pair}|{t}')
                for arm in ARMS:
                    for section in ('behavior', 'scores', 'probabilities'): keys.add(f'{section}|{f}|{r}|{future}|{arm}')
                for name in WEIGHTS: keys.add(f'contrast|{f}|{r}|{future}|{name}')
    return keys


def summary(blocks, result, parents=4, draws=4):
    assert tuple(blocks) == BLOCKS and result['blocks'] == list(BLOCKS) and result['records'] == 16*parents
    assert all(set(x) == expected_keys() for x in blocks.values())
    assert result['schema'] == 'd196_pulse_mechanism_v1'
    assert result['families'] == ['common','residual'] and result['roles'] == ['A','B']
    assert result['futures'] == ['future_1','future_2'] and result['arms'] == list(ARMS)
    assert result['repair_times'] == list(TIMES) and result['reader_times'] == [0,1,1000]
    assert result['pair_fields'] == list(FIELDS) and result['behavior_fields'] == list(BEHAVIOR)
    assert result['contrasts'] == {k:list(v) for k,v in WEIGHTS.items()}
    assert result['retrospective'] and result['terminal_outcomes_previously_exposed'] and result['benchmark_excluded']
    assert not result['confirmatory'] and result['new_dynamics'] == result['fitted_models'] == 0 and not result['automatic_successor']
    view_keys = set()
    for key in expected_keys():
        parts = key.split('|'); section = parts[0]
        if section in ('scores', 'probabilities'): continue
        for role in (parts[2], 'role_mean'):
            p = parts.copy(); p[2] = role
            for future in ((parts[3], 'both') if section in ('reader', 'behavior', 'contrast') else (None,)):
                q = p.copy()
                if future is not None: q[3] = future
                view_keys.add('|'.join(q))
    assert set(result['views']) == view_keys
    assert set(result['transitions']) == {k for k in view_keys if k.startswith('contrast|')}
    def averaged_roles(parts, future):
        roles = ('A','B') if parts[2] == 'role_mean' else (parts[2],)
        arrays=[]
        for role in roles:
            p=parts.copy();p[2]=role
            if future is not None:p[3]=future
            arrays.append(np.stack([blocks[b]['|'.join(p)] for b in BLOCKS]))
        return np.array([math.fsum(float(a.flat[i]) for a in arrays)/len(arrays)
                         for i in range(arrays[0].size)]).reshape(arrays[0].shape)
    def means(a):
        return np.array([[[math.fsum(float(v) for v in a[b,i,:,k])/a.shape[2] for k in range(a.shape[3])]
                          for i in range(4*parents)] for b in range(4)])
    def count(xs):
        return dict(n=len(xs),improved=sum(x>2e-12 for x in xs),worsened=sum(x < -2e-12 for x in xs),
            tied=sum(abs(x)<=2e-12 for x in xs),net=math.fsum(xs)/len(xs),
            positive=math.fsum(max(x,0) for x in xs)/len(xs),negative=math.fsum(min(x,0) for x in xs)/len(xs))
    for key in sorted(view_keys):
        parts=key.split('|');section=parts[0];is_reader=section in ('reader','behavior','contrast')
        futures=('future_1','future_2') if is_reader and parts[3]=='both' else ((parts[3],) if is_reader else (None,))
        values=[averaged_roles(parts,f) for f in futures]
        a=np.concatenate(values,axis=2) if len(values)==2 else values[0]
        fields=BEHAVIOR if section in ('behavior','contrast') else (('projection_gap',) if 'projection' in section else FIELDS)
        old.describe(means(a) if is_reader else a,fields,parents,result['views'][key])
        if section=='contrast':
            expected={}
            for j,field in enumerate(BEHAVIOR[:3]):
                expected[field]=dict(records=count([math.fsum(float(v) for v in row)/len(row) for b in a[...,j] for row in b]),
                    draws=count([float(v) for v in a[...,j].flat]))
            close(result['transitions'][key],expected)
    changed=[]
    for b in BLOCKS:
        for f in ('common','residual'):
            for r in ('A','B'):
                for future in ('future_1','future_2'):
                    prefix=f'{f}|{r}|{future}'
                    cells={a:blocks[b][f'behavior|{prefix}|{a}'] for a in ARMS}
                    for name in WEIGHTS:contrast(cells,name,blocks[b][f'contrast|{prefix}|{name}'])
                    for i in range(4*parents):
                        for d in range(draws):
                            cs={name:blocks[b][f'contrast|{prefix}|{name}'][i,d] for name in WEIGHTS}
                            if not any(abs(float(x))>2e-12 for row in cs.values() for x in row[:3]):continue
                            changed.append(dict(block=b,family=f,role=r,future=future,record=i,message=i//parents,replicate=i%parents,draw=d,
                                contrasts={k:dict(zip(BEHAVIOR,map(float,v))) for k,v in cs.items()},
                                cells={a:dict(behavior=dict(zip(BEHAVIOR,map(float,cells[a][i,d]))),
                                    scores=list(map(float,blocks[b][f'scores|{prefix}|{a}'][i,d])),
                                    probabilities=list(map(float,blocks[b][f'probabilities|{prefix}|{a}'][i,d]))) for a in ARMS}))
    close(result['changed_draws'],changed)
    return dict(passes=True,views=len(view_keys),changed_draws=len(changed),independent_scalar_summary=True,new_dynamics=0)
