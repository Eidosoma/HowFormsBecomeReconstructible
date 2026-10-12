"""D175 saved-field measurements only. No IO, dynamics, fitting or outcomes."""
import numpy as np

GROUPS = ('A_ordinary', 'A_aligned', 'B_ordinary', 'B_aligned')
IDS = tuple(range(90000, 90016))
TIMES = (0, 1, 300, 301, 400, 401, 1000)
FIELDS = ('V', 'ema', 'R', 'theta')
CHAIN = ('final_R', 'tanh_R', 'outgoing', 'routed_outgoing',
         'fresh_V:0', 'fresh_V:1', 'fresh_V:100', 'fresh_V:300')
STAGES = tuple(f'writer:{t}:{k}' for t in TIMES for k in FIELDS) + CHAIN
FEATURES = ('own_best', 'own_minus_alternative_best', 'guide_margin',
            'routed_canonical_margin', 'diagnostic_preference', 'diagnostic_V_rms')
SHAPES = dict(founder_packets=(4, 2, 2048), guide=(4, 2, 16, 16),
    input=(4, 4, 2, 2048), routed=(4, 4, 2, 2048), outgoing=(4, 4, 2, 2048),
    terminal_packet=(4, 4, 2, 2048), read_states=(4, 4, 2, 5, 3, 16, 16),
    write_states=(4, 4, 2, 7, 4, 16, 16), terminal_states=(4, 4, 2, 4, 3, 16, 16),
    scores=(4, 4, 2, 2, 2, 16, 16), shift=(4, 4, 2, 2),
    starting_features=(4, 4, 7), diagnostic_features=(4, 4, 2, 6))
PACKETS = ('founder_packets', 'input', 'routed', 'outgoing', 'terminal_packet')


def rms(x):
    return np.sqrt(np.mean(x*x, axis=(-2, -1)))


def decode(x):
    assert x.dtype == np.uint8 and x.shape[-1] == 2048
    a = np.frombuffer(x.tobytes(), '<f8').reshape(x.shape[:-1] + (16, 16))
    assert np.isfinite(a).all()
    return a


def project(x):
    a = x - x.mean(axis=(-2, -1), keepdims=True)
    return a * (.3 / np.maximum(a.std(axis=(-2, -1), keepdims=True), 1e-9))


def targets():
    y, x = np.indices((16, 16))
    return np.stack((np.where(y < 8, 1., -1.), np.where(x % 8 < 4, 1., -1.)))


def geometry(role, shift):
    y, x = np.asarray(shift) % 16
    return 1 - min(y, 16-y)/4 if role == 0 else 1 - min(x % 8, 8-x % 8)/2


def paired(u, p):
    """Delta RMS, U RMS, P RMS, unit-centered shape distance, validity."""
    uc = u-u.mean(axis=(-2, -1), keepdims=True)
    pc = p-p.mean(axis=(-2, -1), keepdims=True)
    su, sp = rms(uc), rms(pc)
    valid = (su > 0) & (sp > 0)
    zu = uc / np.where(su > 0, su, 1)[..., None, None]
    zp = pc / np.where(sp > 0, sp, 1)[..., None, None]
    return np.stack((rms(p-u), rms(u), rms(p), np.where(valid, rms(zp-zu), 0)), -1), valid


def validate(raw):
    assert set(raw) == set(SHAPES), 'complete diagnostic-only schema'
    for key, shape in SHAPES.items():
        a = raw[key]
        dtype = np.uint8 if key in PACKETS else np.int64 if key == 'shift' else np.float64
        assert a.shape == shape and a.dtype == dtype and np.isfinite(a).all(), key
    assert np.all((raw['shift'] >= 0) & (raw['shift'] < 16))
    for key in ('input', 'routed', 'read_states', 'shift'):
        np.testing.assert_array_equal(raw[key][:, :, 0], raw[key][:, :, 1])
    np.testing.assert_array_equal(raw['write_states'][:, :, 0, :3], raw['write_states'][:, :, 1, :3])
    np.testing.assert_array_equal(raw['write_states'][:, :, :, 0, :3], raw['read_states'][:, :, :, -1])
    np.testing.assert_array_equal(raw['write_states'][:, :, :, 0, 3], 0)
    np.testing.assert_array_equal(raw['terminal_states'][:, :, 0, 0], raw['terminal_states'][:, :, 1, 0])
    np.testing.assert_allclose(decode(raw['outgoing']), project(np.tanh(raw['write_states'][..., -1, 2, :, :])), atol=1e-12, rtol=0)


