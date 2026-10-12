"""Full raw-window checks, independent serial endpoints and fixed block inference."""
import math
import numpy as np
import statistics_block as st
import support as s

METRICS = ('uninterrupted', 'terminal', 'ever_recovered', 'terminal_after_failure',
           'mean_cycle_success', 'initial_success_run', 'ever_opposite', 'terminal_opposite')


def scalar_score(raw):
    windows = raw['port_windows']
    s.require(windows.shape == (32, 8, 16, 2, 2), 'Complete observation window')
    means = np.empty((8, 16, 2, 2))
    for vi, case, cue, port in np.ndindex(means.shape):
        means[vi, case, cue, port] = math.fsum(map(float, windows[:, vi, case, cue, port]))/32
    error = s.close(means, raw['mean_ports'], 1e-12, 'Independent scalar port means')
    margin, opposite = np.empty((8, 16)), np.empty((8, 16))
    for vi, case in np.ndindex(8, 16):
        rule = 1 if (case//4) % 2 == 0 else -1
        p = means[vi, case]
        values = [rule*p[0, 0], -rule*p[0, 1], -rule*p[1, 0], rule*p[1, 1]]
        margin[vi, case], opposite[vi, case] = min(values), -max(values)
    s.close(margin, raw['min_margin'], 1e-12, 'Independent intended margin')
    s.close(opposite, raw['opposite_margin'], 1e-12, 'Independent opposite margin')
    s.equal(margin > .25, raw['both_pass'], 'Every strict intended flag')
    s.equal(opposite > .25, raw['opposite_pass'], 'Every strict opposite flag')
    s.require(not ((margin > .25) & (opposite > .25)).any(), 'Exclusive task flags')
    return dict(status='PASS', raw_endpoints=128, dual_task_flags=256, scalar_window_max_error=error,
                nearest_threshold=float(min(abs(margin-.25).min(), abs(opposite-.25).min())))


def endpoints(good, other):
    s.require(good.shape == other.shape == (18, 8, 16) and good.dtype == other.dtype == bool,
              'Complete fixed serial panel')
    prefix = np.logical_and.accumulate(good, axis=0)
    result = dict(uninterrupted=good.all(axis=0), terminal=good[-1],
                  ever_recovered=(good[1:] & ~prefix[:-1]).any(axis=0),
                  terminal_after_failure=good[-1] & ~prefix[-2], mean_cycle_success=good.mean(axis=0),
                  initial_success_run=prefix.sum(axis=0), ever_opposite=other.any(axis=0), terminal_opposite=other[-1])
    independent = {k: np.zeros((8, 16)) for k in METRICS}
    for vi, case in np.ndindex(8, 16):
        flags = [bool(v) for v in good[:, vi, case]]
        opposites = [bool(v) for v in other[:, vi, case]]
        independent['uninterrupted'][vi, case] = all(flags)
        independent['terminal'][vi, case] = flags[-1]
        independent['ever_recovered'][vi, case] = any(flags[j] and not all(flags[:j]) for j in range(1, 18))
        independent['terminal_after_failure'][vi, case] = flags[-1] and not all(flags[:-1])
        independent['mean_cycle_success'][vi, case] = sum(flags)/18
        independent['initial_success_run'][vi, case] = next((i for i, flag in enumerate(flags) if not flag), 18)
        independent['ever_opposite'][vi, case] = any(opposites)
        independent['terminal_opposite'][vi, case] = opposites[-1]
    for k in METRICS:
        s.close(result[k], independent[k], 1e-14, 'Independent endpoint '+k)
    return result


def strata(values, cfg):
    return [[values[b] for b in cfg['blocks'] if cfg['history_by_block'][str(b)] == h] for h in range(4)]


def summary(counts, cfg, denominator=16):
    rows = strata(counts, cfg)
    values = np.asarray(rows)/denominator
    interval = st.bootstrap(values, cfg)
    st.audit_bootstrap(rows, cfg, interval, denominator)
    return dict(mean=math.fsum(map(float, values.ravel()))/64,
                by_block={str(b): float(counts[b]/denominator) for b in cfg['blocks']},
                descriptive_stratified_block_bootstrap95=interval,
                positive_blocks=int((values > 0).sum()), tied_blocks=int((values == 0).sum()),
                negative_blocks=int((values < 0).sum()))


def summarize(panel, cfg):
    s.require(set(panel) == set(cfg['blocks']), 'Exact registered cohort')
    ep = {b: endpoints(p['intended'], p['opposite']) for b, p in panel.items()}
    rates, rows = {}, []
    for vi, name in enumerate(cfg['variants']):
        rates[name] = {}
        for metric in METRICS:
            denominator = 16*18 if metric == 'mean_cycle_success' else 16
            counts = {b: int(panel[b]['intended'][:, vi].sum()) if metric == 'mean_cycle_success'
                      else int(ep[b][metric][vi].sum()) for b in cfg['blocks']}
            rates[name][metric] = summary(counts, cfg, denominator)
        for b in cfg['blocks']:
            rows.append(dict(block=b, history=cfg['history_by_block'][str(b)], variant=name,
                             **{k: float(ep[b][k][vi].mean()) for k in METRICS}))
    contrasts, all_counts = {}, {}
    for name, coefs in cfg['contrasts'].items():
        contrasts[name], all_counts[name] = {}, {}
        for metric in ('uninterrupted', 'terminal'):
            counts = {b: sum(c*int(ep[b][metric][vi].sum()) for vi, c in enumerate(coefs)) for b in cfg['blocks']}
            contrasts[name][metric] = summary(counts, cfg)
            all_counts[name][metric] = strata(counts, cfg)
    primary_counts = all_counts[cfg['primary_contrast']]['uninterrupted']
    effect = st.bounds(np.asarray(primary_counts)/16, cfg['primary_margin'])
    st.audit_bounds(primary_counts, cfg['primary_margin'], effect)
    effect.update(by_block=contrasts[cfg['primary_contrast']]['uninterrupted']['by_block'],
                  descriptive_stratified_block_bootstrap95=contrasts[cfg['primary_contrast']]['uninterrupted']['descriptive_stratified_block_bootstrap95'])
    paired = {}
    for ri, regime in enumerate(cfg['noise_regimes']):
        paired[regime] = {}
        for metric in ('uninterrupted', 'terminal'):
            x = np.concatenate([ep[b][metric][4*ri+2] for b in cfg['blocks']])
            y = np.concatenate([ep[b][metric][4*ri] for b in cfg['blocks']])
            paired[regime][metric] = dict(repeated_only=int((x & ~y).sum()), baseline_only=int((y & ~x).sum()),
                                         both=int((x & y).sum()), neither=int((~(x | y)).sum()), records=1024)
    histories = {history: {name: {k: sum(int(ep[b][k][vi].sum()) for b in cfg['blocks']
                    if cfg['history_by_block'][str(b)] == h)/256 for k in ('uninterrupted', 'terminal')}
                    for vi, name in enumerate(cfg['variants'])} for h, history in enumerate(cfg['histories'])}
    groups = {}
    for flag, label in [(False, 'initially_failing'), (True, 'initially_passing')]:
        n = sum(int((p['initial'] == flag).sum()) for p in panel.values())
        group = {}
        for vi, name in enumerate(cfg['variants']):
            group[name] = {}
            for k in ('uninterrupted', 'terminal'):
                count = sum(int(ep[b][k][vi][panel[b]['initial'] == flag].sum()) for b in cfg['blocks'])
                group[name][k] = dict(successes=count, rate=count/n if n else None)
        groups[label] = dict(records=n, rates=group, weighting='Descriptive pooled record rates; no primary substitution')
    curves = {name: [dict(generation=g,
                  success=sum(int(panel[b]['intended'][gi, vi].sum()) for b in cfg['blocks'])/1024,
                  uninterrupted=sum(int(panel[b]['intended'][:gi+1, vi].all(axis=0).sum()) for b in cfg['blocks'])/1024,
                  opposite=sum(int(panel[b]['opposite'][gi, vi].sum()) for b in cfg['blocks'])/1024)
                  for gi, g in enumerate(cfg['generations'])] for vi, name in enumerate(cfg['variants'])}
    verdict = ('PRACTICAL_SUPERIORITY_PASS' if effect['practical_superiority'] else
               'PRACTICAL_SUPERIORITY_UNSUPPORTED' if effect['practical_superiority_unsupported'] else
               'PRACTICAL_SUPERIORITY_INCONCLUSIVE')
    return dict(blocks=64, records=1024, generations=cfg['generations'], primary_name=cfg['primary_contrast'],
                primary_endpoint='uninterrupted', primary_effect=effect, rates=rates, contrasts=contrasts,
                paired_counts=paired, history_summaries=histories, pre_repair_subgroups=groups, curves=curves,
                scientific_verdict=verdict, new_scientific_cohort=True, fitted_parameters=0,
                subgroup_rescue_permitted=False, secondary_intervals_descriptive=True), rows, primary_counts


def run(output, cfg, progress):
    panel, endpoint_rows, resource_rows = {}, [], []
    totals = {name: dict(repair_calls=0, added_edges=0, added_abs_weight=0., repair_cpu_seconds=0., audit_cpu_seconds=0.,
                        available_edges=0, fallback_edges=0, returning_edges=0, returning_fallback_edges=0,
                        allocated_record_bytes=4096, reader_updates_per_record=18*2048) for name in cfg['variants']}
    moments = []
    max_window_error, nearest, raw_count, task_flags = 0., 1., 0, 0
    for block in cfg['blocks']:
        progress('complete_scoring_and_evidence_accounting', block=block)
        folder = output/'blocks'/str(block)
        receipt = s.read(folder/'REPLAY_AUDIT.json')
        seal = s.read(folder/'ENROLLMENT_SEAL.json')
        enrolled = s.arrays(folder/'enrollment.npz')
        s.require(seal['enrollment_sha256'] == s.sha(folder/'enrollment.npz'), 'Committed all-record enrollment')
        intended, opposite = [], []
        previous = np.repeat(enrolled['initial_packets'][None], 8, axis=0)
        for gi, g in enumerate(cfg['generations']):
            replay = receipt['continuations'][gi]
            path = folder/f'continuation_{g:02d}.npz'
            s.require(replay['file_sha256'] == s.sha(path) and replay['generation'] == g, 'Scored evidence identity')
            raw = s.arrays(path)
            s.equal(previous, raw['incoming'], 'All actual body-written successor links')
            previous = raw['outgoing']
            score = replay['scoring']
            s.require(score['status'] == 'PASS', 'Committed independent raw-window scoring')
            max_window_error = max(max_window_error, score['scalar_window_max_error'])
            nearest = min(nearest, score['nearest_threshold'])
            raw_count += score['raw_endpoints']
            task_flags += score['dual_task_flags']
            intended.append(raw['both_pass']); opposite.append(raw['opposite_pass']); moments.append(raw['noise_moments'])
            for vi, name in enumerate(cfg['variants']):
                for key, field in [('repair_calls', 'applied'), ('added_edges', 'added_edges'),
                                   ('available_edges', 'available_edges'), ('fallback_edges', 'fallback_edges'),
                                   ('returning_edges', 'returning_edges'), ('returning_fallback_edges', 'returning_fallback_edges')]:
                    totals[name][key] += int(raw[field][vi].sum())
                for key in ('added_abs_weight', 'repair_cpu_seconds', 'audit_cpu_seconds'):
                    totals[name][key] += math.fsum(map(float, raw[key][vi]))
                for case in range(16):
                    ids = dict(block=block, history=cfg['history_by_block'][str(block)], generation=g, variant=name, case=case)
                    endpoint_rows.append(dict(**ids, intended=int(raw['both_pass'][vi, case]),
                        opposite=int(raw['opposite_pass'][vi, case]), min_margin=float(raw['min_margin'][vi, case]),
                        opposite_margin=float(raw['opposite_margin'][vi, case]),
                        uninterrupted_so_far=int(all(x[vi, case] for x in intended))))
                    resource_rows.append(dict(**ids, **{k: float(raw[k][vi, case]) for k in
                        ('applied', 'missing_edges', 'added_edges', 'added_abs_weight', 'magnitude', 'shuffle_changes',
                         'repair_cpu_seconds', 'audit_cpu_seconds')}))
        panel[block] = dict(intended=np.stack(intended), opposite=np.stack(opposite), initial=enrolled['initial_pass'])
    s.require(raw_count == 147456 and task_flags == 294912, 'Every continuation endpoint and task')
    result, block_rows, counts = summarize(panel, cfg)
    noise = {}
    for i, name in enumerate(cfg['noise_regimes']):
        p, m, pp, mm, pm, n = [math.fsum(float(a[i, j]) for a in moments) for j in range(6)]
        vp, vm = pp/n-(p/n)**2, mm/n-(m/n)**2
        noise[name] = dict(draws=int(n), mean_plus=p/n, mean_minus=m/n, variance_plus=vp, variance_minus=vm,
                           measured_correlation=(pm/n-p*m/n**2)/math.sqrt(vp*vm), target_correlation=cfg['correlations'][i])
    for name, row in totals.items():
        row['fallback_fraction'] = row['fallback_edges']/row['available_edges'] if row['available_edges'] else None
        row['returning_fallback_fraction'] = row['returning_fallback_edges']/row['returning_edges'] if row['returning_edges'] else None
    result.update(resources_and_mechanism=totals, noise_diagnostics=noise)
    for name, rows in [('reads', endpoint_rows), ('resources', resource_rows), ('block_summaries', block_rows)]:
        s.csv_write(output/(name+'.csv'), rows)
        retained = s.table(output/(name+'.csv'))
        s.require(len(retained) == len(rows), 'Complete table '+name)
        for a, b in zip(retained, rows):
            s.require(set(a) == set(b), 'Table schema')
            for key, value in b.items():
                s.require(a[key] == str(value), 'Lossless table field '+key)
    s.dump(output/'block_contrast_counts.json', counts)
    s.dump(output/'analysis.json', result)
    s.dump(output/'SCORING_AUDIT.json', dict(status='PASS', raw_endpoints=raw_count, dual_task_flags=task_flags,
        scalar_window_max_error=max_window_error, nearest_threshold=nearest, tables=3,
        table_rows=dict(reads=len(endpoint_rows), resources=len(resource_rows), block_summaries=len(block_rows)),
        independent_integer_interval_audit=True, independent_bootstrap_multiplicities=True,
        scalar_endpoint_audit=True, independent_blocks=64, secondary_inference_descriptive=True,
        scoring_receipts_bound_to_every_retained_raw_file=True, new_scientific_cohort=True))
    return result
