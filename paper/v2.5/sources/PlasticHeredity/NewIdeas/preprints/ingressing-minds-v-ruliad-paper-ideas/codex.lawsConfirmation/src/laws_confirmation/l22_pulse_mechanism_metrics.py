"""D196 fixed offline pulse geometry, projection and reader summaries."""

import importlib.util
from pathlib import Path
import numpy as np
from . import l22_yoked_separation_metrics as old

BLOCKS, FAMILIES, ROLES, FUTURES = old.BLOCKS, old.FAMILIES, old.ROLES, old.FUTURES
TIMES, READ_TIMES, FIELDS, TOL = old.TIMES, old.READ_TIMES, old.FIELDS, old.TOL
ARMS = ('LL', 'YL', 'LL_pulse', 'YL_pulse')
CHAIN = ('body_input', 'V', 'R', 'writer_drive', 'theta')
EVENT_FIELDS = ('V', 'ema', 'R', 'theta')
PROJECT = ('V', 'R', 'writer_drive', 'theta')
PHASES = ('before', 'after', 'step')
PAIRS = {'undisturbed': ('LL', 'YL'), 'disturbed': ('LL_pulse', 'YL_pulse'),
         'own_pulse': ('LL_pulse', 'LL'), 'recorded_pulse': ('YL_pulse', 'YL')}
CONTRASTS = {
    'contingent_body_undisturbed': (1., -1., 0., 0.),
    'contingent_body_disturbed': (0., 0., 1., -1.),
    'own_disturbance': (-1., 0., 1., 0.),
    'yoked_disturbance': (0., -1., 0., 1.),
    'disturbance_interaction': (-1., 1., 1., -1.),
}
BEHAVIOR = ('accuracy', 'partner_accuracy', 'preference', 'projection_gap', 'margin', 'winner_gap')
pair, writer_drive, scores, describe = old.pair, old.writer_drive, old.scores, old.describe