def fields(raw):
    writes = raw['write_states'].reshape(4, 4, 2, 28, 16, 16)
    r = raw['write_states'][:, :, :, -1, 2]
    chain = np.stack((r, np.tanh(r), decode(raw['outgoing']), decode(raw['terminal_packet']),
                     *(raw['terminal_states'][:, :, :, t, 0] for t in range(4))), axis=3)
    return np.concatenate((writes, chain), axis=3)


def extract(raw):
    validate(raw)
    x = fields(raw)
    distance, valid = paired(x[:, :, 0], x[:, :, 1])
    entry = np.empty((4, 4, 2)); q = np.empty((4, 4, 3))
    for life in range(4):
        for g in range(4):
            shift = raw['shift'][life, g, 0] if g % 2 == 0 else np.array([0, 0])
            theta = raw['write_states'][life, g, 0, 2, 3]
            base = np.roll(theta, tuple(shift), (0, 1))
            entry[life, g] = rms(np.roll(base, (2, 1), (0, 1))-base), rms(base)
            normal, pulse = geometry(g//2, shift), geometry(g//2, shift + (2, 1))
            q[life, g] = normal, pulse, pulse-normal
    routing = np.empty((4, 4, 2, 3), dtype=np.int64)
    for life in range(4):
        for g in range(4):
            for arm in range(2):
                scores = raw['scores'][life, g, arm, 1]
                peaks = scores.max(axis=(1, 2))
                family = -1 if abs(peaks[0]-peaks[1]) <= 1e-12 else int(np.argmax(peaks))
                shift = [0, 0] if family == -1 else np.argwhere(abs(scores[family]-peaks[family]) <= 1e-12)[0]
                routing[life, g, arm] = family, *shift
                np.testing.assert_array_equal(decode(raw['terminal_packet'][life, g, arm]),
                    np.roll(decode(raw['outgoing'][life, g, arm]), tuple(-np.asarray(shift)), (0, 1)))
    endpoint = raw['diagnostic_features'].copy()
    v = raw['terminal_states'][..., -1, 0, :, :]
    for g in range(4):
        patterns = targets()[[g//2, 1-g//2]]
        matches = np.mean(((v[:, g, :, None] > 0) == (patterns > 0)) &
                          (abs(v[:, g, :, None]) > .2), axis=(-2, -1))
        np.testing.assert_array_equal(endpoint[:, g, :, 4], matches[..., 0]-matches[..., 1])
    np.testing.assert_allclose(endpoint[..., 5], rms(v), rtol=0, atol=1e-12)
    return dict(distance=distance, shape_valid=valid, entry=entry, q=q, endpoint=endpoint, routing=routing)


def ratio(a, b):
    return float(a/b) if b != 0 else None


def summary(a):
    assert set(a) == {'distance', 'shape_valid', 'entry', 'q', 'endpoint', 'routing'}
    assert a['distance'].shape == (16, 4, 4, len(STAGES), 4)
    assert a['shape_valid'].shape == (16, 4, 4, len(STAGES))
    groups = []
    for g, group in enumerate(GROUPS):
        d, valid = a['distance'][:, :, g], a['shape_valid'][:, :, g]
        stages = []
        for s, stage in enumerate(STAGES):
            v, x = valid[..., s], d[..., s, :]
            stages.append(dict(stage=stage, n=64, mean_delta=float(x[..., 0].mean()),
                rms_delta=float(np.sqrt(np.mean(x[..., 0]**2))), mean_U_rms=float(x[..., 1].mean()),
                mean_P_rms=float(x[..., 2].mean()), shape_distance=float(x[..., 3][v].mean()) if v.any() else None,
                shape_valid=int(v.sum()), shape_invalid=int((~v).sum()),
                founders=[dict(id=ID, mean_delta=float(x[b, :, 0].mean()),
                    rms_delta=float(np.sqrt(np.mean(x[b, :, 0]**2))),
                    shape_distance=float(x[b, :, 3][v[b]].mean()) if v[b].any() else None,
                    shape_valid=int(v[b].sum())) for b, ID in enumerate(IDS)]))
        recovery = []
        for field in FIELDS:
            i, j = (STAGES.index(f'writer:{t}:{field}') for t in (400, 1000))
            start, end = d[..., i, 0], d[..., j, 0]
            recovery.append(dict(field=field, rms_ratio=ratio(np.linalg.norm(end), np.linalg.norm(start)),
                smaller=int((end < start).sum()), equal=int((end == start).sum()), larger=int((end > start).sum()),
                zero_denominators=int((start == 0).sum()),
                founders=[dict(id=ID, rms_ratio=ratio(np.linalg.norm(end[b]), np.linalg.norm(start[b])))
                          for b, ID in enumerate(IDS)]))
        endpoint = []
        for j, feature in enumerate(FEATURES):
            u, p = a['endpoint'][:, :, g, 0, j], a['endpoint'][:, :, g, 1, j]
            delta = p-u; bmean = delta.mean(1)
            endpoint.append(dict(feature=feature, mean_U=float(u.mean()), mean_P=float(p.mean()),
                mean_delta=float(delta.mean()), mean_absolute_delta=float(abs(delta).mean()),
                positive=int((bmean > 1e-12).sum()), negative=int((bmean < -1e-12).sum()),
                numerical_zero=int((abs(bmean) <= 1e-12).sum()), founder_deltas=bmean.tolist()))
        route = a['routing'][:, :, g]
        geometry_rows = []
        for level in (-.5, 0., .5):
            mask = a['q'][:, :, g, 2] == level
            values = np.stack((d[..., STAGES.index('writer:400:R'), 0],
                d[..., STAGES.index('writer:1000:R'), 0],
                a['endpoint'][:, :, g, 1, 0]-a['endpoint'][:, :, g, 0, 0],
                a['endpoint'][:, :, g, 1, 4]-a['endpoint'][:, :, g, 0, 4]), -1)
            geometry_rows.append(dict(delta_q=level, n=int(mask.sum()), founders=int(mask.any(1).sum()),
                means=values[mask].mean(0).tolist() if mask.any() else None,
                founder_counts=mask.sum(1).tolist()))
        entry = a['entry'][:, :, g]
        groups.append(dict(group=group, stages=stages, recovery=recovery, endpoint=endpoint,
            entry_mean_delta=float(entry[..., 0].mean()), entry_mean_U_rms=float(entry[..., 1].mean()),
            entry_relative_rms=ratio(np.linalg.norm(entry[..., 0]), np.linalg.norm(entry[..., 1])),
            route=dict(family_switch=int((route[..., 0, 0] != route[..., 1, 0]).sum()),
                shift_switch=int(np.any(route[..., 0, 1:] != route[..., 1, 1:], axis=-1).sum()),
                U_tie=int((route[..., 0, 0] == -1).sum()), P_tie=int((route[..., 1, 0] == -1).sum()),
                U_correct=int((route[..., 0, 0] == g//2).sum()), P_correct=int((route[..., 1, 0] == g//2).sum())),
            geometry=geometry_rows))
    return dict(blocks=list(IDS), cases=256, diagnostic_pairs=256, groups=groups,
        actual_lineage_outcomes_loaded=False, new_fits=0, new_dynamics=0, prospective_evidence=False)
