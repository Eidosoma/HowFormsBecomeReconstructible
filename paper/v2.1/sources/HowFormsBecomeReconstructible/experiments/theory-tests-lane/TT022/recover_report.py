"""Post-acquisition report recovery using only the frozen TT022 saved evidence.

Written after the report-order failure, before inspecting scientific effects.
No original run file, frozen input, outcome, or scientific rule is changed.
"""
from collections import Counter
from dataclasses import asdict
from datetime import datetime
import hashlib
import json
from pathlib import Path
import shutil
import time
import traceback

import analysis
import common as c
import design
import execute
import run


ORIGINAL = c.ROOT/'runs/serial_v1'
DESTINATION = c.ROOT/'checks/report_recovery_v1'


def files(directory):
    paths = sorted(directory.rglob('*'))
    assert not any(p.is_symlink() for p in paths)
    return {str(p): c.sha(p) for p in paths if p.is_file()}


def prerequisite(directory, status, inputs):
    receipt = c.read_json(directory/'COMPLETE.json')
    assert receipt['status'] == status and receipt['inputs'] == inputs
    expected = dict(receipt['outputs'])
    expected[str(directory/'COMPLETE.json')] = c.sha(directory/'COMPLETE.json')
    assert files(directory) == expected
    return len(receipt['outputs'])


def checked_block_receipts(directory):
    """Bind acquisition replay receipts and pairing checks to verified arrays."""
    cfg, rcfg = design.configs('development')
    config = c.read_json(directory/'CONFIG.json')
    assert config['role'] == 'development'
    assert config['families'] == list(design.FAMILIES)
    assert config['policies'] == list(design.POLICIES)
    proofs = []
    distinct_births = set()
    for future in range(design.FUTURES):
        paired_environment = None
        for family in design.FAMILIES:
            for policy in design.POLICIES:
                path = directory/f'future_{future:02d}'/family/policy
                proof = c.read_json(path/'CHECK.json')
                env, native, average_error = [], 0, 0.
                for generation in range(1, design.GENERATIONS+1):
                    meta = c.read_json(path/f'g{generation:02d}.json')
                    for key, n in (('read_proof', len(rcfg.times)), ('repair_proof', len(cfg.times))):
                        item = meta[key]
                        assert item['native_arrays'] == 4*n and item['rng_match']
                        assert item['max_native_error'] == 0.
                        native += item['native_arrays']
                    assert meta['read_proof']['carrier_bytes_per_record'] == 2048
                    average_error = max(average_error, meta['repair_proof']['max_average_error'])
                    env.append(dict(birth_sha256=meta['arrays']['develop']['s0_V']['sha256'],
                        mask_sha256=meta['arrays']['boundary']['fresh']['sha256'],
                        read_rng=meta['read']['rng_final'], birth_rng=meta['read']['birth_rng_final'],
                        fission_rng=meta['injury']['rng_final'], repair_rng=meta['repair']['rng_final']))
                terminal = c.read_json(path/'terminal.json')
                assert terminal['proof']['native_arrays'] == 4*len(rcfg.times)
                assert terminal['proof']['max_native_error'] == 0. and terminal['proof']['rng_match']
                assert terminal['proof']['carrier_bytes_per_record'] == 2048
                native += terminal['proof']['native_arrays']
                assert proof['environment'] == env
                assert proof['terminal_birth_sha256'] == terminal['arrays']['s0_V']['sha256']
                assert proof['terminal_rng'] == terminal['metadata']['rng_final']
                assert proof['native_arrays'] == native
                assert proof['max_average_error'] == average_error <= 2e-12
                assert proof['scoring_only_labels'] and proof['finite_record_bytes'] == 2048
                assert proof['actual_record_writes'] == (0 if policy in ('capture_once', 'unchanged') else design.GENERATIONS*cfg.sweeps)
                assert proof['unused_native_sidecar_writes'] == (design.GENERATIONS*cfg.sweeps if policy == 'average' else 0)
                environment = (env, proof['terminal_birth_sha256'], proof['terminal_rng'])
                if paired_environment is None:
                    paired_environment = environment
                    for birth in [v['birth_sha256'] for v in env]+[proof['terminal_birth_sha256']]:
                        assert birth not in distinct_births
                        distinct_births.add(birth)
                else:
                    assert environment == paired_environment
                proofs.append(proof)
    aggregate = dict(policies=len(proofs), chains=sum(v['records'] for v in proofs),
        **{key: sum(v[key] for v in proofs) for key in ('native_arrays', 'native_reader_contexts', 'native_repair_contexts')},
        actual_record_writes_per_message_batch=sum(v['actual_record_writes'] for v in proofs),
        unused_native_sidecar_writes_per_message_batch=sum(v['unused_native_sidecar_writes'] for v in proofs),
        max_native_error=0., max_average_error=max(v['max_average_error'] for v in proofs))
    original = c.read_json(directory/'CHECK.json')
    assert original['status'] == 'PASS' and original['role'] == 'development'
    assert original['tissue'] == config['tissue']
    assert original['reused_starting_packets'] and not original['fresh_population_confirmation']
    assert all(original[k] == v for k, v in aggregate.items())
    return aggregate


