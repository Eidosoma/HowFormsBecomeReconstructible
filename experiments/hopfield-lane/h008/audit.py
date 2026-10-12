"""Replay all probes and lineages; independently check inherited boundaries."""
import json
import numpy as np
from h008 import engine as e
from h008.inference import present_summary
from h007.io import checksum, save, load_source


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
    current = present_summary(out, config)
    check('current decision replay', current == enrollment['decision'])
    check('no future observations at enrollment seal', enrollment['future_files_at_freeze'] == 0)
    allowed = config['mode'] == 'benchmark' or current['passed']
    check('gate or engineering override controls futures', allowed == enrollment['allow_futures'])
    expected = {f'future_{s}_{f:02d}.npz' for s in config['seeds'] for f in range(e.FORKS)} if allowed else set()
    check('exact future inventory', {p.name for p in out.glob('future_*.npz')} == expected)
    check('exact validation inventory', {p.name for p in out.glob('present_*.npz')} == {f'present_{s}.npz' for s in config['seeds']})
    upstream = json.loads((out/'upstream_enrollment.json').read_text())
    prior = next(d for d in upstream['decisions'] if d['dose'] == e.DOSE)
    prior_rows = {row['seed']: row for row in prior['blocks']}
    for seed in config['seeds']:
        prefix = f'{seed} '
        source, candidate = load_source(out, seed), e.load_candidate(out, seed)
        packets = e.decode(candidate['packet_codes'])
        original, altered = packets
        rebuilt = e.selected.construct(seed, source)
        index = e.selected.DOSES.index(e.DOSE)
        check(prefix+'source writer', np.array_equal(source['records'], e.model.m.write_body(source['source_bodies'])))
        base, founder, _, _, _ = e.model.h001.acquire(seed, 'function')
        check(prefix+'source base and founder', np.array_equal(base, source['base']) and np.array_equal(founder, source['founder']))
        check(prefix+'H007 candidate construction', np.array_equal(packets, rebuilt['packets'][index]) and
              np.array_equal(candidate['permutations'], rebuilt['permutations'][index]) and
              np.array_equal(candidate['changed_bodies'], rebuilt['changed_bodies'][index]) and
              np.array_equal(candidate['feasible'], rebuilt['feasible']))
        check(prefix+'fixed H007 membership', np.array_equal(candidate['eligible'], prior_rows[seed]['eligible']) and
              not np.any(candidate['eligible'] & ~candidate['feasible']))
        check(prefix+'input archive codebook', candidate['packet_codes'].dtype == np.int8 and np.isin(candidate['packet_codes'], [-1, 0, 1]).all())
        check(prefix+'visible block and histogram unchanged', np.array_equal(original[..., :24, :24], altered[..., :24, :24]) and
              np.array_equal(np.sort(original.reshape(4, 4, -1), axis=-1), np.sort(altered.reshape(4, 4, -1), axis=-1)))
        gained = e.model.effective_weights(np.zeros((64, 64)), packets, 4., e.model.INPUTS)
        check(prefix+'gained record norm unchanged', np.array_equal(np.sum(gained[0]**2, axis=(-2, -1)), np.sum(gained[1]**2, axis=(-2, -1))))
        body = candidate['changed_bodies'].astype(float)
        written = (body[..., 0, :, None]*body[..., 0, None, :] + body[..., 1, :, None]*body[..., 1, None, :])/128
        written[..., np.arange(64), np.arange(64)] = 0
        check(prefix+'independent altered source writer', np.array_equal(written, altered))
        for f in range(4):
            for r in range(4):
                p = candidate['permutations'][f, r]
                check(prefix+f'{f}/{r} hidden involution and conjugacy', np.array_equal(p[:24], np.arange(24)) and
                      np.array_equal(p[p], np.arange(64)) and np.array_equal(altered[f, r], original[f, r][np.ix_(p, p)]))
        with np.load(out/f'present_{seed}.npz') as present:
            measured = e.measure(seed, source, candidate)
            for name, value in measured.items():
                check(prefix+'current replay '+name, np.array_equal(value, present[name]))
            check(prefix+'validation did not change membership', np.array_equal(present['eligible'], candidate['eligible']))
            _, current_success = e.model.h001.score(present['validation_states'], 'function', None, np.array([-1., 1.]))
            check(prefix+'independent current scoring', np.array_equal(current_success, present['validation_success']))
        if allowed:
            for fork in range(e.FORKS):
                label = f'{seed}/{fork} '
                with np.load(out/f'future_{seed}_{fork:02d}.npz') as raw:
                    codes = raw['record_codes']
                    bodies, masks, readers = raw['bodies'], raw['damage'], raw['reader_states']
                    check(label+'identity and dimensions', int(raw['seed']) == seed and int(raw['fork']) == fork and
                          codes.shape == (17, 2, 7, 4, 4, 64, 64) and bodies.shape == (16, 2, 7, 4, 4, 2, 64) and
                          readers.shape == (4, 2, 7, 4, 4, 2, 64) and np.array_equal(raw['checkpoints'], e.CHECKPOINTS) and
                          np.array_equal(raw['variants'], e.VARIANTS) and np.array_equal(raw['arms'], e.ARMS))
                    check(label+'symmetric zero-diagonal archive', codes.dtype == np.int8 and np.isin(codes, [-1, 0, 1]).all() and
                          np.array_equal(codes, codes.swapaxes(-1, -2)) and not np.diagonal(codes, axis1=-1, axis2=-2).any())
                    check(label+'initial transplantation', np.array_equal(e.decode(codes[0]), e.initial_records(packets)))
                    check(label+'binary body and reader clamps', np.isin(bodies, [-1, 1]).all() and np.isin(readers, [-1, 1]).all() and
                          np.all(bodies[..., :4] == np.array([-1, 1])[:, None]) and np.all(readers[..., :4] == np.array([-1, 1])[:, None]))
                    for v in range(2):
                        check(label+f'{v} complete restoration identity', np.array_equal(codes[:, v, 1], codes[:, 0, 0]) and
                              np.array_equal(bodies[:, v, 1], bodies[:, 0, 0]) and np.array_equal(readers[:, v, 1], readers[:, 0, 0]))
                    check(label+'protected packet invariant', np.array_equal(codes[:, :, 3],
                          np.broadcast_to(candidate['packet_codes'], codes[:, :, 3].shape)))
                    for g, body in enumerate(bodies, 1):
                        expected_mask = e.model.m.mask_edges(e.model.m.rng(seed, 'h008', 'future', fork, 'damage', g), (4, 4, 64, 64), .5)
                        check(label+f'{g} paired damage', np.array_equal(masks[g-1], expected_mask))
                        previous, outgoing = e.decode(codes[g-1]), e.decode(codes[g])
                        state = body.astype(float)
                        written = (state[..., 0, :, None]*state[..., 0, None, :] + state[..., 1, :, None]*state[..., 1, None, :])/128
                        written[..., np.arange(64), np.arange(64)] = 0
                        written[:, 3] = previous[:, 3]
                        written[:, 4] = previous[:, 4]*masks[g-1]
                        written[:, 6] = 0
                        check(label+f'{g} independent writer/copy boundary', np.array_equal(written, outgoing))
                        incoming = previous*masks[g-1]
                        incoming[:, 3] = previous[:, 3]
                        incoming[:, 5] = 0
                        check(label+f'{g} complete body replay', np.array_equal(e.read(incoming, source['base'], seed, 'future', fork, 'body', g), body))
                        if g in e.CHECKPOINTS:
                            k = e.CHECKPOINTS.index(g)
                            check(label+f'{g} complete reader replay', np.array_equal(e.read(outgoing, source['base'], seed, 'future', fork, 'assay', g), readers[k]))
                    _, body_success = e.model.h001.score(bodies, 'function', None, np.array([-1., 1.]))
                    _, reader_success = e.model.h001.score(readers, 'function', None, np.array([-1., 1.]))
                    check(label+'independent functional endpoints', np.array_equal(body_success, raw['body_success']) and
                          np.array_equal(reader_success, raw['success']))
                    check(label+'uninterrupted endpoint', np.array_equal(body_success.all(axis=0) & reader_success[-1], raw['uninterrupted']))
                    own = np.all(codes == candidate['packet_codes'][:, None], axis=(-2, -1))
                    distinct = np.any(codes[:, 0] != codes[:, 1], axis=(-2, -1))
                    at = np.array(e.CHECKPOINTS)
                    joint = (own[at] & body_success[at-1] & reader_success).all(axis=1) & distinct[at]
                    check(label+'independent exact record diagnostics', np.array_equal(own, raw['own_retained']) and
                          np.array_equal(distinct, raw['distinct']) and np.array_equal(joint, raw['joint_functional_retention']))
                    # Equal paired records cannot later diverge under shared future tapes.
                    check(label+'paired equality is absorbing', not np.any((~distinct[:-1]) & distinct[1:]))
                del codes, bodies, masks, readers
        save(out/'AUDIT_PROGRESS.json', dict(completed_seed=seed, checks_count=len(checks)))
    result = dict(passed=True, checks_count=len(checks), checks=checks)
    save(out/'audit.json', result)
    return result
