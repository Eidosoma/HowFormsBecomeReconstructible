"""Saved-evidence closeout written after inspecting the completed TT021 results.

Use the frozen, qualified scorer. Generate no dynamics and no new test records.
Preserve the original storage failure and verify the exact 62+2 partition.
"""
from dataclasses import asdict
from datetime import datetime
import math
from pathlib import Path
import statistics
import time
import traceback

from scipy.special import stdtrit

import analysis
import common as c
import continue_after_storage as continuation
import design
import execute
import run


def exact_files(directory, hashes, completed=True):
    actual = {str(p) for p in continuation.own_files(directory)
              if not (completed and p == directory/'COMPLETE.json')}
    assert actual == set(hashes), f'changed file inventory: {directory}'
    c.verify(hashes)


def independent_claims(directory, registration, summary):
    """Recalculate registered contrasts directly from the checked record rows."""
    data = {i: c.read_json(directory/f'tissue_{i}/records.json') for i in c.BLOCKS}
    result = {}
    for name, claim in registration['claims'].items():
        values = []
        differences = []
        for index in c.BLOCKS:
            left, right = (data[index][claim[k]] for k in ('left', 'right'))
            assert len(left) == len(right) == 16
            identities = lambda rows: [(r['world'], r['message'], r['replicate']) for r in rows]
            assert identities(left) == identities(right)
            assert len(set(identities(left))) == 16
            assert {(r['message'], r['replicate']) for r in left} == {
                (m, r) for m in range(4) for r in range(4)}
            delta = [a['accuracy']-b['accuracy'] for a, b in zip(left, right)]
            assert all(math.isfinite(x) and -1 <= x <= 1 for x in delta)
            values.append(statistics.mean(delta))
            differences.extend(delta)
        n = len(values)
        mean = statistics.mean(values)
        se = statistics.stdev(values)/math.sqrt(n)
        alpha = registration['per_claim_alpha']
        bounded_radius = math.sqrt(2*math.log(1/alpha)/n)
        radius = float(stdtrit(n-1, 1-alpha))*se if se else bounded_radius
        r95 = float(stdtrit(n-1, .975))*se if se else math.sqrt(2*math.log(40)/n)
        clip = lambda value: max(-1., min(1., value))
        lower = clip(mean-radius)
        classification = 'PRACTICAL_SUPERIORITY_PASS' if lower > claim['margin'] else 'NOT_CONFIRMED'
        changes = dict(improved=sum(x > 0 for x in differences),
                       worsened=sum(x < 0 for x in differences),
                       tied=sum(x == 0 for x in differences))
        saved = summary['contrasts'][name]
        assert saved['left'] == claim['left'] and saved['right'] == claim['right']
        assert saved['margin'] == claim['margin'] and saved['classification'] == classification
        assert saved['record_changes'] == changes
        assert n == saved['interval']['n'] == 64
        assert saved['interval']['alpha'] == alpha == .01
        close = lambda a, b: math.isclose(a, b, abs_tol=2e-14, rel_tol=0.)
        assert all(close(saved['blocks'][str(i)], v) for i, v in zip(c.BLOCKS, values))
        for key, value in (('mean', mean), ('standard_error', se),
                           ('lower_one_sided', lower), ('upper_one_sided', clip(mean+radius)),
                           ('hoeffding_lower_sensitivity', clip(mean-bounded_radius))):
            assert close(saved['interval'][key], value), (name, key)
        assert close(saved['mean'], mean)
        assert all(close(a, b) for a, b in zip(saved['interval']['pointwise_two_sided_95'],
                                             [clip(mean-r95), clip(mean+r95)]))
        result[name] = dict(mean=mean, lower_one_sided=lower, margin=claim['margin'],
                            classification=classification, record_changes=changes)
    assert len(result) == 5 and registration['family_alpha'] == .05
    return result


