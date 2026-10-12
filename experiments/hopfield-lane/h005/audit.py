"""Retained-source, matching, transition and endpoint audits for H005."""
from pathlib import Path
import json
import numpy as np
from h005 import engine as e


def audit(out):
    out = Path(out)
    config = json.loads((out / 'config.json').read_text())
    checks = []

    def check(label, value):
        checks.append(dict(label=label, passed=bool(value)))
        if not value:
            e.e.save(out / 'audit.json', dict(passed=False, checks_count=len(checks), checks=checks))
            raise AssertionError(label)

    for manifest in ['freeze.json', 'enrollment_sha256.json', 'raw_sha256.json']:
        for name, expected in json.loads((out / manifest).read_text()).items():
            check(f'{manifest} {name}', e.e.checksum(out / name) == expected)
    enrollment = json.loads((out / 'ENROLLMENT.json').read_text())
    expected_names = {f'future_{seed}_{fork:02d}.npz' for seed in config['seeds'] for fork in range(e.FORKS)}
    check('exact future block/fork inventory', {p.name for p in out.glob('future_*.npz')} == expected_names)
    check('every original candidate retained', enrollment['candidate_pairs'] == len(config['seeds']) * 16)
    for seed in config['seeds']:
        with np.load(out / f'inputs/source_{seed}.npz') as data:
            source = {key: data[key] for key in data.files}
        check(f'{seed} supplied G16 packet writer identity',
              np.array_equal(source['records'], e.e.m.write_body(source['source_bodies'])))
        base, founder, initial, cues, stable = e.e.h001.acquire(seed, 'function')
        check(f'{seed} original base and founder identity',
              np.array_equal(base, source['base']) and np.array_equal(founder, source['founder']))
        with np.load(out / f'present_{seed}.npz') as present:
            measured = e.measure(seed, source)
            for name in measured:
                check(f'{seed} present replay {name}', np.array_equal(measured[name], present[name]))
            eligible = e.match(present['screen_signals'])
            check(f'{seed} frozen eligibility', eligible.tolist() == enrollment['blocks'][str(seed)]['eligible'])
            check(f'{seed} exact matched screen signals',
                  np.array_equal(present['screen_signals'][:, 0][:, eligible],
                                 present['screen_signals'][:, 1][:, eligible]))
        for fork in range(e.FORKS):
            prefix = f'{seed}/{fork} '
            with np.load(out / f'future_{seed}_{fork:02d}.npz') as raw:
                codes = raw['record_codes']; records = e.decode(codes)
                bodies = raw['bodies']; masks = raw['damage']
                check(prefix+'identity', int(raw['seed']) == seed and int(raw['fork']) == fork)
                check(prefix+'dimensions', records.shape == (17, 2, 7, 4, 4, 64, 64)
                      and bodies.shape == (16, 2, 7, 4, 4, 2, 64))
                check(prefix+'lossless codebook', codes.dtype == np.int8 and np.isin(codes, [-1, 0, 1]).all())
                check(prefix+'symmetric zero-diagonal records', np.array_equal(codes, codes.swapaxes(-1, -2))
                      and not np.diagonal(codes, axis1=-1, axis2=-2).any())
                check(prefix+'initial packet transplantation', np.array_equal(records[0], e.initial_records(source)))
                check(prefix+'binary bodies', np.isin(bodies, [-1, 1]).all())
                check(prefix+'only input cue values fixed', np.all(bodies[..., :4] == np.array([-1, 1])[:, None]))
                eq = e.ARMS.index('equalized')
                check(prefix+'equalized histories exact throughout',
                      np.array_equal(codes[:, 0, eq], codes[:, 1, eq]) and
                      np.array_equal(bodies[:, 0, eq], bodies[:, 1, eq]))
                protected = e.ARMS.index('protected_copy')
                check(prefix+'protected packet invariant', np.array_equal(records[:, :, protected],
                      np.broadcast_to(source['records'], records[:, :, protected].shape)))
                for g, state in enumerate(bodies, 1):
                    expected_mask = e.e.m.mask_edges(e.e.m.rng(seed, 'h005', 'future', fork, 'damage', g),
                                                    (4, 4, 64, 64), .5)
                    check(prefix+f'damage {g}', np.array_equal(masks[g-1], expected_mask))
                    # Scalar products of the two retained binary trials; no call to the writer.
                    state = state.astype(float)
                    expected = (state[..., 0, :, None]*state[..., 0, None, :] +
                                state[..., 1, :, None]*state[..., 1, None, :])/128
                    diagonal = np.arange(64); expected[..., diagonal, diagonal] = 0
                    expected[:, protected] = records[g-1, :, protected]
                    damaged = e.ARMS.index('damaged_copy')
                    expected[:, damaged] = records[g-1, :, damaged] * masks[g-1]
                    expected[:, e.ARMS.index('write_off')] = 0
                    check(prefix+f'independent writer/copy boundary {g}', np.array_equal(expected, records[g]))
                check(prefix+'checkpoint endpoints', np.array_equal(e.success(raw['reader_states']), raw['success']))
                check(prefix+'body endpoints', np.array_equal(e.success(bodies), raw['body_success']))
                check(prefix+'uninterrupted endpoint', np.array_equal(
                      np.all(e.success(bodies), axis=0) & raw['success'][-1], raw['uninterrupted']))
                replay = e.read(records[-1], source['base'], seed, 'future', fork, 'assay', 16)
                check(prefix+'terminal reader replay', np.array_equal(replay, raw['reader_states'][-1]))
                # Replay an injured boundary to check reader blocks and time-tape placement.
                incoming = records[0] * masks[0]
                incoming[:, protected] = records[0, :, protected]
                incoming[:, e.ARMS.index('read_off')] = 0
                first = e.read(incoming, source['base'], seed, 'future', fork, 'body', 1)
                check(prefix+'first injured-body replay', np.array_equal(first, bodies[0]))
            del records, codes, bodies, masks
        e.e.save(out / 'AUDIT_PROGRESS.json', dict(completed_seed=seed, checks_count=len(checks)))
    result = dict(passed=True, checks_count=len(checks), checks=checks)
    e.e.save(out / 'audit.json', result)
    return result