def checker():
    path = Path(__file__).resolve().parents[2]/'scripts/check_l22_pulse_mechanism.py'
    spec = importlib.util.spec_from_file_location('d196_scalar', path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def specs(parents=4, draws=4):
    n, out = 4*parents, {}
    def add(k, fields, reader=False): out[k] = ((n, draws, len(fields)) if reader else (n, len(fields)), fields)
    for f in FAMILIES:
        for r in ROLES:
            for contrast in PAIRS:
                for field in CHAIN:
                    for t in TIMES: add(f'chain|{f}|{r}|{contrast}|{field}|{t}', FIELDS)
            for phase in PHASES:
                for field in EVENT_FIELDS: add(f'event_route|{f}|{r}|{phase}|{field}', FIELDS)
            for arm in ARMS[2:]:
                for jump in ('jump', 'first_response'):
                    for field in EVENT_FIELDS: add(f'event|{f}|{r}|{arm}|{jump}|{field}', FIELDS)
                for phase in PHASES:
                    for field in PROJECT: add(f'event_projection|{f}|{r}|{arm}|{phase}|{field}', ('projection_gap',))
            for arm in ARMS:
                for field in PROJECT:
                    for t in TIMES: add(f'projection|{f}|{r}|{arm}|{field}|{t}', ('projection_gap',))
            for future in FUTURES:
                for contrast in PAIRS:
                    for t in READ_TIMES: add(f'reader|{f}|{r}|{future}|{contrast}|{t}', FIELDS, True)
                for arm in ARMS:
                    add(f'behavior|{f}|{r}|{future}|{arm}', BEHAVIOR, True)
                    add(f'scores|{f}|{r}|{future}|{arm}', tuple('score_'+str(i) for i in range(4)), True)
                    add(f'probabilities|{f}|{r}|{future}|{arm}', tuple('weight_'+str(i) for i in range(4)), True)
                for contrast in CONTRASTS: add(f'contrast|{f}|{r}|{future}|{contrast}', BEHAVIOR, True)
    return out


def validate(data, parents=4, draws=4):
    expected = specs(parents, draws)
    if set(data) != set(expected): raise ValueError('complete fixed diagnostic scope required')
    for key, a in data.items():
        if a.shape != expected[key][0] or a.dtype != np.float64 or not np.isfinite(a).all():
            raise ValueError('invalid derived array '+key)


def projection(x, codes, parents):
    if x.shape != (4*parents, 16, 16) or codes.shape != (4, 16, 16): raise ValueError('projection address')
    labels = np.arange(4*parents)//parents
    return np.mean(x*(codes[labels]-codes[(labels+2) % 4]), axis=(-2, -1))[:, None]


def extract(bundle, family, parents=4, draws=4, guard=lambda: None):
    """Read arrays only. No simulator, RNG, writer update or reader is called."""
    c, scalar = checker(), old.checker()
    c.addresses(bundle, parents, draws)
    out, pairs, projections, score_rows, max_error = {}, 0, 0, 0, 0.
    def add_pair(key, a, b):
        nonlocal pairs, max_error
        value = pair(a, b); max_error = max(max_error, scalar.pair(a, b, value))
        out[key] = value; pairs += int(np.prod(a.shape[:-2])); guard()
    def add_projection(key, x):
        nonlocal projections
        value = projection(x, bundle['codes'], parents)
        c.projection(x, bundle['codes'], parents, value)
        out[key] = value; projections += x.shape[0]
    def field(raw, t, k):
        if k == 'writer_drive':
            x = writer_drive(raw[f's{t}_R']); scalar.drive(raw[f's{t}_R'], x); return x
        return raw[f's{t}_{k}']
    for role in ROLES:
        raws = bundle['raws'][role]
        for t in TIMES:
            fields = {arm: {k: field(raws[arm], t, k) for k in CHAIN} for arm in ARMS}
            for contrast, (left, right) in PAIRS.items():
                for k in CHAIN: add_pair(f'chain|{family}|{role}|{contrast}|{k}|{t}', fields[left][k], fields[right][k])
            for arm in ARMS:
                for k in PROJECT: add_projection(f'projection|{family}|{role}|{arm}|{k}|{t}', fields[arm][k])
        for phase in PHASES:
            for k in EVENT_FIELDS:
                add_pair(f'event_route|{family}|{role}|{phase}|{k}',
                    raws['LL_pulse'][f'pulse_{phase}_{k}'], raws['YL_pulse'][f'pulse_{phase}_{k}'])
        for arm in ARMS[2:]:
            raw = raws[arm]
            for jump, left, right in [('jump', 'after', 'before'), ('first_response', 'step', 'after')]:
                for k in EVENT_FIELDS:
                    add_pair(f'event|{family}|{role}|{arm}|{jump}|{k}', raw[f'pulse_{left}_{k}'], raw[f'pulse_{right}_{k}'])
            for phase in PHASES:
                for k in PROJECT:
                    value = raw[f'pulse_{phase}_R'] if k == 'writer_drive' else raw[f'pulse_{phase}_{k}']
                    if k == 'writer_drive':
                        drive = writer_drive(value); scalar.drive(value, drive); value = drive
                    add_projection(f'event_projection|{family}|{role}|{arm}|{phase}|{k}', value)
        for future in FUTURES:
            readers, behavior = bundle['readers'][role][future], {}
            for contrast, (left, right) in PAIRS.items():
                for t in READ_TIMES:
                    a, b = [readers[arm][f's{t}_V'].reshape(4*parents, draws, 16, 16) for arm in (left, right)]
                    add_pair(f'reader|{family}|{role}|{future}|{contrast}|{t}', a, b)
            for arm in ARMS:
                raw = readers[arm]; value = scores(raw['s1000_V'], bundle['codes'], parents, draws)
                scalar.scores(raw['s1000_V'], bundle['codes'], parents, draws, raw, value)
                behavior[arm] = value[2]; score_rows += 4*parents*draws
                out[f'behavior|{family}|{role}|{future}|{arm}'] = value[2]
                out[f'scores|{family}|{role}|{future}|{arm}'] = value[0].reshape(4*parents, draws, 4)
                out[f'probabilities|{family}|{role}|{future}|{arm}'] = value[1].reshape(4*parents, draws, 4)
                saved = bundle['records'][role][future][arm]
                assert len(saved) == 4*parents
                for i, row in enumerate(saved):
                    assert (row['world'], row['message'], row['replicate']) == (i, i//parents, i % parents)
                    for j, k in enumerate(BEHAVIOR[:4]): scalar.close(float(value[2][i, :, j].mean()), row[k])
            for contrast, weights in CONTRASTS.items():
                value = sum(w*behavior[a] for a, w in zip(ARMS, weights))
                c.contrast(behavior, contrast, value)
                out[f'contrast|{family}|{role}|{future}|{contrast}'] = value
    assert set(out) == {k for k in specs(parents, draws) if k.split('|')[1] == family}
    return out, dict(passes=True, field_pairs=pairs, projection_rows=projections,
        score_rows=score_rows, scalar_max_error=max_error, new_dynamics=0)


def count(x):
    def one(a):
        return dict(n=int(a.size), improved=int((a > TOL).sum()), worsened=int((a < -TOL).sum()),
            tied=int((np.abs(a) <= TOL).sum()), net=float(a.mean()),
            positive=float(np.maximum(a, 0).mean()), negative=float(np.minimum(a, 0).mean()))
    return dict(records=one(x.mean(axis=2)), draws=one(x))


def summary(blocks, parents=4, draws=4):
    if set(blocks) != set(BLOCKS): raise ValueError('four fixed histories, no pilot')
    for d in blocks.values(): validate(d, parents, draws)
    schema = specs(parents, draws); values = {}; views, transitions = {}, {}
    for key in schema:
        if key.startswith(('scores|', 'probabilities|')): continue
        values[key] = np.stack([blocks[b][key] for b in BLOCKS])
    # Average distances after extraction, never average fields before distances.
    for key in list(values):
        parts = key.split('|')
        if parts[2] != 'A': continue
        other = parts.copy(); other[2] = 'B'
        mean = parts.copy(); mean[2] = 'role_mean'
        values['|'.join(mean)] = .5*(values[key]+values['|'.join(other)])
    for key in list(values):
        parts = key.split('|')
        if parts[0] not in ('reader', 'behavior', 'contrast') or parts[3] != 'future_1': continue
        other = parts.copy(); other[3] = 'future_2'
        both = parts.copy(); both[3] = 'both'
        values['|'.join(both)] = np.concatenate((values[key], values['|'.join(other)]), axis=2)
    for key, a in values.items():
        kind = key.split('|')[0]
        fields = BEHAVIOR if kind in ('behavior', 'contrast') else (('projection_gap',) if 'projection' in kind else FIELDS)
        views[key] = describe(a.mean(axis=2) if a.ndim == 4 else a, fields, parents)
        if kind == 'contrast':
            transitions[key] = {f: count(a[..., j]) for j, f in enumerate(BEHAVIOR[:3])}
    changed = []
    for b in BLOCKS:
        data = blocks[b]
        for family in FAMILIES:
            for role in ROLES:
                for future in FUTURES:
                    prefix = f'{family}|{role}|{future}'
                    for i in range(4*parents):
                        for d in range(draws):
                            cs = {c: data[f'contrast|{prefix}|{c}'][i, d] for c in CONTRASTS}
                            if not any(np.any(np.abs(a[:3]) > TOL) for a in cs.values()): continue
                            changed.append(dict(block=b, family=family, role=role, future=future, record=i,
                                message=i//parents, replicate=i % parents, draw=d,
                                contrasts={c: dict(zip(BEHAVIOR, a.tolist())) for c, a in cs.items()},
                                cells={arm: dict(behavior=dict(zip(BEHAVIOR, data[f'behavior|{prefix}|{arm}'][i, d].tolist())),
                                    scores=data[f'scores|{prefix}|{arm}'][i, d].tolist(),
                                    probabilities=data[f'probabilities|{prefix}|{arm}'][i, d].tolist()) for arm in ARMS}))
    return dict(schema='d196_pulse_mechanism_v1', blocks=list(BLOCKS), records=16*parents,
        families=list(FAMILIES), roles=list(ROLES), futures=list(FUTURES), arms=list(ARMS),
        repair_times=list(TIMES), reader_times=list(READ_TIMES), pair_fields=list(FIELDS),
        behavior_fields=list(BEHAVIOR), contrasts={k:list(v) for k,v in CONTRASTS.items()},
        views=views, transitions=transitions, changed_draws=changed,
        retrospective=True, terminal_outcomes_previously_exposed=True, confirmatory=False,
        new_dynamics=0, fitted_models=0, benchmark_excluded=True, automatic_successor=False)
