"""Retained-state audits of mutation, observer, freezes and renewal boundaries."""
from pathlib import Path
import json
import numpy as np
from h006 import engine as e
from h006.inference import present_summary, select_dose


def audit(out):
    out = Path(out)
    config = json.loads((out/'config.json').read_text())
    checks = []

    def check(label, value):
        checks.append(dict(label=label, passed=bool(value)))
        if not value:
            e.e.save(out/'audit.json', dict(passed=False, checks_count=len(checks), checks=checks))
            raise AssertionError(label)

    for manifest in ('freeze.json', 'selection_sha256.json', 'enrollment_sha256.json', 'raw_sha256.json'):
        if not (out/manifest).exists():
            continue
        for name, expected in json.loads((out/manifest).read_text()).items():
            check(f'{manifest} {name}', e.e.checksum(out/name) == expected)
    selection = json.loads((out/'SELECTION.json').read_text())
    decisions = present_summary(out, config['selection_seeds'], e.DOSES, 'selection', config)
    check('selection replay', decisions == selection['decisions'])
    expected_dose = 32 if config['mode'] == 'benchmark' else select_dose(decisions)
    check('fixed largest-passing dose or engineering override', expected_dose == selection['selected_dose'])
    check('selection sealed before assay observations', selection['assay_files_at_freeze'] == 0)
    check('selection sealed before futures', selection['future_files_at_freeze'] == 0)
    enrollment = json.loads((out/'ENROLLMENT.json').read_text()) if (out/'ENROLLMENT.json').exists() else None
    if expected_dose is not None:
        replay = present_summary(out, config['assay_seeds'], (expected_dose,), 'assay', config)[0]
        check('independent assay decision replay', replay == enrollment['decision'])
        check('enrollment sealed before futures', enrollment['future_files_at_freeze'] == 0)
        check('selected dose propagated without fallback', enrollment['dose'] == expected_dose)
    has_futures = expected_dose is not None and (config['mode'] == 'benchmark' or enrollment['decision']['passed'])
    expected_files = {f'future_{s}_{f:02d}.npz' for s in config['assay_seeds'] for f in range(e.FORKS)} if has_futures else set()
    check('exact future inventory and gate stop', {p.name for p in out.glob('future_*.npz')} == expected_files)
    for stage, seeds, doses in [('selection', config['selection_seeds'], e.DOSES),
                                 ('assay', config['assay_seeds'] if expected_dose is not None else [], (expected_dose,))]:
        check(stage+' exact present inventory', {p.name for p in out.glob(stage+'_*.npz')} == {f'{stage}_{s}.npz' for s in seeds})
        for seed in seeds:
            with np.load(out/f'inputs/source_{seed}.npz') as raw:
                source = {k: raw[k] for k in raw.files}
            prefix = f'{stage}/{seed} '
            check(prefix+'source writer identity', np.array_equal(source['records'], e.e.m.write_body(source['source_bodies'])))
            base, founder, _, _, _ = e.e.h001.acquire(seed, 'function')
            check(prefix+'source base/founder identity', np.array_equal(base, source['base']) and np.array_equal(founder, source['founder']))
            with np.load(out/f'{stage}_{seed}.npz') as present:
                measured = e.measure(seed, source, doses, stage)
                for name, value in measured.items():
                    check(prefix+'present replay '+name, np.array_equal(value, present[name]))
                packets = e.decode(present['packet_codes'])
                masks = present['flip_masks']
                feasible = present['feasible']
                check(prefix+'archive codebook', present['packet_codes'].dtype == np.int8 and np.isin(present['packet_codes'], [-1, 0, 1]).all())
                check(prefix+'source preserved', np.array_equal(packets[:, 0], np.broadcast_to(source['records'], packets[:, 0].shape)))
                check(prefix+'symmetric zero-diagonal packets', np.array_equal(packets, packets.swapaxes(-1, -2)) and not np.diagonal(packets, axis1=-1, axis2=-2).any())
                check(prefix+'infeasible never enrolled', not np.any(present['eligible'] & ~feasible))
                for d, dose in enumerate(doses):
                    for v, sites in ((1, np.arange(8, 24)), (2, np.arange(24, 64))):
                        allowed = np.zeros((64, 64), bool)
                        allowed[np.ix_(np.arange(4), sites)] = True
                        allowed |= allowed.T.copy()
                        mask = masks[d, v]
                        check(prefix+f'{dose}/{v} exact support and count', not np.any(mask & ~allowed) and
                              np.array_equal(mask.sum(axis=(-2, -1)), feasible*2*dose))
                        check(prefix+f'{dose}/{v} sign flips only', np.array_equal(packets[d, v], source['records']*np.where(mask, -1, 1)))
                        for value in (-1/64, 0., 1/64):
                            check(prefix+f'{dose}/{v} histogram {value}', np.array_equal(
                                (packets[d, v] == value).sum(axis=(-2, -1)), (source['records'] == value).sum(axis=(-2, -1))))
                        check(prefix+f'{dose}/{v} exact squared norm', np.array_equal(
                            np.sum(packets[d, v]**2, axis=(-2, -1)), np.sum(source['records']**2, axis=(-2, -1))))
                    check(prefix+f'{dose} cue degree matched', np.array_equal(masks[d, 1, ..., :4, :].sum(axis=-1), masks[d, 2, ..., :4, :].sum(axis=-1)))
                    check(prefix+f'{dose} cue association changed as specified', np.all(e.cue_link(packets[d, 1])[feasible] == 1-dose/32)
                          and np.all(e.cue_link(packets[d, 2])[feasible] == 1))
                    # Apply the linear gain to the exact record difference. Subtracting
                    # two separately rounded base-plus-record matrices need not be exact.
                    gained = e.e.effective_weights(np.zeros_like(source['base']),
                                                   packets[d]-packets[d, 0], 4., e.e.INPUTS)
                    check(prefix+f'{dose} gained perturbation strength matched', np.array_equal(
                        np.sum(gained[1]**2, axis=(-2, -1)), np.sum(gained[2]**2, axis=(-2, -1))))
                if stage == 'assay':
                    selected_packets = packets[0]
            if stage != 'assay' or not has_futures:
                continue
            for fork in range(e.FORKS):
                label = f'{seed}/{fork} '
                with np.load(out/f'future_{seed}_{fork:02d}.npz') as raw:
                    codes = raw['record_codes']
                    records = e.decode(codes)
                    bodies, masks = raw['bodies'], raw['damage']
                    check(label+'identity and dimensions', int(raw['seed']) == seed and int(raw['fork']) == fork and
                          records.shape == (17, 3, 7, 4, 4, 64, 64) and bodies.shape == (16, 3, 7, 4, 4, 2, 64))
                    check(label+'lossless symmetric zero-diagonal packets', codes.dtype == np.int8 and
                          np.isin(codes, [-1, 0, 1]).all() and np.array_equal(codes, codes.swapaxes(-1, -2)) and
                          not np.diagonal(codes, axis1=-1, axis2=-2).any())
                    check(label+'initial transplantation', np.array_equal(records[0], e.initial_records(selected_packets)))
                    check(label+'binary bodies and input clamps', np.isin(bodies, [-1, 1]).all() and
                          np.all(bodies[..., :4] == np.array([-1, 1])[:, None]))
                    restored = e.ARMS.index('restored')
                    for v in range(3):
                        check(label+f'restored {v} exact unchanged future', np.array_equal(codes[:, v, restored], codes[:, 0, 0]) and
                              np.array_equal(bodies[:, v, restored], bodies[:, 0, 0]))
                    protected = e.ARMS.index('protected_copy')
                    check(label+'protected packet invariant', np.array_equal(records[:, :, protected],
                          np.broadcast_to(selected_packets, records[:, :, protected].shape)))
                    for g, body in enumerate(bodies, 1):
                        expected_mask = e.e.m.mask_edges(e.e.m.rng(seed, 'h006', 'future', fork, 'damage', g), (4, 4, 64, 64), .5)
                        check(label+f'damage {g}', np.array_equal(masks[g-1], expected_mask))
                        body = body.astype(float)
                        expected = (body[..., 0, :, None]*body[..., 0, None, :] +
                                    body[..., 1, :, None]*body[..., 1, None, :])/128
                        diagonal = np.arange(64)
                        expected[..., diagonal, diagonal] = 0
                        expected[:, protected] = records[g-1, :, protected]
                        damaged = e.ARMS.index('damaged_copy')
                        expected[:, damaged] = records[g-1, :, damaged]*masks[g-1]
                        expected[:, e.ARMS.index('write_off')] = 0
                        check(label+f'independent writer/copy boundary {g}', np.array_equal(expected, records[g]))
                    # Score independently through the original H001 endpoint implementation.
                    _, body_success = e.e.h001.score(bodies, 'function', None, np.array([-1., 1.]))
                    _, reader_success = e.e.h001.score(raw['reader_states'], 'function', None, np.array([-1., 1.]))
                    check(label+'independent endpoints', np.array_equal(body_success, raw['body_success']) and np.array_equal(reader_success, raw['success']))
                    check(label+'uninterrupted endpoint', np.array_equal(np.all(body_success, axis=0) & reader_success[-1], raw['uninterrupted']))
                    check(label+'terminal reader replay', np.array_equal(e.read(records[-1], source['base'], seed, 'future', fork, 'assay', 16), raw['reader_states'][-1]))
                    incoming = records[0]*masks[0]
                    incoming[:, protected] = records[0, :, protected]
                    incoming[:, e.ARMS.index('read_off')] = 0
                    check(label+'first injured-body replay', np.array_equal(e.read(incoming, source['base'], seed, 'future', fork, 'body', 1), bodies[0]))
                del codes, records, bodies, masks
            e.e.save(out/'AUDIT_PROGRESS.json', dict(completed_seed=seed, checks_count=len(checks)))
    result = dict(passed=True, checks_count=len(checks), checks=checks)
    e.e.save(out/'audit.json', result)
    return result
