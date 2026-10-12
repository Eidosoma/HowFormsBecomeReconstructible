"""Independent construction, writer, scoring and exact replay checks."""
import json
import numpy as np
from h007 import engine as e
from h007.io import checksum, save, load_source
from h007.inference import present_summary


def audit(out):
    config = json.loads((out/'config.json').read_text())
    checks = []

    def check(label, passed):
        checks.append(dict(label=label, passed=bool(passed)))
        if not passed:
            save(out/'audit.json', dict(passed=False, checks_count=len(checks), checks=checks))
            raise AssertionError(label)

    for manifest in ('freeze.json', 'enrollment_sha256.json', 'raw_sha256.json'):
        for name, expected in json.loads((out/manifest).read_text()).items():
            check(manifest+' '+name, checksum(out/name) == expected)
    enrollment = json.loads((out/'ENROLLMENT.json').read_text())
    decisions = present_summary(out, config)
    check('all current decisions replay', decisions == enrollment['decisions'])
    check('no replacement observations at enrollment freeze', enrollment['replacement_files_at_freeze'] == 0)
    allowed = config['mode'] == 'benchmark' or any(d['passed'] for d in decisions)
    check('gate or engineering override controls transmission', allowed == enrollment['allow_replacements'])
    names = {f'replacement_{s}_{t:02d}.npz' for s in config['seeds'] for t in range(e.TRIALS)} if allowed else set()
    check('exact replacement inventory', {p.name for p in out.glob('replacement_*.npz')} == names)
    check('exact current inventory', {p.name for p in out.glob('present_*.npz')} == {f'present_{s}.npz' for s in config['seeds']})
    for seed in config['seeds']:
        prefix = f'{seed} '
        source = load_source(out, seed)
        check(prefix+'original source writer', np.array_equal(source['records'], e.e.m.write_body(source['source_bodies'])))
        base, founder, _, _, _ = e.e.h001.acquire(seed, 'function')
        check(prefix+'original base and founder', np.array_equal(base, source['base']) and np.array_equal(founder, source['founder']))
        with np.load(out/f'present_{seed}.npz') as present:
            replay = e.measure(seed, source)
            for name, value in replay.items():
                check(prefix+'current replay '+name, np.array_equal(value, present[name]))
            packets = e.decode(present['packet_codes'])
            feasible = present['feasible']
            check(prefix+'infeasible sources never matched', not np.any(present['eligible'] & ~feasible))
            for d, k in enumerate(e.DOSES):
                original, altered = packets[d]
                check(prefix+f'{k} source preserved', np.array_equal(original, source['records']))
                check(prefix+f'{k} complete visible block preserved', np.array_equal(original[..., :24, :24], altered[..., :24, :24]))
                check(prefix+f'{k} full histogram preserved', np.array_equal(np.sort(original.reshape(4, 4, -1), axis=-1), np.sort(altered.reshape(4, 4, -1), axis=-1)))
                check(prefix+f'{k} symmetric zero diagonal', np.array_equal(altered, altered.swapaxes(-1, -2)) and not np.diagonal(altered, axis1=-1, axis2=-2).any())
                check(prefix+f'{k} exact number changed', np.array_equal((original != altered).sum(axis=(-2, -1)), feasible*4*k*(64-2*k)))
                check(prefix+f'{k} exact norm preserved', np.array_equal(np.sum(original**2, axis=(-2, -1)), np.sum(altered**2, axis=(-2, -1))))
                gains = e.e.effective_weights(np.zeros((64, 64)), packets[d], 4., e.e.INPUTS)
                check(prefix+f'{k} gained record norm preserved', np.array_equal(np.sum(gains[0]**2, axis=(-2, -1)), np.sum(gains[1]**2, axis=(-2, -1))))
                bodies = present['changed_bodies'][d].astype(float)
                written = (bodies[..., 0, :, None]*bodies[..., 0, None, :] + bodies[..., 1, :, None]*bodies[..., 1, None, :])/128
                written[..., np.arange(64), np.arange(64)] = 0
                check(prefix+f'{k} independent complete writer', np.array_equal(written, altered))
                for f in range(4):
                    for r in range(4):
                        p = present['permutations'][d, f, r]
                        check(prefix+f'{k}/{f}/{r} hidden involution and conjugacy',
                              np.array_equal(p[:24], np.arange(24)) and np.array_equal(p[p], np.arange(64)) and
                              np.array_equal(altered[f, r], original[f, r][np.ix_(p, p)]))
        if allowed:
            for trial in range(e.TRIALS):
                label = f'{seed}/{trial} '
                with np.load(out/f'replacement_{seed}_{trial:02d}.npz') as raw:
                    codes = raw['record_codes']
                    records = e.decode(codes)
                    body, reader = raw['bodies'], raw['reader_states']
                    mask = raw['damage']
                    check(label+'identity and shape', int(raw['seed']) == seed and int(raw['trial']) == trial and records.shape == (2, 4, 2, 7, 4, 4, 64, 64))
                    check(label+'archive and record symmetry', codes.dtype == np.int8 and np.isin(codes, [-1, 0, 1]).all() and
                          np.array_equal(codes, codes.swapaxes(-1, -2)) and not np.diagonal(codes, axis1=-1, axis2=-2).any())
                    check(label+'input transplantation', np.array_equal(records[0], e.initial_records(packets)))
                    expected_mask = e.e.m.mask_edges(e.e.m.rng(seed, 'h007', 'replacement', trial, 'damage'), (4, 4, 64, 64), .5)
                    check(label+'paired damage', np.array_equal(mask, expected_mask))
                    check(label+'binary bodies and input clamps', np.isin(body, [-1, 1]).all() and np.all(body[..., :4] == np.array([-1, 1])[:, None]))
                    state = body.astype(float)
                    expected = (state[..., 0, :, None]*state[..., 0, None, :] + state[..., 1, :, None]*state[..., 1, None, :])/128
                    expected[..., np.arange(64), np.arange(64)] = 0
                    protected, damaged = e.ARMS.index('protected_copy'), e.ARMS.index('damaged_copy')
                    expected[:, :, protected] = records[0, :, :, protected]
                    expected[:, :, damaged] = records[0, :, :, damaged]*mask
                    expected[:, :, e.ARMS.index('write_off')] = 0
                    check(label+'independent writer and copy boundaries', np.array_equal(expected, records[1]))
                    incoming = records[0]*mask
                    incoming[:, :, protected] = records[0, :, :, protected]
                    incoming[:, :, e.ARMS.index('read_off')] = 0
                    check(label+'complete body replay', np.array_equal(e.read(incoming, source['base'], seed, 'replacement', trial, 'body'), body))
                    check(label+'complete fresh-reader replay', np.array_equal(e.read(records[1], source['base'], seed, 'replacement', trial, 'assay'), reader))
                    _, body_success = e.e.h001.score(body, 'function', None, np.array([-1., 1.]))
                    _, reader_success = e.e.h001.score(reader, 'function', None, np.array([-1., 1.]))
                    own = np.all(records[1] == packets[:, :, None], axis=(-2, -1))
                    distinct = np.any(records[1, :, 0] != records[1, :, 1], axis=(-2, -1))
                    joint = np.all(own & body_success & reader_success, axis=1) & distinct
                    check(label+'independent complete event', np.array_equal(own, raw['own_retained']) and np.array_equal(distinct, raw['distinct']) and
                          np.array_equal(body_success, raw['body_success']) and np.array_equal(reader_success, raw['reader_success']) and
                          np.array_equal(joint, raw['joint_functional_retention']))
                    for d in range(4):
                        check(label+f'{d} unchanged dose-label identity', np.array_equal(records[:, d, 0, 0], records[:, 0, 0, 0]) and
                              np.array_equal(body[d, 0, 0], body[0, 0, 0]) and np.array_equal(reader[d, 0, 0], reader[0, 0, 0]))
                        for v in range(2):
                            check(label+f'{d}/{v} exact restoration', np.array_equal(records[:, d, v, 1], records[:, d, 0, 0]) and
                                  np.array_equal(body[d, v, 1], body[d, 0, 0]) and np.array_equal(reader[d, v, 1], reader[d, 0, 0]))
                del records, codes, body, reader
        save(out/'AUDIT_PROGRESS.json', dict(completed_seed=seed, checks_count=len(checks)))
    result = dict(passed=True, checks_count=len(checks), checks=checks)
    save(out/'audit.json', result)
    return result
