"""Excluded qualification of the new serial composition and information boundary."""
import argparse
from dataclasses import asdict
import os
from pathlib import Path
import shutil
import time
import traceback

from common import *
import audit
import design
import execute
import kernel
import run


def rejected(label, function, checks):
    try: function()
    except (AssertionError, ValueError, FileNotFoundError): checks.append(label)
    else: raise AssertionError('not rejected: '+label)


def main(name):
    destination = ROOT/'checks'/name; destination.mkdir(parents=True, exist_ok=False)
    tick = time.monotonic(); inputs = runtime_hashes(); checks = []
    write_json(destination/'STARTED.json', dict(started_utc=now(), inputs=inputs, scientific_futures_generated=False))
    try:
        source_check(); baseline_check()
        checks.append('byte-identical qualified physics and checksum-bound exposed/excluded starting packets')
        rejected('scientific futures blocked before freeze',
            lambda: run.run_block(destination/'forbidden', BLOCKS[0], 'development'), checks)
        assert len(design.POLICIES) == 7 and design.FAMILIES == ('common', 'residual')
        selected = design.spec('common', 'average')
        assert selected.base.reader == 'fixed' and selected.capture
        assert not design.spec('common', 'capture_once').base.write
        checks.append('seven fixed policies, both record families, protected-snapshot and nonwriting controls retained')
        serial = destination/'serial'; serial.mkdir()
        for index in DISPOSABLE:
            run.run_block(serial/f'tissue_{index}', index, 'qualification')
            run.saved_check(serial/f'tissue_{index}')
        checks.append('all excluded two-cycle trajectories, injuries, inheritance and scores independently replayed')
        parallel = destination/'parallel'; parallel.mkdir()
        cpus = sorted(os.sched_getaffinity(0))[-2:]
        execute.batch(parallel, DISPOSABLE, 'qualification', cpus)
        array_files = 0
        for p in sorted(serial.rglob('*.npz')):
            q = parallel/p.relative_to(serial)
            assert identities(arrays(p)) == identities(arrays(q)); array_files += 1
        for p in serial.rglob('records.json'):
            assert p.read_bytes() == (parallel/p.relative_to(serial)).read_bytes()
        for index in DISPOSABLE:
            assert run.saved_check(serial/f'tissue_{index}') == run.saved_check(parallel/f'tissue_{index}')
        checks.append('serial and two-worker arrays, record rows and saved checks exactly equal')
        cfg, rcfg = design.configs('qualification'); index = DISPOSABLE[0]
        ctx = model.source.context(index, cfg); baseline_packets, _ = baseline('qualification', index)
        policy_dir = serial/f'tissue_{index}'/'future_00/common/capture'
        incoming = baseline_packets[design.initial_name('common', 'capture')].tobytes()
        development = arrays(policy_dir/'g01_develop.npz'); meta = read_json(policy_dir/'g01.json')
        corrupt = {k: v.copy() for k, v in development.items()}
        corrupt['s1_V'].flat[0] = np.nextafter(corrupt['s1_V'].flat[0], np.inf)
        rejected('one-ULP physical corruption rejected',
            lambda: audit.read(ctx, incoming, rcfg, 0, 1, 'develop', corrupt, meta['read'], True), checks)
        corrupt = {k: v.copy() for k, v in development.items()}; corrupt['s0_R'].flat[0] = 1.
        rejected('ancestral reader memory rejected',
            lambda: audit.read(ctx, incoming, rcfg, 0, 1, 'develop', corrupt, meta['read'], False), checks)
        rejected('malformed inherited packet rejected', lambda: model.boundary.decode(incoming[:-8], cfg.replicates), checks)
        repaired = arrays(policy_dir/'g01_repair.npz')
        state = {k: repaired['s0_'+k].copy() for k in KEYS}
        address = kernel.address(index, 0, 1, 'repair'); selected = design.spec('common', 'capture')
        rejected('task codebook rejected at repair boundary', lambda: model.repair(
            model.boundary.runtime_context(ctx)|{'codes': ctx['codes']}, state, address, selected), checks)
        rejected('hidden ancestral state rejected at repair boundary', lambda: model.repair(
            model.boundary.runtime_context(ctx), state|{'parent': state['V']}, address, selected), checks)
        boundary = arrays(policy_dir/'g01_boundary.npz'); body = arrays(policy_dir/'g01_body.npz')
        rejected('wrong outgoing packet rejected', lambda: audit.repair(ctx, incoming,
            development[f's{cfg.sweeps}_V'], rcfg, 0, 1, selected, 'capture', boundary, meta['injury'],
            repaired, meta['repair'], body, bytes(len(incoming)), False), checks)
        changed_boundary = {k: v.copy() for k, v in boundary.items()}; changed_boundary['fresh'].flat[0] ^= True
        rejected('changed injury mask rejected', lambda: audit.injury(ctx, incoming,
            development[f's{cfg.sweeps}_V'], 0, 1, selected, changed_boundary, repaired, meta['injury']), checks)
        average_dir = serial/f'tissue_{index}'/'future_00/common/average'
        average_raw = arrays(average_dir/'g01_repair.npz'); average_raw['a0_mean'] += .1
        a_meta = read_json(average_dir/'g01.json'); a_read = arrays(average_dir/'g01_develop.npz')
        a_in = baseline_packets[design.initial_name('common', 'average')].tobytes()
        rejected('missing birth observation in average rejected', lambda: audit.repair(ctx, a_in,
            a_read[f's{cfg.sweeps}_V'], rcfg, 0, 1, design.spec('common', 'average'), 'average',
            arrays(average_dir/'g01_boundary.npz'), a_meta['injury'], average_raw, a_meta['repair'],
            arrays(average_dir/'g01_body.npz'), run.packet(average_raw, 'average', cfg), True), checks)
        mutant = destination/'corrupted_record'; shutil.copytree(policy_dir, mutant)
        rows = read_json(mutant/'records.json'); rows[0]['terminal'] = 1.-rows[0]['terminal']
        (mutant/'records.json').write_bytes(serialized(rows))
        rejected('changed saved endpoint row rejected', lambda: run.saved_policy(mutant, ctx, incoming,
            'common', 'capture', 0, 2, rcfg), checks)
        mutant = destination/'wrong_route'; shutil.copytree(policy_dir, mutant)
        route = read_json(mutant/'g02.json'); route['input_sha256'] = '0'*64
        (mutant/'g02.json').write_bytes(serialized(route))
        rejected('wrong cross-generation packet route rejected', lambda: run.saved_policy(mutant, ctx, incoming,
            'common', 'capture', 0, 2, rcfg), checks)
        rejected('undeclared random phase rejected', lambda: kernel.address(index, 0, 1, 'policy_capture'), checks)
        keys = [kernel.address(i, f, g, phase) for i in BLOCKS for f in range(design.FUTURES)
                for g in range(1, design.GENERATIONS+1) for phase in design.PHASES]
        assert len(keys) == len(set(keys))
        assert all(kernel.address(i, f, g, phase) == audit.address(i, f, g, phase)
                   for i in BLOCKS for f in range(design.FUTURES)
                   for g in range(1, design.GENERATIONS+1) for phase in design.PHASES)
        checks.append('all prospective addresses distinct and independently reconstructed; no scientific draws generated')
        sample_births = []
        for future, generation, phase in ((0, 1, 'develop'), (1, 1, 'develop'), (0, 2, 'develop'), (0, 1, 'terminal')):
            rng = ref.old.Coupled(ref.old.READ_TAG, audit.address(index, future, generation, phase), 'assay_birth', cfg.replicates)
            value = rng.standard_normal((4*cfg.replicates, 16, 16)); sample_births.append(value.tobytes())
            assert all(np.array_equal(value[:cfg.replicates], value[m*cfg.replicates:(m+1)*cfg.replicates]) for m in range(4))
        assert len(set(sample_births)) == 4
        checks.append('excluded actual RNG samples preserve message pairing and separate futures, generations and terminal birth')
        fake = run.rows([np.array([1., .5, 0., 1.])]*2, [np.array([1., 1., 0., .5])]*2,
                        np.array([0., 1., 1., 1.]), 1)
        assert fake[0]['uninterrupted_development'] and fake[0]['terminal'] == 0.
        assert not fake[1]['uninterrupted_development'] and fake[1]['uninterrupted_repaired']
        assert not fake[3]['uninterrupted_repaired'] and fake[3]['terminal'] == 1.
        checks.append('ties fail uninterrupted endpoints and terminal success stays separate')
        verify(inputs); assert runtime_hashes() == inputs
        outputs = {str(p): sha(p) for p in destination.rglob('*') if p.is_file()}
        result = dict(status='PASS', completed_utc=now(), seconds=time.monotonic()-tick,
            checks=checks, checks_passed=len(checks), inputs=inputs, outputs=outputs,
            environment=execute.environment(), matched_array_files=array_files,
            serial_parallel_exact=True, scientific_futures_generated=False,
            max_native_error=0., source_population_exposed=True)
        write_json(destination/'COMPLETE.json', result)
        write_json(ROOT/'QUALIFICATION.json', dict(status='PASS', path=str(destination/'COMPLETE.json'), sha256=sha(destination/'COMPLETE.json')))
        print(json.dumps({k: v for k, v in result.items() if k not in ('inputs', 'outputs')}, sort_keys=True), flush=True)
    except BaseException as error:
        write_json(destination/'FAILED.json', dict(status='FAILED', failed_utc=now(), error=repr(error),
            traceback=traceback.format_exc(), automatic_retry=False))
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--name', required=True)
    main(parser.parse_args().name)
