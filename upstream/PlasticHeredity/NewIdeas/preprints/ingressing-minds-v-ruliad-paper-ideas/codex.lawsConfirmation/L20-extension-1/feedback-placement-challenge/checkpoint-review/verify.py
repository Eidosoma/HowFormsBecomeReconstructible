"""Independent scalar/gather checks of D175's saved-field measurements."""
import numpy as np


def direct_pair(u, p):
    a, b = u.ravel(), p.ravel()
    n = len(a)
    sqrtmean = lambda z: float(np.sqrt(np.dot(z, z)/n))
    ac, bc = a-a.sum()/n, b-b.sum()/n
    au, bu = sqrtmean(ac), sqrtmean(bc)
    valid = au != 0 and bu != 0
    return [sqrtmean(b-a), sqrtmean(a), sqrtmean(b),
            sqrtmean(bc/bu-ac/au) if valid else 0.], valid


def template(role):
    t = np.ones((16, 16))
    if role == 0:
        t[8:] = -1
    else:
        t[:, 4:8] = -1; t[:, 12:] = -1
    return t


def q(role, shift):
    y, x = np.indices((16, 16)); dy, dx = shift
    t = template(role)
    return float((t*t[(y-dy) % 16, (x-dx) % 16]).sum()/256)


def block(raw, got):
    assert set(got) == {'distance', 'shape_valid', 'entry', 'q', 'endpoint', 'routing'}
    assert got['distance'].shape == (4, 4, 36, 4)
    maximum = 0.
    y, x = np.indices((16, 16))
    for life in range(4):
        for group in range(4):
            arms = []
            for arm in range(2):
                states = [raw['write_states'][life, group, arm, t, k]
                          for t in range(7) for k in range(4)]
                end = raw['write_states'][life, group, arm, 6, 2]
                packet = lambda name: np.frombuffer(raw[name][life, group, arm].tobytes(), '<f8').reshape(16, 16)
                states += [end, np.tanh(end), packet('outgoing'), packet('terminal_packet')]
                states += [raw['terminal_states'][life, group, arm, t, 0] for t in range(4)]
                arms.append(states)
                v = states[-1]; own = template(group//2); other = template(1-group//2)
                counts = [np.count_nonzero(((v > 0) == (t > 0)) & (abs(v) > .2)) for t in (own, other)]
                want = np.array([(counts[0]-counts[1])/256, np.sqrt(np.sum(v*v)/256)])
                np.testing.assert_allclose(got['endpoint'][life, group, arm, 4:], want, atol=1e-12, rtol=0)
            for stage, (u, p) in enumerate(zip(*arms)):
                value, valid = direct_pair(u, p)
                np.testing.assert_allclose(got['distance'][life, group, stage], value, atol=2e-12, rtol=0)
                assert got['shape_valid'][life, group, stage] == valid
                maximum = max(maximum, float(np.max(abs(got['distance'][life, group, stage]-value))))
            shift = raw['shift'][life, group, 0] if group % 2 == 0 else (0, 0)
            dy, dx = shift; theta = raw['write_states'][life, group, 0, 2, 3]
            base = theta[(y-dy) % 16, (x-dx) % 16]
            moved = theta[(y-dy-2) % 16, (x-dx-1) % 16]
            entry = [np.sqrt(np.sum((moved-base)**2)/256), np.sqrt(np.sum(base**2)/256)]
            np.testing.assert_allclose(got['entry'][life, group], entry, atol=1e-12, rtol=0)
            before, during = q(group//2, shift), q(group//2, (dy+2, dx+1))
            np.testing.assert_array_equal(got['q'][life, group], [before, during, during-before])
            for arm in range(2):
                score = raw['scores'][life, group, arm, 1]
                peaks = [float(np.max(score[i])) for i in range(2)]
                family = -1 if abs(peaks[0]-peaks[1]) <= 1e-12 else int(peaks[1] > peaks[0])
                choices = [(i, j) for i in range(16) for j in range(16)
                           if family >= 0 and abs(score[family, i, j]-peaks[family]) <= 1e-12]
                shift = choices[0] if choices else (0, 0)
                np.testing.assert_array_equal(got['routing'][life, group, arm], [family, *shift])
    np.testing.assert_array_equal(got['endpoint'], raw['diagnostic_features'])
    return dict(passes=True, matched_cases=16, measured_fields=576, maximum_residual=maximum,
                tissue_dynamics_replayed=False, outcomes_loaded=False)


def summary(arrays, report):
    """Independent scalar reconstruction of the complete fixed aggregation."""
    assert report['blocks'] == list(range(90000, 90016)) and report['cases'] == 256
    assert len(report['groups']) == 4
    for g, row in enumerate(report['groups']):
        for s, stage in enumerate(row['stages']):
            d = arrays['distance'][:, :, g, s]
            v = arrays['shape_valid'][:, :, g, s]
            assert stage['n'] == 64 and stage['shape_valid'] == np.count_nonzero(v)
            assert stage['shape_invalid'] == 64-np.count_nonzero(v)
            values = [float(d[b, l, 0]) for b in range(16) for l in range(4)]
            np.testing.assert_allclose(stage['mean_delta'], sum(values)/64, atol=1e-12, rtol=0)
            np.testing.assert_allclose(stage['rms_delta'], np.sqrt(sum(x*x for x in values)/64), atol=1e-12, rtol=0)
            for arm, key in ((1, 'mean_U_rms'), (2, 'mean_P_rms')):
                np.testing.assert_allclose(stage[key], sum(float(d[b, l, arm]) for b in range(16) for l in range(4))/64, atol=1e-12, rtol=0)
            shape = [float(d[b, l, 3]) for b in range(16) for l in range(4) if v[b, l]]
            assert (stage['shape_distance'] is None) == (not shape)
            if shape:
                np.testing.assert_allclose(stage['shape_distance'], sum(shape)/len(shape), atol=1e-12, rtol=0)
            assert len(stage['founders']) == 16
            for b, founder in enumerate(stage['founders']):
                assert founder['id'] == 90000+b
                np.testing.assert_allclose(founder['mean_delta'], sum(values[4*b:4*b+4])/4, atol=1e-12, rtol=0)
                np.testing.assert_allclose(founder['rms_delta'], np.sqrt(sum(z*z for z in values[4*b:4*b+4])/4), atol=1e-12, rtol=0)
                shape_b = [float(d[b, l, 3]) for l in range(4) if v[b, l]]
                assert founder['shape_valid'] == len(shape_b)
                assert (founder['shape_distance'] is None) == (not shape_b)
                if shape_b:
                    np.testing.assert_allclose(founder['shape_distance'], sum(shape_b)/len(shape_b), atol=1e-12, rtol=0)
        for k, recovery in enumerate(row['recovery']):
            start = arrays['distance'][:, :, g, 4*4+k, 0]
            end = arrays['distance'][:, :, g, 6*4+k, 0]
            sums = [sum(float(x*x) for x in a.ravel()) for a in (end, start)]
            if sums[1]:
                np.testing.assert_allclose(recovery['rms_ratio'], np.sqrt(sums[0]/sums[1]), atol=1e-12, rtol=1e-12)
            else:
                assert recovery['rms_ratio'] is None
            for key, mask in (('smaller', end < start), ('equal', end == start),
                              ('larger', end > start), ('zero_denominators', start == 0)):
                assert recovery[key] == np.count_nonzero(mask)
            for b, founder in enumerate(recovery['founders']):
                assert founder['id'] == 90000+b
                den = sum(float(x*x) for x in start[b])
                if den:
                    np.testing.assert_allclose(founder['rms_ratio'], np.sqrt(sum(float(x*x) for x in end[b])/den), atol=1e-12, rtol=1e-12)
                else:
                    assert founder['rms_ratio'] is None
        for j, feature in enumerate(row['endpoint']):
            d = arrays['endpoint'][:, :, g, 1, j]-arrays['endpoint'][:, :, g, 0, j]
            means = [sum(float(x) for x in d[b])/4 for b in range(16)]
            np.testing.assert_allclose(feature['founder_deltas'], means, atol=1e-12, rtol=0)
            np.testing.assert_allclose(feature['mean_delta'], sum(means)/16, atol=1e-12, rtol=0)
            np.testing.assert_allclose(feature['mean_absolute_delta'], sum(abs(float(x)) for x in d.ravel())/64, atol=1e-12, rtol=0)
            for arm, key in ((0, 'mean_U'), (1, 'mean_P')):
                values = arrays['endpoint'][:, :, g, arm, j].ravel()
                np.testing.assert_allclose(feature[key], sum(float(x) for x in values)/64, atol=1e-12, rtol=0)
            assert feature['positive'] == sum(x > 1e-12 for x in means)
            assert feature['negative'] == sum(x < -1e-12 for x in means)
            assert feature['numerical_zero'] == sum(abs(x) <= 1e-12 for x in means)
        entry = arrays['entry'][:, :, g]
        for col, key in ((0, 'entry_mean_delta'), (1, 'entry_mean_U_rms')):
            np.testing.assert_allclose(row[key], sum(float(x) for x in entry[..., col].ravel())/64, atol=1e-12, rtol=0)
        den = sum(float(x*x) for x in entry[..., 1].ravel())
        if den:
            np.testing.assert_allclose(row['entry_relative_rms'], np.sqrt(sum(float(x*x) for x in entry[..., 0].ravel())/den), atol=1e-12, rtol=1e-12)
        else:
            assert row['entry_relative_rms'] is None
        route = arrays['routing'][:, :, g].reshape(64, 2, 3)
        assert row['route'] == dict(family_switch=sum(int(r[0, 0] != r[1, 0]) for r in route),
            shift_switch=sum(int(list(r[0, 1:]) != list(r[1, 1:])) for r in route),
            U_tie=sum(int(r[0, 0] == -1) for r in route), P_tie=sum(int(r[1, 0] == -1) for r in route),
            U_correct=sum(int(r[0, 0] == g//2) for r in route), P_correct=sum(int(r[1, 0] == g//2) for r in route))
        assert sum(r['n'] for r in row['geometry']) == 64
        for r in row['geometry']:
            mask = arrays['q'][:, :, g, 2] == r['delta_q']
            assert r['n'] == int(mask.sum()) and r['founders'] == int(mask.any(1).sum())
            assert r['founder_counts'] == mask.sum(1).tolist()
            selected = [(b, l) for b in range(16) for l in range(4) if mask[b, l]]
            if not selected:
                assert r['means'] is None
            else:
                values = [[arrays['distance'][b, l, g, 18, 0], arrays['distance'][b, l, g, 26, 0],
                    arrays['endpoint'][b, l, g, 1, 0]-arrays['endpoint'][b, l, g, 0, 0],
                    arrays['endpoint'][b, l, g, 1, 4]-arrays['endpoint'][b, l, g, 0, 4]] for b, l in selected]
                np.testing.assert_allclose(r['means'], [sum(x[j] for x in values)/len(values) for j in range(4)], atol=1e-12, rtol=0)
    return dict(passes=True, groups=4, stage_rows=144, endpoint_rows=24, geometry_rows=12)
