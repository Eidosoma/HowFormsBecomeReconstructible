"""Packet-only features from actions sealed before the exposed paired futures."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import time
import numpy as np
from core import ROOT, P, require

sys.path.insert(0, str(ROOT / 'support'))
from bridge import e, audit as transfer_audit, ev, read


def digest(value):
    return hashlib.sha256(value.tobytes()).hexdigest()


def verify_files(root, manifest, exempt=()):
    actual = {str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()}
    require(actual == set(manifest) | set(exempt), 'Source coverage changed: ' + str(root))
    require(not any(p.is_symlink() for p in root.rglob('*')), 'Source symlinks')
    for name, expected in manifest.items():
        file = (root / name).resolve()
        require(file.is_relative_to(root.resolve()), 'Escaping evidence path')
        require(ev.sha(file) == expected, 'Source hash changed: ' + name)


def packet_features(original, repaired, rule):
    """The endpoint, history, current body and forecasts are absent from this API."""
    start = time.process_time()
    t0, _ = e.transfer(original, rule)
    t1, _ = e.transfer(repaired, rule)
    feature_cpu = time.process_time() - start
    start = time.process_time()
    a0 = transfer_audit.transfer(original, rule)[0]
    a1 = transfer_audit.transfer(repaired, rule)[0]
    require(abs(t0 - a0) <= 1e-12 and abs(t1 - a1) <= 1e-12, 'Separate signed-transfer calculation differs')
    return dict(transfer=float(t0), transfer_change=float(t1 - t0)), feature_cpu, time.process_time() - start


def prepare(destination):
    binding = read(ROOT / 'SOURCE_BINDINGS.json')
    source = Path(binding['source_run'])
    inputs = Path(binding['source_inputs'])
    complete = read(source / 'COMPLETE.json')
    require(complete['status'] == 'COMPLETE', 'Predecessor incomplete')
    require(ev.sha(source / 'COMPLETE.json') == binding['source_complete_sha256'], 'Source completion changed')
    require(ev.sha(source / 'OUTPUTS.json') == complete['output_manifest_sha256'], 'Source output commitment changed')
    verify_files(source, read(source / 'OUTPUTS.json')['sha256'], ('OUTPUTS.json', 'COMPLETE.json', 'STATUS.json'))
    require(ev.sha(inputs / 'INPUTS.json') == read(source / 'START.json')['input_manifest_sha256'], 'Source input binding changed')
    verify_files(inputs, read(inputs / 'INPUTS.json')['sha256'], ('INPUTS.json',))
    seal = read(source / 'PANEL_SEAL.json')
    require(ev.sha(source / 'PANEL_SEAL.json') == complete['panel_seal_sha256'], 'Source panel seal changed')
    require(seal['all_actions_and_forecasts_checked_before_any_future'], 'Actions not sealed before futures')
    require(ev.sha(source / 'ACTIONS.json') == seal['action_receipts_sha256'], 'Action receipt binding changed')
    actions = read(source / 'ACTIONS.json')
    initial = ev.load(source / 'ACTIONS.npz', seal['action_arrays_sha256'])['initial_packets']
    rows = seal['rows']
    forecasts = {(tuple(f['key']), f['regime']): f['probabilities'] for f in seal['forecasts']}
    require(len(rows) == len(actions) == len(initial) == 63 and len(forecasts) == 126, 'Complete source panel required')
    labels, label_sources = {}, []
    for reference in read(source / 'FUTURE_REFERENCES.json'):
        path = (source / reference['path']).resolve()
        require(path.is_relative_to(source.resolve()), 'Future path escapes source')
        require(ev.sha(path / 'COMMIT.json') == reference['commit_sha256'], 'Commit binding changed')
        commit = read(path / 'COMMIT.json')
        verify_files(path, commit['sha256'], ('COMMIT.json',))
        outcomes = read(path / 'OUTCOMES.json')
        require(outcomes == commit['payload']['outcomes'], 'Committed paired outcomes differ')
        for o in outcomes:
            key = (tuple(o['key']), o['regime'])
            require(key not in labels and o['control'] in (0, 1) and o['repaired'] in (0, 1), 'Duplicate/nonbinary source outcome')
            labels[key] = o
        label_sources.append(reference)
    expected = {(tuple(r['key']), regime) for r in rows for regime in ('matched', 'independent')}
    require(set(labels) == set(forecasts) == expected, 'Source paired panel coverage')
    counts = Counter((r['block'], r['current_pass']) for r in rows)
    records, measured = [], []
    feature_cpu = audit_cpu = 0.
    for index, (row, action, pair) in enumerate(zip(rows, actions, initial, strict=True)):
        require(row['key'] == action['key'], 'Wrong repair action identity')
        require([digest(a) for a in pair] == seal['branch_packet_sha256'][index], 'Action packet hash mismatch')
        require(digest(pair[0]) == row['packet_sha256'] == action['incoming_sha256'], 'Wrong original packet')
        require(digest(pair[1]) == action['repaired_sha256'], 'Wrong counterfactual repair')
        features, cost, checked_cost = packet_features(pair[0], pair[1], row['rule'])
        require(abs(features['transfer'] - row['boundary'][-1]) <= 1e-12, 'Original signed transfer changed')
        feature_cpu += cost; audit_cpu += checked_cost
        measured.append(dict(key=row['key'], **features, feature_cpu_seconds=cost, feature_audit_cpu_seconds=checked_cost))
        for regime in ('matched', 'independent'):
            label = labels[tuple(row['key']), regime]
            probabilities = forecasts[tuple(row['key']), regime]
            feature = dict(**features, independent=float(regime == 'independent'),
                ordinary_risk=1 - probabilities['tt008'], direct_risk=1 - probabilities['direct_rival'],
                successor_risk=1 - probabilities['candidate'])
            weight = 1 / (4 * counts[row['block'], row['current_pass']])
            records.append(dict(key=row['key'], block=row['block'], regime=regime, history=row['history'],
                current_pass=row['current_pass'], weight=weight, features=feature,
                control=label['control'], repaired=label['repaired'], benefit=label['repaired'] - label['control']))
    require(sorted({r['block'] for r in records}) == P['blocks'], 'Changed development blocks')
    resources = read(source / 'RESOURCES.json')
    receipt = dict(status='PASS', records=63, paired_records=126, blocks=16, source_output_files=170,
        source_input_files=595, all_packet_features_independently_checked=True,
        feature_cpu_seconds=feature_cpu, feature_audit_cpu_seconds=audit_cpu,
        prior_physical_repair_cpu_seconds=resources['repair_cpu_seconds'], prior_repair_audit_cpu_seconds=resources['optimizer_audit_cpu_seconds'],
        deployment_warning='Candidate dry-run repair is required for every packet, including skipped interventions. Current feature timing and prior repair timing are separate measurements, not a joint deployment benchmark.',
        new_native_reads=0, new_paired_outcomes=0,
        source_panel_seal_sha256=complete['panel_seal_sha256'], source_complete_sha256=ev.sha(source / 'COMPLETE.json'),
        source_output_manifest_sha256=complete['output_manifest_sha256'])
    ev.write(destination / 'RECORDS.json', records)
    ev.write(destination / 'PACKET_FEATURES.json', measured)
    ev.write(destination / 'SOURCE_VERIFICATION.json', receipt)
    ev.write(destination / 'PAIRED_REFERENCES.json', label_sources)
    return records, receipt