def main():
    tick = time.monotonic()
    destination = c.ROOT/'checks/closeout_v1'
    destination.mkdir(parents=True, exist_ok=False)
    verifier_sha = c.sha(__file__)
    c.write_json(destination/'STARTED.json', dict(started_utc=c.now(),
        verifier_sha256=verifier_sha, written_after_outcome_inspection=True,
        new_trajectories=0))
    try:
        old, directory = continuation.OLD, continuation.NEW
        complete = c.read_json(directory/'COMPLETE.json')
        registration = c.read_json(c.ROOT/'REGISTRATION.json')
        amendment = c.read_json(c.ROOT/'CONTINUATION_REGISTRATION.json')
        carry = c.read_json(c.ROOT/'CONTINUATION_CARRY.json')
        launch = c.read_json(c.ROOT/'CONTINUATION_LAUNCH.json')
        running = c.read_json(directory/'RUNNING.json')
        old_running = c.read_json(old/'RUNNING.json')
        failure = c.read_json(old/'FAILED.json')
        assert complete['status'] == 'COMPLETE' and not (directory/'FAILED.json').exists()
        assert failure['error'] == "AssertionError('storage reserve')"
        assert not (old/'COMPLETE.json').exists()
        assert complete['original_failure_preserved'] and complete['execution_amendment']
        assert complete['registration_sha256'] == amendment['original_registration_sha256'] == c.sha(c.ROOT/'REGISTRATION.json')
        assert old_running['registration_sha256'] == complete['registration_sha256']
        assert complete['continuation_registration_sha256'] == running['registration_sha256'] == launch['registration_sha256'] == c.sha(c.ROOT/'CONTINUATION_REGISTRATION.json')
        assert launch['status'] == 'DETACHED_STARTED' and launch['pid'] == running['pid']
        assert complete['inputs'] == amendment['inputs'] == continuation.inputs()
        assert registration['inputs'] == old_running['inputs'] == c.runtime_hashes()
        assert all(amendment['inputs'][p] == digest for p, digest in registration['inputs'].items())
        assert complete['environment'] == amendment['environment'] == registration['environment'] == execute.environment()
        assert c.serialized(asdict(c.model.CONFIG)) == c.serialized(registration['config'])
        assert c.serialized(asdict(c.model.READOUT)) == c.serialized(registration['readout'])
        assert {k: asdict(v) for k, v in design.plan().items()} == registration['plan']
        assert design.claims() == registration['claims']
        c.verify(registration['evidence']); c.verify(amendment['evidence'])
        assert datetime.fromisoformat(registration['registered_utc']) < datetime.fromisoformat(old_running['started_utc'])
        assert datetime.fromisoformat(amendment['registered_utc']) < datetime.fromisoformat(running['started_utc'])
        assert datetime.fromisoformat(complete['completed_utc']) < datetime.fromisoformat(amendment['original_deadline_utc'])
        assert complete['seconds'] < running['deadline_seconds'] <= amendment['deadline_seconds']
        assert complete['workers'] == running['workers'] == amendment['workers'] == 2
        assert complete['numerical_threads'] == running['numerical_threads'] == 1
        assert running['cpus'] == amendment['cpus'] == registration['cpus']

        carried = c.BLOCKS[:-2]
        new = continuation.MISSING
        assert complete['blocks'] == registration['blocks'] == list(c.BLOCKS)
        assert complete['carried_blocks'] == len(carried) == 62
        assert complete['new_blocks'] == amendment['unstarted_blocks'] == list(new)
        assert amendment['carried_blocks'] == list(carried)
        assert {int(i) for i in carry['blocks']} == set(carried)
        assert complete['carried_outputs'] == carry['hashes']
        assert {p.name for p in directory.iterdir() if p.is_symlink()} == {f'tissue_{i}' for i in carried}
        assert {p.name for p in directory.glob('tissue_*')} == {f'tissue_{i}' for i in c.BLOCKS}
        for index in carried:
            expected = old/f'tissue_{index}'
            assert (directory/f'tissue_{index}').resolve() == expected.resolve()
            assert Path(carry['blocks'][str(index)]).resolve() == expected.resolve()
        for index in new:
            assert not (directory/f'tissue_{index}').is_symlink()
            assert not (old/f'tissue_{index}').exists() and not (old/f'worker_{index}.json').exists()
        exact_files(old, complete['carried_outputs'], completed=False)
        exact_files(directory, complete['outputs'])
        source_files = c.source_check()
        prerequisites = {}
        for label, path, expected_status, bound in (
            ('qualification', c.ROOT/'checks/qualification_v1', 'PASS', registration['inputs']),
            ('benchmark', c.ROOT/'runs/benchmark_v1', 'COMPLETE', registration['inputs']),
            ('continuation_qualification', c.ROOT/'checks/continuation_v1', 'PASS', amendment['inputs']),
        ):
            receipt = c.read_json(path/'COMPLETE.json')
            assert receipt['status'] == expected_status and receipt['inputs'] == bound
            exact_files(path, receipt['outputs'])
            prerequisites[label+'_outputs'] = len(receipt['outputs'])

        counts = {k: 0 for k in complete['verification'] if not k.startswith('max_')}
        saved_counts = {k: 0 for k in complete['saved_verification']}
        maximum = 0.
        blocks = {}
        for index in c.BLOCKS:
            block = directory/f'tissue_{index}'
            config = c.read_json(block/'CONFIG.json')
            assert config['tissue'] == index and config['baseline'] is None
            assert config['config'] == registration['config'] and config['readout'] == registration['readout']
            assert config['role'] == 'prospective confirmation'
            proof = c.read_json(block/'CHECK.json')
            assert proof['status'] == 'PASS' and proof['independent_physics'] is True
            assert proof['role'] == 'prospective confirmation' and proof['tissue'] == index
            assert proof['reused_scientific_trajectories'] == 0
            assert proof['max_native_error'] == 0. and proof['max_average_error'] <= 2e-12
            assert proof['boundary']['passes'] and proof['parent']['max_absolute_difference'] == 0.
            for item in [*proof['repairs'].values(), *proof['reads'].values()]:
                assert item['rng_match'] and item['max_native_error'] == 0.
            assert all(item['carrier_bytes_per_record'] == 2048 for item in proof['reads'].values())
            worker = c.read_json((old if index in carried else directory)/f'worker_{index}.json')
            assert worker['tissue'] == index and worker['numerical_threads'] == 1
            assert len(worker['affinity']) == 1 and worker['affinity'][0] in registration['cpus']
            preregistered = registration if index in carried else amendment
            assert datetime.fromisoformat(worker['started_utc']) > datetime.fromisoformat(preregistered['registered_utc'])
            saved = run.saved_check(block, c.model.CONFIG, c.model.READOUT)
            assert saved == c.read_json(block/'SAVED_CHECK.json')
            if index in carried: assert saved == carry['saved'][str(index)]
            for key in counts: counts[key] += proof[key]
            for key in saved_counts: saved_counts[key] += saved[key]
            maximum = max(maximum, proof['max_average_error'])
            blocks[index] = saved
        counts.update(max_native_error=0., max_average_error=maximum)
        assert counts == complete['verification'] and saved_counts == complete['saved_verification']
        summary = analysis.summary(directory)
        assert c.serialized(summary) == (directory/'SUMMARY.json').read_bytes()
        prefix = 'Execution amendment: 62 unchanged blocks carried after a storage halt; only the two unstarted blocks completed. See ../../CONTINUATION_AMENDMENT.md.\n\n'
        assert prefix+analysis.report(summary) == (directory/'REPORT.md').read_text()
        claims = independent_claims(directory, registration, c.read_json(directory/'SUMMARY.json'))
        assert complete['primary'] == summary['primary'] == claims['primary_capture_gain']['classification']
        c.verify(complete['inputs']); c.verify(amendment['evidence'])
        exact_files(old, complete['carried_outputs'], completed=False)
        exact_files(directory, complete['outputs'])
        retained = sum(Path(p).stat().st_size for p in [*complete['carried_outputs'], *complete['outputs']])
        assert retained == complete['combined_retained_bytes'] < registration['run_byte_limit']
        assert c.sha(__file__) == verifier_sha
        result = dict(status='PASS', completed_utc=c.now(), seconds=time.monotonic()-tick,
            verifier_sha256=verifier_sha, verifier_written_after_outcome_inspection=True,
            checker_sha256=c.sha(c.ROOT/'run.py'), completion_sha256=c.sha(directory/'COMPLETE.json'),
            registration_sha256=c.sha(c.ROOT/'REGISTRATION.json'),
            continuation_registration_sha256=c.sha(c.ROOT/'CONTINUATION_REGISTRATION.json'),
            original_failure_sha256=c.sha(old/'FAILED.json'),
            verified_original_inputs=len(registration['inputs']), verified_inputs=len(complete['inputs']),
            verified_continuation_outputs=len(complete['outputs']), verified_carried_outputs=len(complete['carried_outputs']),
            source_files=source_files, **prerequisites, verification=counts, saved_verification=saved_counts,
            blocks=blocks, formal_claims=claims, primary=summary['primary'],
            summary_exact=True, report_exact=True, independent_claim_calculations=True,
            carried_blocks=62, new_blocks_in_continuation=list(new), original_failure_preserved=True,
            execution_amendment_after_62_generated=True, scientific_rules_unchanged=True,
            original_runtime_to_storage_halt_seconds=(datetime.fromisoformat(failure['failed_utc'])-datetime.fromisoformat(old_running['started_utc'])).total_seconds(),
            continuation_runtime_seconds=complete['seconds'], new_trajectories=0,
            automatic_polling=False, automatic_retry=False, automatic_successor=False)
        c.write_json(destination/'COMPLETE.json', result)
        c.write_json(c.ROOT/'CLOSEOUT.json', result)
        print(c.serialized({k: v for k, v in result.items() if k not in ('blocks', 'formal_claims')}).decode(), flush=True)
    except BaseException as error:
        c.write_json(destination/'FAILED.json', dict(status='FAILED', failed_utc=c.now(),
            error=repr(error), traceback=traceback.format_exc(), automatic_retry=False))
        raise


if __name__ == '__main__':
    main()