def main():
    tick = time.monotonic()
    DESTINATION.mkdir(parents=True, exist_ok=False)
    verifier_sha = c.sha(__file__)
    c.write_json(DESTINATION/'STARTED.json', dict(started_utc=c.now(),
        verifier_sha256=verifier_sha, written_after_acquisition=True,
        written_before_scientific_effect_inspection=True, new_dynamics=0,
        original_run_status='FAILED', original_run_unchanged=True))
    try:
        frozen = c.read_json(c.ROOT/'FREEZE.json')
        running = c.read_json(ORIGINAL/'RUNNING.json')
        failure = c.read_json(ORIGINAL/'FAILED.json')
        launch = c.read_json(c.ROOT/'LAUNCH.json')
        assert failure['status'] == 'FAILED' and failure['error'] == 'AssertionError()'
        assert 'assert analysis.report(read_json' in failure['traceback']
        assert not (ORIGINAL/'COMPLETE.json').exists()
        assert running['inputs'] == frozen['inputs'] == c.runtime_hashes()
        assert execute.environment() == frozen['environment']
        assert running['freeze_sha256'] == launch['freeze_sha256'] == c.sha(c.ROOT/'FREEZE.json')
        assert launch['status'] == 'DETACHED_STARTED' and launch['pid'] == running['pid']
        assert running['workers'] == frozen['workers'] == 2
        assert running['numerical_threads'] == frozen['numerical_threads'] == 1
        assert running['cpus'] == frozen['cpus']
        start, fail = (datetime.fromisoformat(x) for x in (running['started_utc'], failure['failed_utc']))
        assert datetime.fromisoformat(frozen['frozen_utc']) < start < fail
        acquisition_seconds = (fail-start).total_seconds()
        assert acquisition_seconds < running['deadline_seconds'] == frozen['deadline_seconds']
        cfg, rcfg = design.configs('development')
        assert c.serialized(asdict(cfg)) == c.serialized(frozen['config'])
        assert c.serialized(asdict(rcfg)) == c.serialized(frozen['readout'])
        assert c.serialized(design.comparisons()) == c.serialized(frozen['comparisons'])
        assert frozen['blocks'] == list(c.BLOCKS)
        assert frozen['families'] == list(design.FAMILIES) and frozen['policies'] == list(design.POLICIES)
        assert frozen['futures'] == design.FUTURES and frozen['generations'] == design.GENERATIONS
        c.verify(frozen['inputs']); c.verify(frozen['evidence'])
        assert c.source_check() == 289 and c.baseline_check() == 8
        prerequisites = dict(qualification=prerequisite(c.ROOT/'checks/qualification_v1', 'PASS', frozen['inputs']),
            benchmark=prerequisite(c.ROOT/'runs/benchmark_v1', 'COMPLETE', frozen['inputs']))
        before = files(ORIGINAL)
        retained = sum(Path(p).stat().st_size for p in before)
        assert retained < frozen['run_byte_limit'] and shutil.disk_usage(c.ROOT).free >= frozen['free_reserve_bytes']
        c.write_json(DESTINATION/'ORIGINAL_FILES.json', before)
        assert {p.name for p in ORIGINAL.glob('tissue_*')} == {f'tissue_{i}' for i in c.BLOCKS}
        checks, saved = {}, {}
        for index in c.BLOCKS:
            directory = ORIGINAL/f'tissue_{index}'
            assert c.read_json(directory/'CONFIG.json')['tissue'] == index
            saved[index] = run.saved_check(directory)
            checks[index] = checked_block_receipts(directory)
            print(json.dumps(dict(stage='saved_block_verified', tissue=index)), flush=True)
        c.write_json(DESTINATION/'BLOCK_CHECKS.json', dict(acquisition=checks, saved=saved))

        # Require exact scientific content before allowing presentation-order normalization.
        rebuilt = analysis.summary(ORIGINAL)
        summary_bytes = c.serialized(rebuilt)
        assert summary_bytes == (ORIGINAL/'SUMMARY.json').read_bytes()
        original_report = (ORIGINAL/'REPORT.md').read_text()
        assert analysis.report(rebuilt) == original_report
        canonical = analysis.report(json.loads(summary_bytes))
        assert canonical != original_report
        assert Counter(canonical.splitlines()) == Counter(original_report.splitlines())
        with (DESTINATION/'SUMMARY.json').open('xb') as stream: stream.write(summary_bytes)
        with (DESTINATION/'REPORT.md').open('x') as stream: stream.write(canonical)
        assert analysis.report(c.read_json(DESTINATION/'SUMMARY.json')) == (DESTINATION/'REPORT.md').read_text()
        assert c.serialized(analysis.summary(ORIGINAL)) == summary_bytes
        c.write_json(DESTINATION/'REPORT_CHECK.json', dict(status='PASS', reason='JSON_SORTED_KEYS_CHANGE_TABLE_ROW_ORDER_ONLY',
            original_summary_sha256=c.sha(ORIGINAL/'SUMMARY.json'), recovered_summary_sha256=c.sha(DESTINATION/'SUMMARY.json'),
            original_report_sha256=c.sha(ORIGINAL/'REPORT.md'), recovered_report_sha256=c.sha(DESTINATION/'REPORT.md'),
            exact_summary_reproduced=True, original_report_reproduced_from_frozen_in_memory_summary=True,
            report_line_multiset_identical=True, canonical_json_report_roundtrip_exact=True,
            scientific_values_changed=False, analysis_rules_changed=False))

        c.verify(frozen['inputs']); c.verify(frozen['evidence']); c.baseline_check()
        assert files(ORIGINAL) == before and c.runtime_hashes() == frozen['inputs']
        assert c.sha(__file__) == verifier_sha
        verification = {k: sum(v[k] for v in checks.values()) for k in next(iter(checks.values())) if not k.startswith('max_')}
        verification.update(max_native_error=0., max_average_error=max(v['max_average_error'] for v in checks.values()))
        saved_counts = {k: sum(v[k] for v in saved.values()) for k in ('array_receipts', 'records', 'inherited_transitions', 'new_dynamics')}
        output_hashes = files(DESTINATION)
        complete = dict(status='PASS', study='TT022', completed_utc=c.now(), seconds=time.monotonic()-tick,
            original_run=str(ORIGINAL), original_run_status='FAILED', original_failure_preserved=True,
            failure_scope='REPORT_ROW_ORDER_ONLY', original_files_unchanged=True,
            original_files=len(before), original_retained_bytes=retained, inputs=frozen['inputs'],
            freeze_sha256=c.sha(c.ROOT/'FREEZE.json'), original_failure_sha256=c.sha(ORIGINAL/'FAILED.json'),
            recovery_verifier_sha256=verifier_sha, recovery_written_after_acquisition=True,
            recovery_written_before_scientific_effect_inspection=True, environment=execute.environment(),
            prerequisite_output_files=prerequisites, blocks=list(c.BLOCKS),
            verification=verification, saved_verification=saved_counts, outputs=output_hashes,
            acquisition_started_utc=running['started_utc'], original_failure_utc=failure['failed_utc'],
            acquisition_to_failure_seconds=acquisition_seconds, new_dynamics=0, new_record_identities=0,
            summary_byte_identical=True, report_rows_only_reordered=True,
            fresh_population_confirmation=False, significance_verdict=False,
            automatic_polling=False, automatic_retry=False, automatic_successor=False)
        c.write_json(DESTINATION/'COMPLETE.json', complete)
        c.write_json(c.ROOT/'CLOSEOUT.json', dict(status='PASS', study='TT022', completed_utc=complete['completed_utc'],
            path=str(DESTINATION/'COMPLETE.json'), sha256=c.sha(DESTINATION/'COMPLETE.json'),
            original_run_status='FAILED', original_failure_preserved=True,
            recovery_scope='REPORT_ROW_ORDER_AND_SAVED_EVIDENCE_CLOSEOUT', new_dynamics=0))
        print(json.dumps({k: complete[k] for k in ('status', 'seconds', 'original_files', 'original_retained_bytes',
            'verification', 'saved_verification', 'acquisition_to_failure_seconds', 'failure_scope')}), flush=True)
    except BaseException as error:
        c.write_json(DESTINATION/'FAILED.json', dict(status='FAILED', failed_utc=c.now(), error=repr(error), traceback=traceback.format_exc()))
        raise


if __name__ == '__main__':
    main()
